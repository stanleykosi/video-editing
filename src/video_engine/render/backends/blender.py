"""Canonical Blender scene backend for 3D and physically rendered graphics."""

from __future__ import annotations

from fractions import Fraction
from functools import cached_property
from pathlib import Path

from video_engine.errors import EngineError, ErrorCode
from video_engine.graphics.models import BlenderSceneProps, GraphicRenderer
from video_engine.render.backends.base import BackendExecution
from video_engine.render.backends.external_graphics import ExternalMotionGraphicBackend
from video_engine.render.models import RenderArtifact
from video_engine.render.nodes import RenderNode


class BlenderBackend(ExternalMotionGraphicBackend):
    name = "blender"
    version = "1.0.0"
    renderer = GraphicRenderer.BLENDER

    @cached_property
    def tool_fingerprint(self) -> str:
        result = self.runner.run([self.config.blender_path, "--version"])
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
                "Blender requires a zero-input motion graphic node",
            )
        self._validate_output_destination(output_path, work_dir)
        props = BlenderSceneProps.model_validate(graphic.props)
        project_dir = work_dir / "project"
        source = self._stage_project(graphic, props, project_dir, source_name="scene.blend")
        frames_dir = work_dir / "frames"
        frames_dir.mkdir()
        start_frame = props.source_start_frame + graphic.render_start_frame
        end_frame = start_frame + graphic.render_duration_frames - 1
        expression = self._configuration_expression(
            graphic.width,
            graphic.height,
            graphic.frame_rate.numerator,
            graphic.frame_rate.denominator,
            start_frame,
            end_frame,
            frames_dir / "frame_",
            props,
            graphic.transparent,
        )
        command: list[str | Path] = [self.config.blender_path, "-b", source]
        if props.scene_name is not None:
            command.extend(("-S", props.scene_name))
        command.extend(("--python-expr", expression, "-a"))
        self.runner.run(
            command,
            cwd=project_dir,
            timeout=self.config.blender_timeout_seconds,
        )
        rate = f"{graphic.frame_rate.numerator}/{graphic.frame_rate.denominator}"
        self.runner.run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-framerate",
                rate,
                "-start_number",
                str(start_frame),
                "-i",
                frames_dir / "frame_%04d.png",
                "-frames:v",
                str(graphic.render_duration_frames),
                "-vf",
                f"scale={graphic.width}:{graphic.height}:flags=lanczos,format=yuva444p10le",
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
        return self._result(
            graphic,
            output_path,
            {
                "scene_name": props.scene_name,
                "camera_name": props.camera_name,
                "render_engine": props.render_engine,
                "source_start_frame": start_frame,
            },
        )

    @staticmethod
    def _configuration_expression(
        width: int,
        height: int,
        fps_numerator: int,
        fps_denominator: int,
        start_frame: int,
        end_frame: int,
        output_prefix: Path,
        props: BlenderSceneProps,
        transparent: bool,
    ) -> str:
        statements = [
            "import bpy",
            "s=bpy.context.scene",
            f"s.render.resolution_x={width}",
            f"s.render.resolution_y={height}",
            "s.render.resolution_percentage=100",
            f"s.render.fps={round(Fraction(fps_numerator, fps_denominator))}",
            (
                "s.render.fps_base="
                f"{round(Fraction(fps_numerator, fps_denominator)) * fps_denominator}"
                f"/{fps_numerator}"
            ),
            f"s.frame_start={start_frame}",
            f"s.frame_end={end_frame}",
            f"s.render.filepath={str(output_prefix)!r}",
            "s.render.image_settings.file_format='PNG'",
            "s.render.image_settings.color_mode='RGBA'",
            f"s.render.film_transparent={transparent!r}",
            f"s.render.engine={props.render_engine!r}",
        ]
        if props.camera_name is not None:
            statements.append(f"s.camera=bpy.data.objects[{props.camera_name!r}]")
        if props.render_engine == "CYCLES":
            statements.append(f"s.cycles.samples={props.samples}")
        else:
            statements.append("s.render.image_settings.color_depth='8'")
        return ";".join(statements)
