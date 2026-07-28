"""Canonical Manim scene backend for technical and mathematical animation."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from video_engine.errors import EngineError, ErrorCode
from video_engine.graphics.models import GraphicRenderer, ManimSceneProps
from video_engine.render.backends.base import BackendExecution
from video_engine.render.backends.external_graphics import ExternalMotionGraphicBackend
from video_engine.render.models import RenderArtifact
from video_engine.render.nodes import RenderNode


class ManimBackend(ExternalMotionGraphicBackend):
    name = "manim"
    version = "1.0.0"
    renderer = GraphicRenderer.MANIM

    @cached_property
    def tool_fingerprint(self) -> str:
        result = self.runner.run([self.config.manim_path, "--version"])
        version = next(
            (line.strip() for line in result.stdout.splitlines() if line.strip()), "unknown"
        )
        return f"{version};adapter={self.version}"

    def execute(
        self,
        node: RenderNode,
        inputs: tuple[RenderArtifact, ...],
        output_path: Path,
        work_dir: Path,
    ) -> BackendExecution:
        graphic = self._node(node)
        if inputs:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "Manim requires a zero-input motion graphic node",
            )
        props = ManimSceneProps.model_validate(graphic.props)
        project_dir = work_dir / "project"
        source = self._stage_project(graphic, props, project_dir, source_name="scene.py")
        media_dir = work_dir / "media"
        command: list[str | Path] = [
            self.config.manim_path,
            "render",
            "--disable_caching",
            "--progress_bar",
            "none",
            "--media_dir",
            media_dir,
            "--renderer",
            props.renderer,
            "--fps",
            str(float(graphic.frame_rate.fraction)),
            "--resolution",
            f"{graphic.width},{graphic.height}",
            "--output_file",
            "video_engine_scene",
            "--seed",
            str(props.seed),
        ]
        if graphic.transparent:
            command.append("--transparent")
        command.extend((source, props.scene_name))
        self.runner.run(
            command,
            cwd=project_dir,
            timeout=self.config.manim_timeout_seconds,
        )
        candidates = sorted(
            path
            for path in media_dir.rglob("video_engine_scene.*")
            if path.is_file() and path.suffix.lower() in {".mov", ".mp4", ".webm"}
        )
        if len(candidates) != 1:
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "Manim did not produce one unambiguous scene output",
                context={"media_dir": str(media_dir), "candidates": [str(p) for p in candidates]},
            )
        self._conform_range(graphic, candidates[0], output_path, work_dir)
        return self._result(
            graphic,
            output_path,
            {"scene_name": props.scene_name, "manim_renderer": props.renderer},
        )
