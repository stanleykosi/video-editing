"""Validated immutable render DAG and conservative semantic optimizer."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.errors import EngineError, ErrorCode
from video_engine.render.nodes import (
    ArtifactType,
    AudioMixNode,
    AudioSidechainNode,
    ColorConversionNode,
    CompositeNode,
    ConcatNode,
    DecodeNode,
    GradeNode,
    MaskNode,
    MotionGraphicNode,
    MuxNode,
    NodeKind,
    RenderNode,
    SpeedNode,
    TransformNode,
    TransitionNode,
)


def _graph_error(message: str, **context: object) -> EngineError:
    return EngineError(ErrorCode.INVALID_TIMELINE, message, context=dict(context))


class RenderGraph(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    graph_version: str = "1.0.0"
    nodes: tuple[RenderNode, ...] = Field(min_length=1)
    outputs: dict[str, str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dag(self) -> RenderGraph:
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("render node ids must be unique")
        node_ids = set(ids)
        nodes = {node.id: node for node in self.nodes}
        for node in self.nodes:
            missing = [input_id for input_id in node.inputs if input_id not in node_ids]
            if missing:
                raise ValueError(f"node {node.id!r} references missing inputs {missing!r}")
            self._validate_arity(node)
            self._validate_artifacts(node, tuple(nodes[input_id] for input_id in node.inputs))
        missing_outputs = {
            name: node_id for name, node_id in self.outputs.items() if node_id not in node_ids
        }
        if missing_outputs:
            raise ValueError(f"graph outputs reference missing nodes: {missing_outputs!r}")
        self.topological_order()
        return self

    @staticmethod
    def _validate_arity(node: RenderNode) -> None:
        count = len(node.inputs)
        if isinstance(node, (DecodeNode, MotionGraphicNode)):
            if count:
                raise ValueError(f"source node {node.id!r} cannot have inputs")
            return
        if isinstance(node, (CompositeNode, AudioMixNode)):
            return
        if isinstance(node, ConcatNode):
            if count < 2:
                raise ValueError(f"concat node {node.id!r} requires at least two inputs")
            return
        if isinstance(node, TransitionNode) and count != 2:
            raise ValueError(f"transition node {node.id!r} requires exactly two inputs")
        if isinstance(node, AudioSidechainNode) and count != 2:
            raise ValueError(f"side-chain node {node.id!r} requires exactly two inputs")
        if isinstance(node, MaskNode):
            expected = 2 if node.mode in {"alpha_matte", "luma_matte"} else 1
            if count != expected:
                raise ValueError(f"mask node {node.id!r} requires exactly {expected} input(s)")
            return
        if isinstance(node, MuxNode) and count not in {1, 2}:
            raise ValueError(f"mux node {node.id!r} requires one or two inputs")
        if not isinstance(node, (TransitionNode, AudioSidechainNode, MuxNode)) and count != 1:
            raise ValueError(f"node {node.id!r} requires exactly one input")

    @staticmethod
    def _validate_artifacts(node: RenderNode, inputs: tuple[RenderNode, ...]) -> None:
        visual = {
            ArtifactType.VIDEO,
            ArtifactType.IMAGE,
            ArtifactType.MASK,
        }
        audio = {ArtifactType.AUDIO}
        visual_unary = {
            NodeKind.SCALE,
            NodeKind.CROP,
            NodeKind.TRANSFORM,
            NodeKind.COLOR_CONVERSION,
            NodeKind.GRADE,
            NodeKind.BLUR,
            NodeKind.SHADOW,
            NodeKind.GLOW,
            NodeKind.PERSPECTIVE,
            NodeKind.DISTORTION,
            NodeKind.CAPTION,
            NodeKind.OUTPUT_TRANSFORM,
        }
        polymorphic_unary = {
            NodeKind.TRIM,
            NodeKind.CONFORM,
            NodeKind.SPEED,
            NodeKind.SPEED_RAMP,
            NodeKind.REVERSE,
            NodeKind.FREEZE,
        }

        def reject(message: str) -> None:
            raise ValueError(
                f"node {node.id!r} {message}; input types are "
                f"{[item.artifact_type.value for item in inputs]!r}"
            )

        if node.node_type is NodeKind.DECODE:
            if node.artifact_type not in visual | audio:
                reject("has an unsupported decode artifact type")
            return
        if node.node_type is NodeKind.MOTION_GRAPHIC:
            if node.artifact_type not in {ArtifactType.VIDEO, ArtifactType.IMAGE}:
                reject("must produce a visual artifact")
            return
        if isinstance(node, MaskNode):
            if node.artifact_type is not ArtifactType.VIDEO or any(
                item.artifact_type not in visual for item in inputs
            ):
                reject("requires visual inputs and video output")
            return
        if node.node_type in visual_unary:
            if inputs[0].artifact_type not in visual or node.artifact_type not in {
                ArtifactType.VIDEO,
                ArtifactType.MASK,
            }:
                reject("requires a visual input and visual output")
            return
        if node.node_type in {NodeKind.AUDIO_PROCESS, NodeKind.LOUDNESS}:
            if inputs[0].artifact_type not in audio or node.artifact_type is not ArtifactType.AUDIO:
                reject("requires an audio input and audio output")
            return
        if node.node_type is NodeKind.AUDIO_SIDECHAIN:
            if node.artifact_type is not ArtifactType.AUDIO or any(
                item.artifact_type not in audio for item in inputs
            ):
                reject("requires program and key audio inputs with audio output")
            return
        if node.node_type in polymorphic_unary:
            if node.artifact_type is ArtifactType.AUDIO:
                if inputs[0].artifact_type not in audio:
                    reject("declares audio output but has a non-audio input")
            elif node.artifact_type in {ArtifactType.VIDEO, ArtifactType.IMAGE, ArtifactType.MASK}:
                if inputs[0].artifact_type not in visual:
                    reject("declares visual output but has a non-visual input")
            else:
                reject("has an unsupported output artifact type")
            return
        if node.node_type is NodeKind.COMPOSITE:
            if node.artifact_type is not ArtifactType.VIDEO or any(
                item.artifact_type not in visual for item in inputs
            ):
                reject("requires visual inputs and video output")
            return
        if node.node_type is NodeKind.CONCAT:
            if node.artifact_type is ArtifactType.VIDEO:
                if any(item.artifact_type is not ArtifactType.VIDEO for item in inputs):
                    reject("video concat requires video inputs")
            elif node.artifact_type is ArtifactType.AUDIO:
                if any(item.artifact_type is not ArtifactType.AUDIO for item in inputs):
                    reject("audio concat requires audio inputs")
            else:
                reject("supports only video or audio artifacts")
            return
        if node.node_type is NodeKind.AUDIO_MIX:
            if node.artifact_type is not ArtifactType.AUDIO or any(
                item.artifact_type not in audio for item in inputs
            ):
                reject("requires audio inputs and audio output")
            return
        if node.node_type is NodeKind.TRANSITION:
            family = audio if node.artifact_type is ArtifactType.AUDIO else visual
            if node.artifact_type not in visual | {ArtifactType.AUDIO} or any(
                item.artifact_type not in family for item in inputs
            ):
                reject("requires two inputs in the declared media family")
            return
        if node.node_type is NodeKind.ENCODE:
            if node.artifact_type is ArtifactType.ENCODED_VIDEO:
                if inputs[0].artifact_type not in visual:
                    reject("video encoder requires a visual input")
            elif node.artifact_type is ArtifactType.ENCODED_AUDIO:
                if inputs[0].artifact_type not in audio:
                    reject("audio encoder requires an audio input")
            else:
                reject("must produce encoded video or encoded audio")
            return
        if node.node_type is NodeKind.MUX:
            types = [item.artifact_type for item in inputs]
            if node.artifact_type is not ArtifactType.CONTAINER or any(
                item not in {ArtifactType.ENCODED_VIDEO, ArtifactType.ENCODED_AUDIO}
                for item in types
            ):
                reject("requires encoded stream inputs and container output")
            if len(types) != len(set(types)):
                reject("cannot mux duplicate stream families")

    def node_map(self) -> dict[str, RenderNode]:
        return {node.id: node for node in self.nodes}

    def node(self, node_id: str) -> RenderNode:
        try:
            return self.node_map()[node_id]
        except KeyError as exc:
            raise _graph_error("render node was not found", node_id=node_id) from exc

    def topological_order(self, targets: tuple[str, ...] | None = None) -> tuple[str, ...]:
        selected = (
            self.ancestor_closure(targets)
            if targets is not None
            else {node.id for node in self.nodes}
        )
        position = {node.id: index for index, node in enumerate(self.nodes)}
        indegree = {node_id: 0 for node_id in selected}
        dependents: dict[str, list[str]] = defaultdict(list)
        for node in self.nodes:
            if node.id not in selected:
                continue
            for input_id in node.inputs:
                if input_id in selected:
                    indegree[node.id] += 1
                    dependents[input_id].append(node.id)
        ready = deque(
            sorted(
                (node for node, degree in indegree.items() if degree == 0),
                key=lambda node_id: position[node_id],
            )
        )
        ordered: list[str] = []
        while ready:
            current = ready.popleft()
            ordered.append(current)
            for dependent in sorted(dependents[current], key=lambda node_id: position[node_id]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)
        if len(ordered) != len(selected):
            cyclic = sorted(node_id for node_id, degree in indegree.items() if degree > 0)
            raise ValueError(f"render graph contains a cycle involving {cyclic!r}")
        return tuple(ordered)

    def ancestor_closure(self, targets: tuple[str, ...] | None = None) -> set[str]:
        requested = targets or tuple(self.outputs.values())
        nodes = self.node_map()
        unknown = [node_id for node_id in requested if node_id not in nodes]
        if unknown:
            raise _graph_error("partial render targets are missing", targets=unknown)
        closure: set[str] = set()
        pending = list(requested)
        while pending:
            node_id = pending.pop()
            if node_id in closure:
                continue
            closure.add(node_id)
            pending.extend(nodes[node_id].inputs)
        return closure

    def pruned(self, targets: tuple[str, ...] | None = None) -> RenderGraph:
        closure = self.ancestor_closure(targets)
        outputs = (
            self.outputs
            if targets is None
            else {f"target_{index}": node_id for index, node_id in enumerate(targets)}
        )
        return RenderGraph(
            graph_version=self.graph_version,
            nodes=tuple(node for node in self.nodes if node.id in closure),
            outputs=outputs,
        )

    @property
    def graph_hash(self) -> str:
        payload = self.model_dump(mode="json")
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class OptimizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    graph: RenderGraph
    removed_nodes: tuple[str, ...] = ()


def optimize_graph(graph: RenderGraph) -> OptimizationResult:
    """Remove only identities whose timing and image semantics are provably unchanged."""

    current = graph.pruned()
    removed: list[str] = []
    replacements: dict[str, str] = {}

    def resolve(node_id: str) -> str:
        while node_id in replacements:
            node_id = replacements[node_id]
        return node_id

    kept: list[RenderNode] = []
    for node in current.nodes:
        inputs = tuple(resolve(input_id) for input_id in node.inputs)
        updates: dict[str, object] = {"inputs": inputs}
        if isinstance(node, CompositeNode):
            updates["layers"] = tuple(
                layer.model_copy(update={"input_id": resolve(layer.input_id)})
                for layer in node.layers
            )
        elif isinstance(node, AudioMixNode):
            updates["mix_inputs"] = tuple(
                item.model_copy(update={"input_id": resolve(item.input_id)})
                for item in node.mix_inputs
            )
        candidate = node.model_copy(update=updates)
        identity = False
        if len(inputs) == 1:
            if isinstance(candidate, SpeedNode) and candidate.rate.fraction == 1:
                identity = True
            elif isinstance(candidate, TransformNode):
                identity = (
                    candidate.position_x == 0
                    and candidate.position_y == 0
                    and candidate.scale_x == 1
                    and candidate.scale_y == 1
                    and candidate.rotation_degrees == 0
                    and candidate.opacity == 1
                    and not candidate.automation
                )
            elif isinstance(candidate, ColorConversionNode):
                identity = (
                    candidate.input_space == candidate.output_space and candidate.tone_map == "none"
                )
            elif isinstance(candidate, GradeNode):
                identity = (
                    candidate.exposure_stops == 0
                    and candidate.temperature == 0
                    and candidate.tint == 0
                    and candidate.contrast == 1
                    and candidate.saturation == 1
                    and candidate.highlights == 0
                    and candidate.shadows == 0
                    and candidate.lut_path is None
                )
        if identity:
            replacements[candidate.id] = inputs[0]
            removed.append(candidate.id)
        else:
            kept.append(candidate)

    outputs = {name: resolve(node_id) for name, node_id in current.outputs.items()}
    return OptimizationResult(
        graph=RenderGraph(graph_version=current.graph_version, nodes=tuple(kept), outputs=outputs),
        removed_nodes=tuple(removed),
    )
