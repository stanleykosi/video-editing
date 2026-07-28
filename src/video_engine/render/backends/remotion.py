"""Structured Remotion backend for canonical motion-graphic source nodes."""

from __future__ import annotations

import json
import os
import re
import shutil
from fractions import Fraction
from functools import cached_property
from pathlib import Path
from threading import BoundedSemaphore

from video_engine.config import EngineConfig
from video_engine.core.schema import JsonValue
from video_engine.errors import EngineError, ErrorCode
from video_engine.graphics.models import (
    GraphicCanvas,
    GraphicComponentRef,
    GraphicFrameRange,
    GraphicRenderer,
    GraphicRenderRequest,
    GraphicStagedAsset,
)
from video_engine.process import CommandRunner
from video_engine.render.backends.base import BackendExecution, RenderBackend
from video_engine.render.cache import sha256_file
from video_engine.render.models import RenderArtifact
from video_engine.render.nodes import MotionGraphicNode, NodeKind, RenderNode


class RemotionBackend(RenderBackend):
    name = "remotion"
    version = "1.0.0"
    capabilities = frozenset({NodeKind.MOTION_GRAPHIC})

    def __init__(
        self,
        config: EngineConfig,
        project_root: Path,
        runner: CommandRunner | None = None,
    ) -> None:
        self.config = config
        self.project_root = project_root.resolve()
        self.runner = runner or CommandRunner()
        self.bridge_root = Path(__file__).resolve().parents[2] / "graphics" / "remotion"
        self.runner_path = self.bridge_root / "runner.mjs"
        self._render_slots = BoundedSemaphore(self.config.remotion_max_workers)

    @cached_property
    def tool_root(self) -> Path:
        return self._tool_root()

    def _tool_root(self) -> Path:
        if self.config.remotion_root is not None:
            candidate = self.config.remotion_root.resolve()
            if (candidate / "package.json").is_file() and (candidate / "node_modules").is_dir():
                return candidate
            raise EngineError(
                ErrorCode.DEPENDENCY_MISSING,
                "configured Remotion package root is incomplete",
                context={"path": str(candidate)},
            )
        for candidate in self.bridge_root.parents:
            if (candidate / "package.json").is_file() and (candidate / "node_modules").is_dir():
                return candidate
        raise EngineError(
            ErrorCode.DEPENDENCY_MISSING,
            "Remotion package root could not be discovered",
            context={"bridge_root": str(self.bridge_root)},
        )

    @cached_property
    def browser_path(self) -> Path:
        if self.config.remotion_browser_path is not None:
            candidate = self.config.remotion_browser_path.resolve()
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
            raise EngineError(
                ErrorCode.DEPENDENCY_MISSING,
                "configured Remotion browser is missing or not executable",
                context={"path": str(candidate)},
            )
        patterns = (
            Path.home() / ".cache" / "ms-playwright",
            self.tool_root / "node_modules" / ".remotion",
        )
        candidates: list[Path] = []
        for root in patterns:
            if root.is_dir():
                candidates.extend(root.glob("**/chrome-headless-shell"))
                candidates.extend(root.glob("**/headless_shell"))
        for candidate in sorted(candidates, reverse=True):
            resolved = candidate.resolve()
            if resolved.is_file() and os.access(resolved, os.X_OK):
                return resolved
        raise EngineError(
            ErrorCode.DEPENDENCY_MISSING,
            "Remotion requires a configured Chrome headless-shell",
            context={"environment": "VIDEO_ENGINE_REMOTION_BROWSER"},
        )

    @cached_property
    def tool_fingerprint(self) -> str:
        if not self.runner_path.is_file():
            raise EngineError(
                ErrorCode.DEPENDENCY_MISSING,
                "Remotion bridge runner is missing",
                context={"path": str(self.runner_path)},
            )
        node = self.runner.run([self.config.node_path, "--version"]).stdout.strip()
        versions: list[str] = []
        for package_name in ("@remotion/renderer", "@remotion/bundler", "remotion"):
            package_path = self.tool_root / "node_modules" / package_name / "package.json"
            try:
                version = json.loads(package_path.read_text(encoding="utf-8"))["version"]
            except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
                raise EngineError(
                    ErrorCode.DEPENDENCY_MISSING,
                    "installed Remotion package metadata is unavailable",
                    context={"package": package_name, "path": str(package_path)},
                ) from exc
            versions.append(f"{package_name}={version}")
        lockfile = self.tool_root / "package-lock.json"
        lock_hash = sha256_file(lockfile) if lockfile.is_file() else "missing"
        browser = self.browser_path
        return (
            f"node={node};{'|'.join(versions)};lock={lock_hash};"
            f"browser={sha256_file(browser)};"
            "chrome_mode=headless-shell;gl=swiftshader"
        )

    def can_execute(self, node: RenderNode) -> bool:
        return isinstance(node, MotionGraphicNode) and node.renderer is GraphicRenderer.REMOTION

    def output_suffix(self, node: RenderNode) -> str:
        if not isinstance(node, MotionGraphicNode):
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "Remotion backend only renders motion graphic nodes",
                context={"node_type": node.node_type.value},
            )
        return ".mov"

    def execute(
        self,
        node: RenderNode,
        inputs: tuple[RenderArtifact, ...],
        output_path: Path,
        work_dir: Path,
    ) -> BackendExecution:
        if not isinstance(node, MotionGraphicNode) or inputs:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "Remotion requires one zero-input motion graphic node",
            )
        public_dir = work_dir / "public"
        public_dir.mkdir(parents=True, exist_ok=False)
        staged_assets: list[GraphicStagedAsset] = []
        for asset in node.assets:
            source_path = asset.source_path
            source = source_path.resolve()
            if source_path.is_symlink() or not source.is_file():
                raise EngineError(
                    ErrorCode.MEDIA_NOT_FOUND,
                    "graphic asset is missing or is a symbolic link",
                    context={"asset_id": asset.id, "path": str(source)},
                )
            actual_hash = sha256_file(source)
            if actual_hash != asset.sha256:
                raise EngineError(
                    ErrorCode.MEDIA_INVALID,
                    "graphic asset hash mismatch",
                    context={"asset_id": asset.id, "path": str(source)},
                )
            shutil.copy2(source, public_dir / asset.staged_name)
            staged_assets.append(
                GraphicStagedAsset(
                    id=asset.id,
                    sha256=asset.sha256,
                    media_type=asset.media_type,
                    staged_name=asset.staged_name,
                )
            )
        request = GraphicRenderRequest(
            component=GraphicComponentRef(
                id=node.component_id,
                version=node.component_version,
                source_digest=node.component_digest,
            ),
            canvas=GraphicCanvas(
                width=node.width,
                height=node.height,
                frame_rate=node.frame_rate,
                duration_frames=node.composition_duration_frames,
            ),
            render_range=GraphicFrameRange(
                start_frame=node.render_start_frame,
                end_frame_exclusive=(node.render_start_frame + node.render_duration_frames),
            ),
            props=node.props,
            assets=tuple(staged_assets),
            transparent=node.transparent,
        )
        request_path = work_dir / "request.json"
        request_path.write_text(
            json.dumps(
                request.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        expected_output = work_dir / "output.mov"
        if output_path != expected_output:
            raise EngineError(
                ErrorCode.STORAGE,
                "Remotion output path must be confined to its node workspace",
            )
        with self._render_slots:
            self.runner.run(
                [
                    self.config.node_path,
                    str(self.runner_path),
                    "--job-root",
                    str(work_dir),
                    "--browser",
                    str(self.browser_path),
                    "--timeout-ms",
                    str(self.config.remotion_browser_timeout_seconds * 1000),
                ],
                cwd=self.tool_root,
                timeout=self.config.remotion_timeout_seconds,
            )
        if not output_path.is_file():
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "Remotion did not produce its declared output",
                context={"path": str(output_path)},
            )
        output_metadata = self._validate_output(node, output_path)
        bounds_metadata = self._alpha_bounds(node, output_path, work_dir)
        return BackendExecution(
            path=output_path,
            metadata={
                "component_id": node.component_id,
                "component_version": node.component_version,
                "component_digest": node.component_digest,
                "browser_sha256": sha256_file(self.browser_path),
                "render_start_frame": node.render_start_frame,
                "render_duration_frames": node.render_duration_frames,
                "transparent": node.transparent,
                **output_metadata,
                "content_bounds": bounds_metadata,
            },
        )

    def _alpha_bounds(
        self,
        node: MotionGraphicNode,
        output_path: Path,
        work_dir: Path,
    ) -> dict[str, JsonValue]:
        if not node.transparent:
            return {
                "available": True,
                "method": "opaque-full-frame",
                "frames_analyzed": node.render_duration_frames,
                "frame_bounds_count": node.render_duration_frames,
                "edge_touch_frames": node.render_duration_frames,
                "union": {
                    "x": 0,
                    "y": 0,
                    "width": node.width,
                    "height": node.height,
                },
            }
        telemetry_path = work_dir / "alpha-bounds.txt"
        filter_graph = (
            "alphaextract,cropdetect=limit=1:round=1:reset=1,"
            f"metadata=mode=print:file={telemetry_path}"
        )
        self.runner.run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                output_path,
                "-vf",
                filter_graph,
                "-an",
                "-f",
                "null",
                "-",
            ]
        )
        records: list[dict[str, int]] = []
        current: dict[str, int] = {}
        try:
            lines = telemetry_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "Remotion alpha-bounds telemetry was not produced",
                context={"path": str(telemetry_path)},
            ) from exc
        for line in lines:
            if line.startswith("frame:"):
                if {"x1", "x2", "y1", "y2"} <= current.keys():
                    records.append(current)
                current = {}
                continue
            match = re.fullmatch(r"lavfi\.cropdetect\.(x1|x2|y1|y2)=(-?\d+)", line)
            if match:
                current[match.group(1)] = int(match.group(2))
        if {"x1", "x2", "y1", "y2"} <= current.keys():
            records.append(current)
        edge_touch_frames = sum(
            record["x1"] <= 0
            or record["y1"] <= 0
            or record["x2"] >= node.width - 1
            or record["y2"] >= node.height - 1
            for record in records
        )
        union: dict[str, JsonValue] | None = None
        if records:
            x1 = min(record["x1"] for record in records)
            y1 = min(record["y1"] for record in records)
            x2 = max(record["x2"] for record in records)
            y2 = max(record["y2"] for record in records)
            union = {
                "x": x1,
                "y": y1,
                "width": x2 - x1 + 1,
                "height": y2 - y1 + 1,
            }
        return {
            "available": True,
            "method": "alpha-cropdetect-v1",
            "frames_analyzed": node.render_duration_frames,
            "frame_bounds_count": len(records),
            "edge_touch_frames": edge_touch_frames,
            "union": union,
        }

    def _validate_output(
        self, node: MotionGraphicNode, output_path: Path
    ) -> dict[str, str | int | bool]:
        result = self.runner.run(
            [
                self.config.ffprobe_path,
                "-v",
                "error",
                "-count_frames",
                "-select_streams",
                "v:0",
                "-show_entries",
                ("stream=codec_name,width,height,pix_fmt,avg_frame_rate,nb_read_frames,duration"),
                "-of",
                "json",
                str(output_path),
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
            duration = Fraction(str(stream["duration"]))
        except (IndexError, KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "Remotion output metadata is incomplete",
                context={"path": str(output_path), "probe": result.stdout[-4000:]},
            ) from exc
        expected_rate = Fraction(node.frame_rate.numerator, node.frame_rate.denominator)
        expected_duration = Fraction(
            node.render_duration_frames * node.frame_rate.denominator,
            node.frame_rate.numerator,
        )
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
        if abs(duration - expected_duration) > Fraction(
            node.frame_rate.denominator, node.frame_rate.numerator * 2
        ):
            problems.append("duration")
        if problems:
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "Remotion output violates its node contract",
                context={
                    "path": str(output_path),
                    "problems": problems,
                    "stream": stream,
                },
            )
        return {
            "codec": codec,
            "pixel_format": pixel_format,
            "width": width,
            "height": height,
            "frame_count": frame_count,
            "has_alpha": pixel_format.startswith("yuva444p"),
        }
