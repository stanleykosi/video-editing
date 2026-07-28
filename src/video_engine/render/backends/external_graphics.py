"""Shared confinement, conformance, and validation for external graphics tools."""

from __future__ import annotations

import json
import shutil
from abc import abstractmethod
from fractions import Fraction
from pathlib import Path

from video_engine.config import EngineConfig
from video_engine.core.schema import JsonValue
from video_engine.errors import EngineError, ErrorCode
from video_engine.graphics.models import ExternalCompositionProps, GraphicAsset, GraphicRenderer
from video_engine.process import CommandRunner
from video_engine.render.backends.base import BackendExecution, RenderBackend
from video_engine.render.cache import sha256_file
from video_engine.render.models import RenderArtifact
from video_engine.render.nodes import MotionGraphicNode, NodeKind, RenderNode


class ExternalMotionGraphicBackend(RenderBackend):
    """Base for trusted source-code/project graphics renderers."""

    capabilities = frozenset({NodeKind.MOTION_GRAPHIC})
    renderer: GraphicRenderer

    def __init__(
        self,
        config: EngineConfig,
        project_root: Path,
        runner: CommandRunner | None = None,
    ) -> None:
        self.config = config
        self.project_root = project_root.resolve()
        self.runner = runner or CommandRunner()

    def can_execute(self, node: RenderNode) -> bool:
        return isinstance(node, MotionGraphicNode) and node.renderer is self.renderer

    def output_suffix(self, node: RenderNode) -> str:
        self._node(node)
        return ".mov"

    def _node(self, node: RenderNode) -> MotionGraphicNode:
        if not isinstance(node, MotionGraphicNode) or node.renderer is not self.renderer:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                f"{self.name} backend only accepts its declared motion graphics",
                context={"node_type": node.node_type.value},
            )
        return node

    @staticmethod
    def _asset_map(node: MotionGraphicNode) -> dict[str, GraphicAsset]:
        return {asset.id: asset for asset in node.assets}

    def _stage_project(
        self,
        node: MotionGraphicNode,
        props: ExternalCompositionProps,
        project_dir: Path,
        *,
        source_name: str,
    ) -> Path:
        project_dir.mkdir(parents=True, exist_ok=False)
        assets = self._asset_map(node)
        source_asset = assets.get(props.source_asset_id)
        if source_asset is None:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "external graphic source asset is not declared",
                context={"asset_id": props.source_asset_id},
            )
        source = self._verified_asset(source_asset)
        staged_source = project_dir / source_name
        shutil.copy2(source, staged_source)
        claimed_ids = {props.source_asset_id}
        for relative_path, asset_id in props.asset_bindings.items():
            asset = assets.get(asset_id)
            if asset is None:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "external graphic binding references an undeclared asset",
                    context={"asset_id": asset_id, "relative_path": relative_path},
                )
            target = (project_dir / relative_path).resolve()
            if not target.is_relative_to(project_dir.resolve()):
                raise EngineError(
                    ErrorCode.STORAGE,
                    "external graphic binding escapes its project directory",
                    context={"relative_path": relative_path},
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self._verified_asset(asset), target)
            claimed_ids.add(asset_id)
        unbound = sorted(set(assets) - claimed_ids)
        if unbound:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "external graphic declares assets without confined bindings",
                context={"asset_ids": unbound},
            )
        return staged_source

    @staticmethod
    def _verified_asset(asset: GraphicAsset) -> Path:
        source_path = asset.source_path
        source = source_path.resolve()
        if source_path.is_symlink() or not source.is_file():
            raise EngineError(
                ErrorCode.MEDIA_NOT_FOUND,
                "external graphic asset is missing or is a symbolic link",
                context={"asset_id": asset.id, "path": str(source)},
            )
        actual_hash = sha256_file(source)
        if actual_hash != asset.sha256:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "external graphic asset hash mismatch",
                context={"asset_id": asset.id, "path": str(source)},
            )
        return source

    def _conform_range(
        self,
        node: MotionGraphicNode,
        source: Path,
        output_path: Path,
        work_dir: Path,
    ) -> None:
        self._validate_output_destination(output_path, work_dir)
        rate = f"{node.frame_rate.numerator}/{node.frame_rate.denominator}"
        filter_graph = (
            f"trim=start_frame={node.render_start_frame}:"
            f"end_frame={node.render_start_frame + node.render_duration_frames},"
            "setpts=PTS-STARTPTS,"
            f"fps={rate},scale={node.width}:{node.height}:flags=lanczos,"
            "format=yuva444p10le"
        )
        self.runner.run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                source,
                "-vf",
                filter_graph,
                "-frames:v",
                str(node.render_duration_frames),
                "-an",
                "-c:v",
                "prores_ks",
                "-profile:v",
                "4",
                "-pix_fmt",
                "yuva444p10le",
                output_path,
            ]
        )

    @staticmethod
    def _validate_output_destination(output_path: Path, work_root: Path) -> None:
        resolved_output = output_path.resolve()
        resolved_root = work_root.resolve()
        if not resolved_output.is_relative_to(resolved_root):
            raise EngineError(
                ErrorCode.STORAGE,
                "external graphics output escapes its render workspace",
                context={"path": str(resolved_output), "workspace": str(resolved_root)},
            )

    def _validate_output(self, node: MotionGraphicNode, output_path: Path) -> dict[str, JsonValue]:
        result = self.runner.run(
            [
                self.config.ffprobe_path,
                "-v",
                "error",
                "-count_frames",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name,width,height,pix_fmt,avg_frame_rate,nb_read_frames,duration",
                "-of",
                "json",
                output_path,
            ]
        )
        try:
            stream = json.loads(result.stdout)["streams"][0]
            width = int(stream["width"])
            height = int(stream["height"])
            frame_rate = Fraction(str(stream["avg_frame_rate"]))
            frame_count = int(stream["nb_read_frames"])
            codec = str(stream["codec_name"])
            pixel_format = str(stream["pix_fmt"])
        except (IndexError, KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "external graphics output metadata is incomplete",
                context={"path": str(output_path), "probe": result.stdout[-4000:]},
            ) from exc
        expected_rate = Fraction(node.frame_rate.numerator, node.frame_rate.denominator)
        problems: list[str] = []
        if (width, height) != (node.width, node.height):
            problems.append("dimensions")
        if frame_rate != expected_rate:
            problems.append("frame_rate")
        if frame_count != node.render_duration_frames:
            problems.append("frame_count")
        if codec != "prores":
            problems.append("codec")
        if node.transparent and not pixel_format.startswith("yuva444p"):
            problems.append("alpha_pixel_format")
        if problems:
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "external graphics output violates its node contract",
                context={"path": str(output_path), "problems": problems, "stream": stream},
            )
        return {
            "codec": codec,
            "pixel_format": pixel_format,
            "width": width,
            "height": height,
            "frame_count": frame_count,
            "has_alpha": pixel_format.startswith("yuva444p"),
        }

    def _result(
        self,
        node: MotionGraphicNode,
        output_path: Path,
        metadata: dict[str, JsonValue],
    ) -> BackendExecution:
        return BackendExecution(
            path=output_path,
            metadata={
                "component_id": node.component_id,
                "component_version": node.component_version,
                "component_digest": node.component_digest,
                "renderer": self.name,
                "render_start_frame": node.render_start_frame,
                "render_duration_frames": node.render_duration_frames,
                "transparent": node.transparent,
                **self._validate_output(node, output_path),
                **metadata,
            },
        )

    @abstractmethod
    def execute(
        self,
        node: RenderNode,
        inputs: tuple[RenderArtifact, ...],
        output_path: Path,
        work_dir: Path,
    ) -> BackendExecution:
        raise NotImplementedError
