"""Public render compilation, scheduling, delivery, and manifest orchestration."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from video_engine.config import EngineConfig
from video_engine.core.schema import JsonValue, Project
from video_engine.errors import EngineError, ErrorCode
from video_engine.qc.approval import QCApproval, QCApprovalService
from video_engine.render.backends.ffmpeg import FFmpegBackend
from video_engine.render.backends.registry import BackendPlan, BackendRegistry
from video_engine.render.backends.remotion import RemotionBackend
from video_engine.render.cache import RenderCache, sha256_file
from video_engine.render.checkpoints import (
    RenderCheckpoint,
    RenderCheckpointStore,
    checkpoint_identity,
)
from video_engine.render.compiler import CompiledRender, RenderCompiler
from video_engine.render.graph import RenderGraph
from video_engine.render.models import (
    NodeExecutionRecord,
    PartialRenderResult,
    RenderManifest,
    RenderMode,
    RenderRequest,
    RenderResult,
)
from video_engine.render.nodes import (
    CaptionNode,
    DecodeNode,
    GradeNode,
    MotionGraphicNode,
)
from video_engine.render.scheduler import RenderScheduler
from video_engine.temp import TemporaryWorkspace


class RenderService:
    def __init__(
        self,
        project: Project,
        project_root: Path,
        config: EngineConfig,
        registry: BackendRegistry | None = None,
    ) -> None:
        self.project = project.model_copy(deep=True)
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)
        self.registry = registry or BackendRegistry()
        if "ffmpeg" not in self.registry.names:
            self.registry.register(FFmpegBackend(self.config))
        if "remotion" not in self.registry.names:
            self.registry.register(RemotionBackend(self.config, self.project_root))

    def compile(self, request: RenderRequest) -> CompiledRender:
        return RenderCompiler(self.project, self.project_root, self.config).compile(request)

    def render(self, request: RenderRequest) -> RenderResult:
        started = datetime.now(UTC)
        render_id = f"render-{uuid.uuid4().hex}"
        manifest_path = request.output_path.with_suffix(
            request.output_path.suffix + ".render-manifest.json"
        )
        compiled: CompiledRender | None = None
        graph: RenderGraph | None = None
        backend_plan: BackendPlan | None = None
        checkpoint_store: RenderCheckpointStore | None = None
        checkpoint: RenderCheckpoint | None = None
        checkpoint_attempt_id: str | None = None
        checkpoint_path: Path | None = None
        destination_validated = False
        approval: QCApproval | None = None
        try:
            approval = self._validate_approval(request)
            compiled = self.compile(request)
            graph = compiled.graph.pruned()
            backend_plan = self.registry.plan(graph, request.backend)
            identity, signature = checkpoint_identity(
                compiled,
                backend_plan,
                request,
                project_id=self.project.id,
                project_revision=self.project.revision,
            )
            checkpoint_store = RenderCheckpointStore(self.config.cache_dir / "render-checkpoints")
            checkpoint, checkpoint_attempt_id = checkpoint_store.begin(
                identity=identity,
                signature=signature,
                compiled=compiled,
                project_id=self.project.id,
                project_revision=self.project.revision,
                resume=request.resume,
            )
            checkpoint_path = checkpoint_store.path_for(identity)
            self._validate_destinations(request.output_path, manifest_path, graph)
            destination_validated = True
            scheduler = RenderScheduler(
                backend_plan.by_node_id,
                RenderCache(self.config.cache_dir / "render-nodes"),
                max_workers=self.config.max_workers,
                use_cache=request.use_cache,
                publish_cache=request.use_cache or request.resume,
                resume_cache_keys=checkpoint.completed_cache_keys,
            )
            temp_root = self.config.temp_dir
            with TemporaryWorkspace(
                root=temp_root,
                prefix=f"{render_id}-",
                keep=self.config.keep_temporary_files,
            ) as workspace:
                scheduled = scheduler.execute(graph, workspace / "nodes")
                output_node_id = graph.outputs["main"]
                artifact = scheduled.artifacts[output_node_id]
                self._publish_output(artifact.path, request.output_path)
            output_sha = sha256_file(request.output_path)
        except Exception as raw_exc:
            exc = self._render_error(raw_exc)
            records = tuple(
                NodeExecutionRecord.model_validate(record)
                for record in exc.context.get("records", [])
            )
            if (
                checkpoint_store is not None
                and checkpoint is not None
                and checkpoint_attempt_id is not None
                and compiled is not None
            ):
                checkpoint = checkpoint_store.finish(
                    checkpoint,
                    checkpoint_attempt_id,
                    compiled,
                    records,
                    status="failed",
                    failure=exc.to_dict()["error"],
                )
            failure_path = (
                manifest_path
                if destination_validated
                else self.config.cache_dir.parent / "failures" / f"{render_id}.json"
            )
            failure_manifest = RenderManifest(
                render_id=render_id,
                project_id=self.project.id,
                project_revision=self.project.revision,
                sequence_id=(compiled.sequence_id if compiled else request.sequence_id)
                or self.project.active_sequence_id,
                graph_hash=graph.graph_hash if graph else "",
                backend=backend_plan.name if backend_plan else request.backend,
                backend_version=backend_plan.version if backend_plan else "unresolved",
                mode=request.mode,
                status="failed",
                output_path=request.output_path.resolve(),
                started_at=started,
                completed_at=datetime.now(UTC),
                records=records,
                failure=exc.to_dict()["error"],
                metadata=self._manifest_metadata(
                    compiled,
                    backend_plan,
                    request,
                    checkpoint,
                    checkpoint_path,
                    checkpoint_attempt_id,
                    approval,
                ),
            )
            self._write_manifest(failure_path, failure_manifest)
            raise EngineError(
                exc.code,
                exc.message,
                context={**exc.context, "manifest": str(failure_path.resolve())},
            ) from raw_exc
        completed = datetime.now(UTC)
        assert compiled is not None and graph is not None and backend_plan is not None
        assert checkpoint_store is not None
        assert checkpoint is not None and checkpoint_attempt_id is not None
        checkpoint = checkpoint_store.finish(
            checkpoint,
            checkpoint_attempt_id,
            compiled,
            scheduled.records,
            status="succeeded",
            output_sha256=output_sha,
        )
        manifest = RenderManifest(
            render_id=render_id,
            project_id=self.project.id,
            project_revision=self.project.revision,
            sequence_id=compiled.sequence_id,
            graph_hash=graph.graph_hash,
            backend=backend_plan.name,
            backend_version=backend_plan.version,
            mode=request.mode,
            output_path=request.output_path.resolve(),
            started_at=started,
            completed_at=completed,
            records=scheduled.records,
            output_sha256=output_sha,
            output_size_bytes=request.output_path.stat().st_size,
            metadata=self._manifest_metadata(
                compiled,
                backend_plan,
                request,
                checkpoint,
                checkpoint_path,
                checkpoint_attempt_id,
                approval,
            ),
        )
        self._write_manifest(manifest_path, manifest)
        return RenderResult(
            output_path=request.output_path.resolve(),
            manifest_path=manifest_path.resolve(),
            manifest=manifest,
            cache_hits=sum(record.cached for record in scheduled.records),
            executed_nodes=sum(record.status == "succeeded" for record in scheduled.records),
        )

    def execute_partial(
        self, request: RenderRequest, target_node_ids: tuple[str, ...]
    ) -> PartialRenderResult:
        """Execute and persist the ancestor closure for explicit DAG targets."""

        if not target_node_ids or len(target_node_ids) != len(set(target_node_ids)):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "partial render targets must be nonempty and unique",
            )
        compiled = self.compile(request)
        graph = compiled.graph.pruned()
        nodes = graph.node_map()
        missing = [node_id for node_id in target_node_ids if node_id not in nodes]
        noncacheable = [
            node_id
            for node_id in target_node_ids
            if node_id in nodes and not nodes[node_id].cacheable
        ]
        if missing or noncacheable:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "partial render targets must reference cacheable graph nodes",
                context={"missing": missing, "noncacheable": noncacheable},
            )
        plan = self.registry.plan(graph, request.backend)
        scheduler = RenderScheduler(
            plan.by_node_id,
            RenderCache(self.config.cache_dir / "render-nodes"),
            max_workers=self.config.max_workers,
            use_cache=request.use_cache,
            publish_cache=True,
        )
        with TemporaryWorkspace(
            root=self.config.temp_dir,
            prefix="partial-render-",
            keep=self.config.keep_temporary_files,
        ) as workspace:
            scheduled = scheduler.execute(
                graph,
                workspace / "nodes",
                targets=target_node_ids,
            )
        artifacts = {node_id: scheduled.artifacts[node_id] for node_id in target_node_ids}
        return PartialRenderResult(
            graph_hash=graph.graph_hash,
            target_node_ids=target_node_ids,
            artifacts=artifacts,
            records=scheduled.records,
            cache_hits=sum(record.cached for record in scheduled.records),
            executed_nodes=sum(record.status == "succeeded" for record in scheduled.records),
        )

    @staticmethod
    def _render_error(exc: Exception) -> EngineError:
        if isinstance(exc, EngineError):
            return exc
        if isinstance(exc, OSError):
            return EngineError(
                ErrorCode.STORAGE,
                "render storage operation failed",
                context={"detail": str(exc)},
            )
        return EngineError(
            ErrorCode.RENDER_FAILED,
            "render failed unexpectedly",
            context={"detail": str(exc), "type": type(exc).__name__},
        )

    def _manifest_metadata(
        self,
        compiled: CompiledRender | None,
        backend_plan: BackendPlan | None,
        request: RenderRequest,
        checkpoint: RenderCheckpoint | None,
        checkpoint_path: Path | None,
        checkpoint_attempt_id: str | None,
        approval: QCApproval | None,
    ) -> dict[str, JsonValue]:
        metadata: dict[str, JsonValue] = {
            "resume": request.resume,
            "use_cache": request.use_cache,
            "request_metadata": request.metadata,
            "caption_track_ids": (
                list(request.caption_track_ids) if request.caption_track_ids is not None else None
            ),
            "caption_languages": (
                list(request.caption_languages) if request.caption_languages is not None else None
            ),
            "chapter_id": request.chapter_id,
            "qc_approval": approval.model_dump(mode="json") if approval else None,
            "checkpoint": (
                {
                    "identity": checkpoint.identity,
                    "path": str(checkpoint_path.resolve()) if checkpoint_path is not None else None,
                    "status": checkpoint.status,
                    "attempt_id": checkpoint_attempt_id,
                    "attempt_count": len(checkpoint.attempts),
                }
                if checkpoint is not None
                else None
            ),
        }
        if compiled is not None:
            metadata.update(
                {
                    "delivery_profile_id": compiled.delivery_profile.id,
                    "delivery_profile": compiled.delivery_profile.model_dump(mode="json"),
                    "timeline_range": compiled.timeline_range.model_dump(mode="json"),
                    "sequence_revision": next(
                        sequence.revision
                        for sequence in self.project.sequences
                        if sequence.id == compiled.sequence_id
                    ),
                    "sections": [
                        {
                            **output.section.model_dump(mode="json"),
                            "video_node_id": output.video_node_id,
                            "audio_node_id": output.audio_node_id,
                        }
                        for output in compiled.section_outputs
                    ],
                }
            )
        if backend_plan is not None:
            try:
                metadata["tool_fingerprints"] = backend_plan.tool_fingerprints
            except EngineError as exc:
                metadata["tool_fingerprint_error"] = exc.to_dict()["error"]
        return metadata

    def _validate_approval(self, request: RenderRequest) -> QCApproval | None:
        if request.mode is not RenderMode.FINAL:
            return None
        if request.qc_approval_path is None:
            raise EngineError(
                ErrorCode.QC_FAILED,
                "final renders require a human-reviewed QC approval artifact",
                context={"required": "qc_approval_path"},
            )
        sequence_id = request.sequence_id or self.project.active_sequence_id
        return QCApprovalService().validate(
            self.project,
            sequence_id,
            request.qc_approval_path,
        )

    def _validate_destinations(
        self, output_path: Path, manifest_path: Path, graph: RenderGraph
    ) -> None:
        destinations = (output_path.resolve(), manifest_path.resolve())
        cache_root = self.config.cache_dir.resolve()
        if any(path == cache_root or path.is_relative_to(cache_root) for path in destinations):
            raise EngineError(
                ErrorCode.STORAGE,
                "render output cannot be written inside the engine cache",
                context={"paths": [str(path) for path in destinations]},
            )
        sources: list[Path] = []
        for node in graph.nodes:
            values: tuple[str, ...] = ()
            if isinstance(node, DecodeNode):
                values = (node.source_uri,)
            elif isinstance(node, GradeNode):
                values = (node.lut_path,) if node.lut_path else ()
            elif isinstance(node, CaptionNode):
                values = (node.subtitle_path,) if node.subtitle_path else ()
            elif isinstance(node, MotionGraphicNode):
                values = tuple(str(asset.source_path) for asset in node.assets)
            sources.extend(Path(value).resolve() for value in values)
        collisions = [
            {"destination": str(destination), "source": str(source)}
            for destination in destinations
            for source in sources
            if self._paths_alias(destination, source)
        ]
        if collisions:
            raise EngineError(
                ErrorCode.STORAGE,
                "render output collides with an input asset",
                context={"collisions": collisions},
            )

    @staticmethod
    def _paths_alias(first: Path, second: Path) -> bool:
        if first == second:
            return True
        if first.exists() and second.exists():
            try:
                return first.samefile(second)
            except OSError:
                return False
        return False

    @staticmethod
    def _publish_output(source: Path, destination: Path) -> None:
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            shutil.copy2(source, temporary)
            with temporary.open("rb+") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _write_manifest(path: Path, manifest: RenderManifest) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(
                    manifest.model_dump(mode="json"),
                    handle,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=True,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except (OSError, TypeError, ValueError) as exc:
            temporary.unlink(missing_ok=True)
            raise EngineError(
                code=ErrorCode.STORAGE,
                message="failed to write render manifest",
                context={"path": str(path), "detail": str(exc)},
            ) from exc
