"""Typed FFmpeg lowering for canonical render nodes."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from fractions import Fraction
from functools import cached_property
from itertools import pairwise
from pathlib import Path

from video_engine.captions.ass import write_ass
from video_engine.config import EngineConfig
from video_engine.core.schema import ColorSpace, Interpolation, JsonValue, Retime
from video_engine.core.time import AudioSampleTime, RationalTime, RoundingMode
from video_engine.errors import EngineError, ErrorCode
from video_engine.process import CommandRunner
from video_engine.render.backends.base import BackendExecution, RenderBackend
from video_engine.render.cache import sha256_file
from video_engine.render.models import RenderArtifact
from video_engine.render.nodes import (
    ALL_NODE_KINDS,
    ArtifactType,
    AudioAutomationPoint,
    AudioMixNode,
    AudioProcessNode,
    AudioSidechainNode,
    BlurNode,
    CaptionNode,
    ColorConversionNode,
    CompositeNode,
    ConcatNode,
    ConformNode,
    CropNode,
    DecodeNode,
    DistortionNode,
    EncodeNode,
    FreezeNode,
    GlowNode,
    GradeNode,
    LoudnessNode,
    MaskNode,
    MotionGraphicNode,
    MuxNode,
    OutputTransformNode,
    PerspectiveNode,
    RenderNode,
    ReverseNode,
    ScaleNode,
    ShadowNode,
    SpeedNode,
    SpeedRampNode,
    TransformNode,
    TransitionNode,
    TrimNode,
    VisualAutomationPoint,
)


def _seconds(value: RationalTime) -> float:
    return float(value.fraction)


def _number(value: float) -> str:
    return f"{value:.9f}".rstrip("0").rstrip(".") or "0"


def _rational_expression(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"({value.numerator}/{value.denominator})"


def _escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'")


def _float_parameter(parameters: dict[str, JsonValue], key: str, default: float) -> float:
    value = parameters.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "audio processor parameter must be numeric",
            context={"parameter": key, "value": value},
        )
    try:
        return float(value)
    except ValueError as exc:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "audio processor parameter must be numeric",
            context={"parameter": key, "value": value},
        ) from exc


def _int_parameter(parameters: dict[str, JsonValue], key: str, default: int) -> int:
    value = _float_parameter(parameters, key, float(default))
    if not value.is_integer():
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "audio processor parameter must be an integer",
            context={"parameter": key, "value": value},
        )
    return int(value)


def _string_parameter(parameters: dict[str, JsonValue], key: str, default: str) -> str:
    value = parameters.get(key, default)
    if not isinstance(value, str):
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "audio processor parameter must be a string",
            context={"parameter": key, "value": value},
        )
    return value


def _rational_parameter(
    parameters: dict[str, JsonValue], key: str, default: RationalTime
) -> RationalTime:
    value = parameters.get(key)
    if value is None:
        return default
    try:
        return RationalTime.model_validate(value)
    except (ValueError, TypeError) as exc:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "audio processor time parameter must be rational",
            context={"parameter": key, "value": value},
        ) from exc


class FFmpegBackend(RenderBackend):
    name = "ffmpeg"
    version = "1.6.0"
    capabilities = ALL_NODE_KINDS
    intermediate_pixel_format = "yuva444p10le"

    def __init__(self, config: EngineConfig, runner: CommandRunner | None = None) -> None:
        self.config = config
        self.runner = runner or CommandRunner()

    @cached_property
    def tool_fingerprint(self) -> str:
        version = self.runner.run([self.config.ffmpeg_path, "-version"]).stdout
        filters = self.runner.run([self.config.ffmpeg_path, "-hide_banner", "-filters"]).stdout
        encoders = self.runner.run([self.config.ffmpeg_path, "-hide_banner", "-encoders"]).stdout
        digest = hashlib.sha256(
            (version + "\0" + filters + "\0" + encoders).encode("utf-8")
        ).hexdigest()
        first_line = version.splitlines()[0] if version else "unknown"
        return f"{first_line.strip()};capabilities_sha256={digest}"

    def can_execute(self, node: RenderNode) -> bool:
        if not super().can_execute(node):
            return False
        if isinstance(node, SpeedNode):
            return self._supported_tempo(float(node.rate.fraction))
        if isinstance(node, SpeedRampNode):
            return all(self._supported_tempo(float(point.rate.fraction)) for point in node.points)
        return not isinstance(node, MotionGraphicNode)

    def output_suffix(self, node: RenderNode) -> str:
        if isinstance(node, DecodeNode):
            return Path(node.source_uri).suffix or ".bin"
        if node.artifact_type is ArtifactType.AUDIO:
            return ".wav"
        if node.artifact_type is ArtifactType.ENCODED_AUDIO:
            return ".m4a"
        if node.artifact_type is ArtifactType.ENCODED_VIDEO:
            return ".mp4"
        if node.artifact_type in {ArtifactType.IMAGE, ArtifactType.MASK}:
            return ".png"
        if node.artifact_type is ArtifactType.SUBTITLE:
            return ".ass"
        if isinstance(node, MuxNode):
            return f".{node.container}"
        return ".mkv"

    def execute(
        self,
        node: RenderNode,
        inputs: tuple[RenderArtifact, ...],
        output_path: Path,
        work_dir: Path,
    ) -> BackendExecution:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(node, DecodeNode):
            return self._decode(node)
        if isinstance(node, TrimNode):
            return self._trim(node, inputs[0], output_path)
        if isinstance(node, ConformNode):
            return self._conform(node, inputs[0], output_path)
        if isinstance(node, ScaleNode):
            return self._scale(node, inputs[0], output_path)
        if isinstance(node, CropNode):
            return self._crop(node, inputs[0], output_path)
        if isinstance(node, TransformNode):
            return self._transform(node, inputs[0], output_path)
        if isinstance(node, SpeedNode):
            return self._speed(node, inputs[0], output_path)
        if isinstance(node, SpeedRampNode):
            return self._speed_ramp(node, inputs[0], output_path, work_dir)
        if isinstance(node, ReverseNode):
            return self._reverse(node, inputs[0], output_path)
        if isinstance(node, FreezeNode):
            return self._freeze(node, inputs[0], output_path)
        if isinstance(node, ColorConversionNode):
            return self._video_filter(node, inputs[0], output_path, self._color_filter(node))
        if isinstance(node, GradeNode):
            return self._video_filter(node, inputs[0], output_path, self._grade_filter(node))
        if isinstance(node, MaskNode):
            return self._mask(node, inputs, output_path)
        if isinstance(node, BlurNode):
            return self._blur(node, inputs[0], output_path)
        if isinstance(node, ShadowNode):
            return self._shadow(node, inputs[0], output_path)
        if isinstance(node, GlowNode):
            return self._glow(node, inputs[0], output_path)
        if isinstance(node, PerspectiveNode):
            return self._perspective(node, inputs[0], output_path)
        if isinstance(node, DistortionNode):
            interpolation = 1 if node.interpolation == "bilinear" else 0
            return self._video_filter(
                node,
                inputs[0],
                output_path,
                f"lenscorrection=cx={_number(node.center_x)}:cy={_number(node.center_y)}:"
                f"k1={_number(node.quadratic)}:k2={_number(node.double_quadratic)}:"
                f"i={interpolation}:fc=black@0,format=yuva444p10le",
            )
        if isinstance(node, CompositeNode):
            return self._composite(node, inputs, output_path, work_dir)
        if isinstance(node, ConcatNode):
            return self._concat(node, inputs, output_path)
        if isinstance(node, TransitionNode):
            return self._transition(node, inputs, output_path)
        if isinstance(node, CaptionNode):
            return self._caption(node, inputs[0], output_path, work_dir)
        if isinstance(node, AudioProcessNode):
            return self._audio_process(node, inputs[0], output_path)
        if isinstance(node, AudioSidechainNode):
            return self._audio_sidechain(node, inputs, output_path)
        if isinstance(node, AudioMixNode):
            return self._audio_mix(node, inputs, output_path, work_dir)
        if isinstance(node, LoudnessNode):
            return self._loudness(node, inputs[0], output_path)
        if isinstance(node, OutputTransformNode):
            return self._output_transform(node, inputs[0], output_path)
        if isinstance(node, EncodeNode):
            return self._encode(node, inputs[0], output_path)
        if isinstance(node, MuxNode):
            return self._mux(node, inputs, output_path)
        raise EngineError(
            ErrorCode.UNSUPPORTED_CAPABILITY,
            "FFmpeg node lowering is unavailable",
            context={"node_id": node.id, "node_type": node.node_type.value},
        )

    def _run(self, command: list[str]) -> None:
        self.runner.run(command)

    def _decode(self, node: DecodeNode) -> BackendExecution:
        source = Path(node.snapshot_uri or node.source_uri).resolve()
        if not source.is_file():
            raise EngineError(
                ErrorCode.MEDIA_NOT_FOUND,
                "decode source does not exist",
                context={"node_id": node.id, "path": str(source)},
            )
        if node.source_sha256 and sha256_file(source) != node.source_sha256:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "decode snapshot does not match its declared source identity",
                context={"node_id": node.id, "path": str(source)},
            )
        if node.stream_metadata:
            return BackendExecution(path=source, metadata=node.stream_metadata)
        stream_type = "v" if node.artifact_type in {ArtifactType.VIDEO, ArtifactType.IMAGE} else "a"
        selector = (
            f"v:{node.video_stream_index or 0}"
            if stream_type == "v"
            else f"a:{node.audio_stream_index or 0}"
        )
        result = self.runner.run(
            [
                self.config.ffprobe_path,
                "-v",
                "error",
                "-select_streams",
                selector,
                "-show_entries",
                "stream=index,sample_rate,pix_fmt,color_primaries,color_transfer,color_space",
                "-of",
                "json",
                str(source),
            ],
            check=False,
        )
        try:
            probe = json.loads(result.stdout)
            streams = probe.get("streams", [])
        except (json.JSONDecodeError, AttributeError):
            streams = []
        if result.return_code != 0 or not streams:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "requested media stream is missing",
                context={"node_id": node.id, "path": str(source), "stream": selector},
            )
        stream = streams[0]
        metadata: dict[str, JsonValue] = {"stream": selector}
        if stream.get("sample_rate") is not None:
            metadata["sample_rate"] = int(stream["sample_rate"])
        for key in ("pix_fmt", "color_primaries", "color_transfer", "color_space"):
            if stream.get(key) is not None:
                metadata[key] = str(stream[key])
        return BackendExecution(path=source, metadata=metadata)

    def _trim(self, node: TrimNode, source: RenderArtifact, output: Path) -> BackendExecution:
        start = _seconds(node.source_range.start)
        duration = _seconds(node.source_range.duration)
        if source.artifact_type is ArtifactType.IMAGE:
            command = [
                self.config.ffmpeg_path,
                "-y",
                "-loop",
                "1",
                "-i",
                str(source.path),
                "-map",
                f"0:{source.metadata.get('stream', 'v:0')}",
                "-t",
                _number(duration),
                "-vf",
                "setpts=PTS-STARTPTS",
                "-an",
                *self._intermediate_video_args(),
                str(output),
            ]
        elif node.artifact_type is ArtifactType.AUDIO:
            probed_sample_rate = source.metadata.get("sample_rate")
            fallback_sample_rate = (
                int(probed_sample_rate)
                if isinstance(probed_sample_rate, (str, int, float))
                and not isinstance(probed_sample_rate, bool)
                else 48_000
            )
            sample_rate = node.audio_sample_rate or (fallback_sample_rate)
            start_sample = AudioSampleTime.from_time(
                node.source_range.start, sample_rate, node.audio_rounding
            ).samples
            end_sample = AudioSampleTime.from_time(
                node.source_range.end, sample_rate, node.audio_rounding
            ).samples
            duration_samples = end_sample - start_sample
            fade_in_samples = min(
                AudioSampleTime.from_time(
                    node.audio_fade_in, sample_rate, RoundingMode.NEAREST
                ).samples,
                duration_samples // 2,
            )
            fade_out_samples = min(
                AudioSampleTime.from_time(
                    node.audio_fade_out, sample_rate, RoundingMode.NEAREST
                ).samples,
                duration_samples // 2,
            )
            audio_filter = (
                f"atrim=start_sample={start_sample}:end_sample={end_sample},asetpts=PTS-STARTPTS"
            )
            if fade_in_samples > 0:
                audio_filter += f",afade=t=in:ss=0:ns={fade_in_samples}"
            if fade_out_samples > 0:
                audio_filter += (
                    f",afade=t=out:ss={duration_samples - fade_out_samples}:ns={fade_out_samples}"
                )
            command = [
                self.config.ffmpeg_path,
                "-y",
                "-i",
                str(source.path),
                "-map",
                f"0:{source.metadata.get('stream', 'a:0')}",
                "-vn",
                "-af",
                audio_filter,
                "-c:a",
                "pcm_f32le",
                "-ar",
                str(sample_rate),
                str(output),
            ]
        else:
            video_filter = (
                f"trim=start={_number(start)}:duration={_number(duration)},setpts=PTS-STARTPTS"
            )
            command = [
                self.config.ffmpeg_path,
                "-y",
                "-noautorotate",
                "-i",
                str(source.path),
                "-map",
                f"0:{source.metadata.get('stream', 'v:0')}",
                "-vf",
                video_filter,
                "-an",
                *self._intermediate_video_args(),
                str(output),
            ]
        self._run(command)
        return BackendExecution(path=output)

    def _conform(self, node: ConformNode, source: RenderArtifact, output: Path) -> BackendExecution:
        if node.artifact_type is ArtifactType.AUDIO:
            self._run(
                [
                    self.config.ffmpeg_path,
                    "-y",
                    "-i",
                    str(source.path),
                    "-vn",
                    "-af",
                    f"aresample={node.sample_rate}:async=0:first_pts=0",
                    "-c:a",
                    "pcm_f32le",
                    "-ar",
                    str(node.sample_rate),
                    str(output),
                ]
            )
        else:
            rate = f"{node.frame_rate.numerator}/{node.frame_rate.denominator}"
            if node.frame_policy == "passthrough":
                video_filter = "setpts=PTS-STARTPTS"
            elif node.frame_policy == "blend":
                video_filter = f"minterpolate=fps={rate}:mi_mode=blend,setpts=PTS-STARTPTS"
            else:
                video_filter = f"fps={rate}:round=near,setpts=PTS-STARTPTS"
            self._run_video_filter(source.path, output, video_filter)
        return BackendExecution(path=output)

    def _video_filter(
        self,
        node: RenderNode,
        source: RenderArtifact,
        output: Path,
        video_filter: str,
    ) -> BackendExecution:
        if source.artifact_type not in {
            ArtifactType.VIDEO,
            ArtifactType.AUDIO_VIDEO,
            ArtifactType.IMAGE,
            ArtifactType.MASK,
        }:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "video node received a non-video artifact",
                context={"node_id": node.id, "input_type": source.artifact_type.value},
            )
        self._run_video_filter(source.path, output, video_filter)
        return BackendExecution(path=output)

    def _run_video_filter(
        self,
        source: Path,
        output: Path,
        video_filter: str,
        *,
        pixel_format: str | None = None,
    ) -> None:
        self._run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-i",
                str(source),
                "-vf",
                video_filter,
                "-an",
                *self._intermediate_video_args(pixel_format),
                str(output),
            ]
        )

    @classmethod
    def _intermediate_video_args(cls, pixel_format: str | None = None) -> list[str]:
        return [
            "-c:v",
            "ffv1",
            "-level",
            "3",
            "-g",
            "1",
            "-pix_fmt",
            pixel_format or cls.intermediate_pixel_format,
        ]

    @staticmethod
    def _scale_filter(node: ScaleNode) -> str:
        if node.fit == "stretch":
            return f"scale={node.width}:{node.height}:flags={node.algorithm},setsar=1"
        if node.fit == "contain":
            return (
                f"scale={node.width}:{node.height}:force_original_aspect_ratio=decrease:"
                f"flags={node.algorithm},pad={node.width}:{node.height}:(ow-iw)/2:(oh-ih)/2:"
                f"color={node.pad_color},setsar=1"
            )
        return (
            f"scale={node.width}:{node.height}:force_original_aspect_ratio=increase:"
            f"flags={node.algorithm},crop={node.width}:{node.height}:"
            f"(iw-{node.width})*{_number(node.focus_x)}:"
            f"(ih-{node.height})*{_number(node.focus_y)},setsar=1"
        )

    def _scale(self, node: ScaleNode, source: RenderArtifact, output: Path) -> BackendExecution:
        if not node.automation and node.zoom == 1:
            return self._video_filter(node, source, output, self._scale_filter(node))
        if node.fit != "cover":
            return self._video_filter(node, source, output, self._scale_filter(node))
        zoom = self._visual_automation_expression(
            node.automation,
            "reframe_zoom",
            node.zoom,
            "t",
            node.automation_offset,
        )
        focus_x = self._visual_automation_expression(
            node.automation,
            "focus_x",
            node.focus_x,
            "t",
            node.automation_offset,
        )
        focus_y = self._visual_automation_expression(
            node.automation,
            "focus_y",
            node.focus_y,
            "t",
            node.automation_offset,
        )
        factor = f"max({node.width}/iw,{node.height}/ih)*({zoom})"
        video_filter = (
            f"scale=w='ceil(iw*({factor})/2)*2':"
            f"h='ceil(ih*({factor})/2)*2':eval=frame:flags={node.algorithm},"
            f"crop={node.width}:{node.height}:"
            f"x='(iw-{node.width})*({focus_x})':"
            f"y='(ih-{node.height})*({focus_y})',setsar=1"
        )
        return self._video_filter(node, source, output, video_filter)

    @staticmethod
    def _transform_filter(node: TransformNode) -> str:
        parts: list[str] = []
        if node.scale_x != 1 or node.scale_y != 1:
            parts.append(
                f"scale=iw*{_number(node.scale_x)}:ih*{_number(node.scale_y)}:flags=lanczos"
            )
        if node.rotation_degrees:
            radians = node.rotation_degrees * math.pi / 180
            parts.append(f"rotate={_number(radians)}:ow=rotw(iw):oh=roth(ih):c=none")
        if node.opacity != 1:
            parts.extend(["format=gbrap10le", f"colorchannelmixer=aa={_number(node.opacity)}"])
        if node.position_x or node.position_y:
            x_pad = abs(round(node.position_x))
            y_pad = abs(round(node.position_y))
            x = x_pad if node.position_x >= 0 else 0
            y = y_pad if node.position_y >= 0 else 0
            parts.append(f"pad=iw+{x_pad}:ih+{y_pad}:{x}:{y}:color=black@0")
        return ",".join(parts) or "null"

    def _transform(
        self, node: TransformNode, source: RenderArtifact, output: Path
    ) -> BackendExecution:
        if node.canvas_width is None or node.canvas_height is None:
            return self._video_filter(node, source, output, self._transform_filter(node))
        scale_x = self._visual_automation_expression(
            node.automation,
            "scale_x",
            node.scale_x,
            "t",
            node.automation_offset,
        )
        scale_y = self._visual_automation_expression(
            node.automation,
            "scale_y",
            node.scale_y,
            "t",
            node.automation_offset,
        )
        foreground: list[str] = []
        if (
            node.scale_x != 1
            or node.scale_y != 1
            or any(point.property_path in {"scale_x", "scale_y"} for point in node.automation)
        ):
            foreground.append(
                f"scale=w='max(1,round(iw*({scale_x})))':"
                f"h='max(1,round(ih*({scale_y})))':eval=frame:flags=lanczos"
            )
        rotation = self._visual_automation_expression(
            node.automation,
            "rotation_degrees",
            node.rotation_degrees,
            "t",
            node.automation_offset,
        )
        has_rotation_automation = any(
            point.property_path == "rotation_degrees" for point in node.automation
        )
        if node.rotation_degrees or has_rotation_automation:
            radians = f"({rotation})*PI/180"
            dimensions = (
                "ow=hypot(iw,ih):oh=ow" if has_rotation_automation else "ow=rotw(iw):oh=roth(ih)"
            )
            foreground.append(f"rotate=angle='{radians}':{dimensions}:c=none")
        foreground.append("format=yuva444p10le")
        opacity = self._visual_automation_expression(
            node.automation,
            "opacity",
            node.opacity,
            "T",
            node.automation_offset,
        )
        if any(point.property_path == "opacity" for point in node.automation):
            foreground.append(f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*({opacity})'")
        elif node.opacity != 1:
            foreground.append(f"colorchannelmixer=aa={_number(node.opacity)}")
        position_x = self._visual_automation_expression(
            node.automation,
            "position_x",
            node.position_x,
            "t",
            node.automation_offset,
        )
        position_y = self._visual_automation_expression(
            node.automation,
            "position_y",
            node.position_y,
            "t",
            node.automation_offset,
        )
        anchor_x = self._visual_automation_expression(
            node.automation,
            "anchor_x",
            node.anchor_x,
            "t",
            node.automation_offset,
        )
        anchor_y = self._visual_automation_expression(
            node.automation,
            "anchor_y",
            node.anchor_y,
            "t",
            node.automation_offset,
        )
        x = f"({node.canvas_width}-overlay_w)*({anchor_x})+({position_x})"
        y = f"({node.canvas_height}-overlay_h)*({anchor_y})+({position_y})"
        filters = (
            "[0:v]split=2[base_input][foreground_input];"
            f"[base_input]scale={node.canvas_width}:{node.canvas_height}:flags=lanczos,"
            "format=yuva444p10le,colorchannelmixer=aa=0[base];"
            f"[foreground_input]{','.join(foreground)}[foreground];"
            f"[base][foreground]overlay=x='{x}':y='{y}':shortest=1:format=auto[out]"
        )
        self._run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-i",
                str(source.path),
                "-filter_complex",
                filters,
                "-map",
                "[out]",
                "-an",
                *self._intermediate_video_args(),
                str(output),
            ]
        )
        return BackendExecution(
            path=output,
            metadata={
                "canvas_width": node.canvas_width,
                "canvas_height": node.canvas_height,
                "anchor_x": node.anchor_x,
                "anchor_y": node.anchor_y,
            },
        )

    def _crop(self, node: CropNode, source: RenderArtifact, output: Path) -> BackendExecution:
        if node.canvas_width is None or node.canvas_height is None:
            return self._video_filter(
                node,
                source,
                output,
                f"crop={node.width}:{node.height}:{node.x}:{node.y}",
            )
        width = self._visual_automation_expression(
            node.automation,
            "crop_width",
            float(node.width),
            "T",
            node.automation_offset,
        ).replace(",", "\\,")
        height = self._visual_automation_expression(
            node.automation,
            "crop_height",
            float(node.height),
            "T",
            node.automation_offset,
        ).replace(",", "\\,")
        x = self._visual_automation_expression(
            node.automation,
            "crop_x",
            float(node.x),
            "T",
            node.automation_offset,
        ).replace(",", "\\,")
        y = self._visual_automation_expression(
            node.automation,
            "crop_y",
            float(node.y),
            "T",
            node.automation_offset,
        ).replace(",", "\\,")
        alpha = f"alpha(X,Y)*between(X,({x}),({x})+({width})-1)*between(Y,({y}),({y})+({height})-1)"
        self._run_video_filter(
            source.path,
            output,
            f"format=yuva444p10le,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{alpha}'",
        )
        return BackendExecution(
            path=output,
            metadata={"canvas_width": node.canvas_width, "canvas_height": node.canvas_height},
        )

    @staticmethod
    def _color_components(value: str) -> tuple[float, float, float]:
        return (
            int(value[1:3], 16) / 255,
            int(value[3:5], 16) / 255,
            int(value[5:7], 16) / 255,
        )

    def _shadow(self, node: ShadowNode, source: RenderArtifact, output: Path) -> BackendExecution:
        red, green, blue = self._color_components(node.color)
        filters = (
            "[0:v]format=yuva444p10le,split=3[base_input][shadow_input][foreground];"
            "[base_input]colorchannelmixer=aa=0[base];"
            "[shadow_input]format=gbrap10le,"
            f"geq=r='{_number(red * 1023)}':g='{_number(green * 1023)}':"
            f"b='{_number(blue * 1023)}':a='alpha(X,Y)*{_number(node.opacity)}',"
            f"gblur=sigma={_number(node.blur_sigma)}[shadow];"
            f"[base][shadow]overlay=x={_number(node.offset_x)}:y={_number(node.offset_y)}:"
            "shortest=1:format=auto[shadowed];"
            "[shadowed][foreground]overlay=x=0:y=0:shortest=1:format=auto[out]"
        )
        self._run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-i",
                str(source.path),
                "-filter_complex",
                filters,
                "-map",
                "[out]",
                "-an",
                *self._intermediate_video_args(),
                str(output),
            ]
        )
        return BackendExecution(path=output)

    def _glow(self, node: GlowNode, source: RenderArtifact, output: Path) -> BackendExecution:
        red, green, blue = self._color_components(node.color)
        filters = (
            "[0:v]format=yuva444p10le,split=3[base_input][glow_input][foreground];"
            "[base_input]colorchannelmixer=aa=0[base];"
            "[glow_input]format=gbrap10le,"
            f"geq=r='{_number(red * 1023)}':g='{_number(green * 1023)}':"
            f"b='{_number(blue * 1023)}':a='alpha(X,Y)*{_number(node.intensity)}',"
            f"gblur=sigma={_number(node.blur_sigma)}[glow];"
            "[base][glow]overlay=x=0:y=0:shortest=1:format=auto[glowing];"
            "[glowing][foreground]overlay=x=0:y=0:shortest=1:format=auto[out]"
        )
        self._run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-i",
                str(source.path),
                "-filter_complex",
                filters,
                "-map",
                "[out]",
                "-an",
                *self._intermediate_video_args(),
                str(output),
            ]
        )
        return BackendExecution(path=output)

    def _perspective(
        self, node: PerspectiveNode, source: RenderArtifact, output: Path
    ) -> BackendExecution:
        properties = (
            ("x0", "top_left_x", node.top_left_x, "W"),
            ("y0", "top_left_y", node.top_left_y, "H"),
            ("x1", "top_right_x", node.top_right_x, "W"),
            ("y1", "top_right_y", node.top_right_y, "H"),
            ("x2", "bottom_left_x", node.bottom_left_x, "W"),
            ("y2", "bottom_left_y", node.bottom_left_y, "H"),
            ("x3", "bottom_right_x", node.bottom_right_x, "W"),
            ("y3", "bottom_right_y", node.bottom_right_y, "H"),
        )
        time_symbol = f"(in*{node.frame_rate.denominator}/{node.frame_rate.numerator})"
        options = []
        for backend_name, property_path, value, dimension in properties:
            expression = self._visual_automation_expression(
                node.automation,
                property_path,
                value,
                time_symbol,
                node.automation_offset,
            )
            options.append(f"{backend_name}='{dimension}*({expression})'")
        options.extend([f"interpolation={node.interpolation}", "sense=destination", "eval=frame"])
        return self._video_filter(
            node,
            source,
            output,
            "perspective=" + ":".join(options) + ",format=yuva444p10le",
        )

    @staticmethod
    def _visual_automation_expression(
        points: tuple[VisualAutomationPoint, ...],
        property_path: str,
        base_value: float,
        time_symbol: str,
        time_offset: RationalTime,
    ) -> str:
        selected = sorted(
            (point for point in points if point.property_path == property_path),
            key=lambda point: point.time,
        )
        if not selected:
            return _number(base_value)
        timed: list[tuple[float, VisualAutomationPoint]] = [
            (_seconds(point.time), point) for point in selected
        ]
        offset = _seconds(time_offset)
        time_variable = f"({time_symbol}+{_number(offset)})" if offset else time_symbol
        expression = _number(timed[-1][1].value)
        for (start, start_point), (end, end_point) in reversed(list(pairwise(timed))):
            duration = end - start
            progress = f"(({time_variable})-{_number(start)})/{_number(duration)}"
            if start_point.interpolation is Interpolation.HOLD:
                curve = "0"
            elif start_point.interpolation is Interpolation.EASE_IN:
                curve = f"pow({progress},2)"
            elif start_point.interpolation is Interpolation.EASE_OUT:
                curve = f"1-pow(1-({progress}),2)"
            elif start_point.interpolation is Interpolation.EASE_IN_OUT:
                curve = f"({progress})*({progress})*(3-2*({progress}))"
            elif start_point.interpolation is Interpolation.BEZIER:
                p = progress
                start_slope = (
                    start_point.out_tangent[1] if start_point.out_tangent is not None else 0
                )
                end_slope = end_point.in_tangent[1] if end_point.in_tangent is not None else 0
                curve_value = (
                    f"(2*pow({p},3)-3*pow({p},2)+1)*{_number(start_point.value)}"
                    f"+(pow({p},3)-2*pow({p},2)+({p}))*{_number(start_slope * duration)}"
                    f"+(-2*pow({p},3)+3*pow({p},2))*{_number(end_point.value)}"
                    f"+(pow({p},3)-pow({p},2))*{_number(end_slope * duration)}"
                )
                segment = curve_value
                expression = f"if(lt({time_variable},{_number(end)}),{segment},{expression})"
                continue
            else:
                curve = progress
            delta = end_point.value - start_point.value
            segment = f"{_number(start_point.value)}+({_number(delta)})*({curve})"
            expression = f"if(lt({time_variable},{_number(end)}),{segment},{expression})"
        first_time, first_point = timed[0]
        before = _number(base_value if first_time > 0 else first_point.value)
        return f"if(lt({time_variable},{_number(first_time)}),{before},{expression})"

    def _speed(self, node: SpeedNode, source: RenderArtifact, output: Path) -> BackendExecution:
        rate = float(node.rate.fraction)
        self._require_supported_tempo(rate, node.id)
        if node.artifact_type is ArtifactType.AUDIO:
            filters = self._atempo_filters(rate)
            total_samples = AudioSampleTime.from_time(
                node.duration, node.sample_rate, RoundingMode.EXACT
            ).samples
            self._run_audio_filter(
                source.path,
                output,
                f"{','.join(filters)},apad=whole_len={total_samples},"
                f"atrim=end_sample={total_samples}",
            )
        else:
            frames = node.frame_rate.time_to_frames(node.duration, RoundingMode.EXACT)
            frame_rate = f"{node.frame_rate.numerator}/{node.frame_rate.denominator}"
            self._run_video_filter(
                source.path,
                output,
                f"setpts=PTS/{_rational_expression(node.rate.fraction)},"
                f"fps={frame_rate}:round=near,trim=end_frame={frames},setpts=PTS-STARTPTS",
            )
        return BackendExecution(path=output)

    def _speed_ramp(
        self,
        node: SpeedRampNode,
        source: RenderArtifact,
        output: Path,
        work_dir: Path,
    ) -> BackendExecution:
        retime = Retime(speed_ramp=node.points)
        for point in node.points:
            self._require_supported_tempo(float(point.rate.fraction), node.id)
        if node.artifact_type is ArtifactType.VIDEO:
            expression = self._speed_ramp_setpts(retime)
            frame_rate = f"{node.frame_rate.numerator}/{node.frame_rate.denominator}"
            frames = node.frame_rate.time_to_frames(node.duration, RoundingMode.EXACT)
            self._run_video_filter(
                source.path,
                output,
                f"setpts=({expression})/TB,fps={frame_rate}:round=near,"
                f"trim=end_frame={frames},setpts=PTS-STARTPTS",
            )
            return BackendExecution(path=output)

        total_samples = AudioSampleTime.from_time(
            node.duration, node.sample_rate, RoundingMode.EXACT
        ).samples
        commands = self._speed_ramp_audio_commands(retime, node.sample_rate, total_samples)
        command_path = work_dir / (
            f"speed-ramp-{hashlib.sha256(node.id.encode('utf-8')).hexdigest()[:16]}.commands"
        )
        command_path.parent.mkdir(parents=True, exist_ok=True)
        command_path.write_text("\n".join(commands) + "\n", encoding="utf-8")
        initial_tempo = float(retime.rate_at(RationalTime.zero()))
        audio_filter = (
            f"asendcmd=f='{_escape_filter_path(command_path)}',"
            f"rubberband@speed_ramp=tempo={_number(initial_tempo)},"
            f"apad=whole_len={total_samples},atrim=end_sample={total_samples}"
        )
        try:
            self._run_audio_filter(source.path, output, audio_filter)
        finally:
            command_path.unlink(missing_ok=True)
        return BackendExecution(path=output)

    @staticmethod
    def _speed_ramp_audio_commands(
        retime: Retime,
        sample_rate: int,
        total_samples: int,
        *,
        control_interval_samples: int = 480,
    ) -> list[str]:
        if control_interval_samples <= 0:
            raise ValueError("audio speed-ramp control interval must be positive")
        control_samples = set(
            range(control_interval_samples, total_samples, control_interval_samples)
        )
        for point in retime.speed_ramp[1:]:
            control_samples.add(
                min(
                    total_samples,
                    AudioSampleTime.from_time(
                        point.time, sample_rate, RoundingMode.NEAREST
                    ).samples,
                )
            )
        commands: list[str] = []
        for output_sample in sorted(control_samples):
            if output_sample >= total_samples:
                continue
            output_time = AudioSampleTime(samples=output_sample, sample_rate=sample_rate).time
            source_time = retime.source_offset_at(output_time)
            rate = float(retime.rate_at(output_time))
            commands.append(
                f"{_number(_seconds(source_time))} rubberband@speed_ramp tempo {_number(rate)};"
            )
        if not commands:
            commands.append(
                f"0 rubberband@speed_ramp tempo "
                f"{_number(float(retime.rate_at(RationalTime.zero())))};"
            )
        return commands

    @staticmethod
    def _speed_ramp_setpts(retime: Retime) -> str:
        fallback = _rational_expression(retime.speed_ramp[-1].time.fraction)
        expression = fallback
        for left, right in reversed(list(pairwise(retime.speed_ramp))):
            output_start = left.time.fraction
            source_start = retime.source_offset_at(left.time).fraction
            source_end = retime.source_offset_at(right.time).fraction
            rate_start = left.rate.fraction
            if left.interpolation == "hold" or left.rate == right.rate:
                mapped = (
                    f"{_rational_expression(output_start)}+"
                    f"(T-{_rational_expression(source_start)})/"
                    f"{_rational_expression(rate_start)}"
                )
            else:
                slope = (right.rate.fraction - left.rate.fraction) / (
                    right.time - left.time
                ).fraction
                delta = f"(T-{_rational_expression(source_start)})"
                mapped = (
                    f"{_rational_expression(output_start)}+2*{delta}/"
                    f"({_rational_expression(rate_start)}+sqrt("
                    f"{_rational_expression(rate_start * rate_start)}+"
                    f"2*{_rational_expression(slope)}*{delta}))"
                )
            expression = f"if(lt(T\\,{_rational_expression(source_end)})\\,{mapped}\\,{expression})"
        return expression

    @staticmethod
    def _supported_tempo(rate: float) -> bool:
        return math.isfinite(rate) and 0.01 <= rate <= 100

    @classmethod
    def _require_supported_tempo(cls, rate: float, node_id: str) -> None:
        if not cls._supported_tempo(rate):
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "FFmpeg temporal rate must be finite and between 0.01 and 100",
                context={"node_id": node_id, "rate": rate},
            )

    @classmethod
    def _atempo_filters(cls, rate: float) -> list[str]:
        cls._require_supported_tempo(rate, "atempo")
        filters: list[str] = []
        remaining = rate
        while remaining > 2:
            filters.append("atempo=2")
            remaining /= 2
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
        filters.append(f"atempo={_number(remaining)}")
        if len(filters) > 8:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "FFmpeg audio tempo requires too many processing stages",
                context={"rate": rate, "stages": len(filters)},
            )
        return filters

    def _reverse(self, node: ReverseNode, source: RenderArtifact, output: Path) -> BackendExecution:
        if node.artifact_type is ArtifactType.AUDIO:
            audio_filter = "areverse" if node.reverse_audio else "anull"
            self._run_audio_filter(source.path, output, audio_filter)
        else:
            video_filter = "reverse" if node.reverse_video else "null"
            self._run_video_filter(source.path, output, video_filter)
        return BackendExecution(path=output)

    def _freeze(self, node: FreezeNode, source: RenderArtifact, output: Path) -> BackendExecution:
        frame_index = node.frame_rate.time_to_frames(
            node.frame_time,
            RoundingMode.EXACT,
        )
        frame_count = node.frame_rate.time_to_frames(
            node.duration,
            RoundingMode.EXACT,
        )
        rate = f"{node.frame_rate.numerator}/{node.frame_rate.denominator}"
        filter_value = (
            f"select=eq(n\\,{frame_index}),setpts=PTS-STARTPTS,"
            f"tpad=stop_mode=clone:stop={frame_count - 1},"
            f"trim=end_frame={frame_count},"
            f"setpts=N*{node.frame_rate.denominator}/"
            f"({node.frame_rate.numerator}*TB),fps={rate}:round=near"
        )
        self._run_video_filter(source.path, output, filter_value)
        return BackendExecution(path=output)

    @staticmethod
    def _color_filter(node: ColorConversionNode) -> str:
        if node.input_space in {ColorSpace.HLG, ColorSpace.PQ} and node.output_space in {
            ColorSpace.REC709,
            ColorSpace.REC2020,
        }:
            if node.tone_map == "none":
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "HDR-to-SDR conversion cannot execute without tone mapping",
                    context={"node_id": node.id},
                )
            tone_map = node.tone_map
            input_transfer = "arib-std-b67" if node.input_space is ColorSpace.HLG else "smpte2084"
            output_primaries = "bt709" if node.output_space is ColorSpace.REC709 else "bt2020"
            output_matrix = "bt709" if node.output_space is ColorSpace.REC709 else "bt2020nc"
            return (
                f"zscale=pin=bt2020:tin={input_transfer}:min=bt2020nc:rin=limited:"
                f"t=linear:npl={_number(node.peak_nits)},format=gbrpf32le,"
                f"zscale=p={output_primaries},tonemap=tonemap={tone_map}:desat=0,"
                f"zscale=p={output_primaries}:t=bt709:m={output_matrix}:r=limited,"
                "format=yuv444p10le"
            )
        if node.input_space == node.output_space:
            return "null"
        if node.input_space in {ColorSpace.REC709, ColorSpace.REC2020} and (
            node.output_space in {ColorSpace.REC709, ColorSpace.REC2020}
        ):
            input_value = "bt709" if node.input_space is ColorSpace.REC709 else "bt2020"
            output_value = "bt709" if node.output_space is ColorSpace.REC709 else "bt2020"
            return f"colorspace=iall={input_value}:all={output_value},format=yuv444p10le"
        if node.input_space in {ColorSpace.REC709, ColorSpace.REC2020} and (
            node.output_space in {ColorSpace.HLG, ColorSpace.PQ}
        ):
            input_value = "bt709" if node.input_space is ColorSpace.REC709 else "bt2020"
            output_transfer = "arib-std-b67" if node.output_space is ColorSpace.HLG else "smpte2084"
            return (
                f"zscale=pin={input_value}:tin=bt709:min={input_value}:rin=limited:"
                "p=bt2020:t=linear:m=gbr:r=full,format=gbrpf32le,"
                "zscale=pin=bt2020:tin=linear:min=gbr:rin=full:"
                f"p=bt2020:t={output_transfer}:m=bt2020nc:r=limited,"
                "format=yuv444p10le"
            )
        raise EngineError(
            ErrorCode.UNSUPPORTED_CAPABILITY,
            "requested color conversion is unsupported by the FFmpeg backend",
            context={"input": node.input_space.value, "output": node.output_space.value},
        )

    @staticmethod
    def _grade_filter(node: GradeNode) -> str:
        brightness = max(-1.0, min(1.0, node.exposure_stops * 0.1))
        parts = [
            f"eq=brightness={_number(brightness)}:contrast={_number(node.contrast)}:"
            f"gamma={_number(node.gamma)}:saturation={_number(node.saturation)}"
        ]
        if node.temperature or node.tint:
            parts.append(
                "colorbalance="
                f"rs={_number(node.temperature * 0.25)}:"
                f"bs={_number(-node.temperature * 0.25)}:"
                f"gs={_number(node.tint * 0.25)}"
            )
        if node.highlights or node.shadows:
            parts.append(
                f"curves=all='0/{_number(max(0, node.shadows * 0.08))} "
                f"1/{_number(min(1, 1 + node.highlights * 0.08))}'"
            )
        if node.lut_path:
            parts.append(f"lut3d=file='{_escape_filter_path(Path(node.lut_path))}'")
        if node.enabled_range is not None:
            start = _number(_seconds(node.enabled_range.start))
            end = _number(_seconds(node.enabled_range.end))
            enable = f":enable='gte(t,{start})*lt(t,{end})'"
            parts = [part + enable for part in parts]
        return ",".join(parts)

    def _region_factor(
        self,
        node: MaskNode | BlurNode,
        *,
        shape: str,
        invert: bool,
    ) -> str:
        assert node.canvas_width is not None and node.canvas_height is not None
        x = self._visual_automation_expression(
            node.automation,
            "region_x",
            node.x,
            "T",
            node.automation_offset,
        )
        y = self._visual_automation_expression(
            node.automation,
            "region_y",
            node.y,
            "T",
            node.automation_offset,
        )
        width = self._visual_automation_expression(
            node.automation,
            "region_width",
            node.width,
            "T",
            node.automation_offset,
        )
        height = self._visual_automation_expression(
            node.automation,
            "region_height",
            node.height,
            "T",
            node.automation_offset,
        )
        left = f"({x})*{node.canvas_width}"
        top = f"({y})*{node.canvas_height}"
        pixel_width = f"({width})*{node.canvas_width}"
        pixel_height = f"({height})*{node.canvas_height}"
        if shape == "ellipse":
            center_x = f"({left})+({pixel_width})/2"
            center_y = f"({top})+({pixel_height})/2"
            radius = (
                f"sqrt(pow((X-({center_x}))/max(1\\,({pixel_width})/2)\\,2)+"
                f"pow((Y-({center_y}))/max(1\\,({pixel_height})/2)\\,2))"
            )
            factor = (
                f"lte({radius}\\,1)"
                if node.feather == 0
                else f"clip((1-({radius}))/{_number(node.feather)}\\,0\\,1)"
            )
        elif node.feather == 0:
            factor = (
                f"between(X\\,({left})\\,({left})+({pixel_width})-1)*"
                f"between(Y\\,({top})\\,({top})+({pixel_height})-1)"
            )
        else:
            feather_x = _number(node.feather * node.canvas_width)
            feather_y = _number(node.feather * node.canvas_height)
            horizontal = (
                "min("
                f"(X-({left}))/max(1\\,{feather_x})\\,"
                f"(({left})+({pixel_width})-1-X)/max(1\\,{feather_x})"
                ")"
            )
            vertical = (
                "min("
                f"(Y-({top}))/max(1\\,{feather_y})\\,"
                f"(({top})+({pixel_height})-1-Y)/max(1\\,{feather_y})"
                ")"
            )
            factor = f"clip(min({horizontal}\\,{vertical})\\,0\\,1)"
        return f"1-({factor})" if invert else factor

    def _blur(self, node: BlurNode, source: RenderArtifact, output: Path) -> BackendExecution:
        if node.region_shape == "full":
            return self._video_filter(
                node,
                source,
                output,
                f"gblur=sigma={_number(node.sigma)}:steps={node.steps}",
            )
        assert node.region_policy is not None
        factor = self._region_factor(
            node,
            shape=node.region_shape,
            invert=node.region_policy == "outside",
        )
        filters = (
            "[0:v]split=3[base_input][blur_input][mask_input];"
            "[base_input]format=yuva444p10le[base];"
            f"[blur_input]gblur=sigma={_number(node.sigma)}:steps={node.steps},"
            "format=yuva444p10le[blurred];"
            f"[mask_input]format=gray,geq=lum='255*({factor})'[mask];"
            "[base][blurred][mask]maskedmerge=planes=15[out]"
        )
        self._run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-i",
                str(source.path),
                "-filter_complex",
                filters,
                "-map",
                "[out]",
                "-an",
                *self._intermediate_video_args(),
                str(output),
            ]
        )
        return BackendExecution(path=output)

    def _mask(
        self,
        node: MaskNode,
        inputs: tuple[RenderArtifact, ...],
        output: Path,
    ) -> BackendExecution:
        if node.mode == "chroma":
            return self._video_filter(
                node,
                inputs[0],
                output,
                f"chromakey={node.key_color}:{_number(node.similarity)}:"
                f"{_number(node.blend)},format=yuva444p10le",
            )
        if node.mode == "luma_key":
            normalized = "lum(X,Y)/1023"
            if node.softness:
                factor = (
                    f"clip((({normalized})-{_number(node.threshold)})/{_number(node.softness)},0,1)"
                )
            else:
                factor = f"gte(({normalized}),{_number(node.threshold)})"
            if node.invert:
                factor = f"1-({factor})"
            return self._video_filter(
                node,
                inputs[0],
                output,
                "format=yuva444p10le,"
                "geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
                f"a='alpha(X,Y)*({factor})'",
            )
        if node.mode == "rounded_rectangle":
            assert node.canvas_width is not None and node.canvas_height is not None
            radius = self._visual_automation_expression(
                node.automation,
                "corner_radius",
                node.corner_radius,
                "T",
                node.automation_offset,
            )
            half_width = _number(node.canvas_width / 2)
            half_height = _number(node.canvas_height / 2)
            center_x = _number((node.canvas_width - 1) / 2)
            center_y = _number((node.canvas_height - 1) / 2)
            dx = f"max(abs(X-{center_x})-({half_width}-({radius})),0)"
            dy = f"max(abs(Y-{center_y})-({half_height}-({radius})),0)"
            condition = f"lte(({dx})*({dx})+({dy})*({dy}),({radius})*({radius}))"
            return self._video_filter(
                node,
                inputs[0],
                output,
                "format=yuva444p10le,"
                "geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
                f"a='alpha(X,Y)*({condition})'",
            )
        if node.mode in {"rectangle", "ellipse"}:
            factor = self._region_factor(node, shape=node.mode, invert=node.invert)
            return self._video_filter(
                node,
                inputs[0],
                output,
                "format=yuva444p10le,"
                "geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':"
                f"a='alpha(X,Y)*({factor})'",
            )
        assert node.canvas_width is not None and node.canvas_height is not None
        matte_input = inputs[1]
        command = [self.config.ffmpeg_path, "-y", "-i", str(inputs[0].path)]
        if matte_input.artifact_type is ArtifactType.IMAGE:
            command.extend(["-loop", "1"])
        command.extend(["-i", str(matte_input.path)])
        matte_filter = (
            "format=yuva444p10le,alphaextract,format=gray10le"
            if node.mode == "alpha_matte"
            else "format=gray10le"
        )
        if node.invert:
            matte_filter += ",negate"
        filters = (
            "[0:v]format=yuva444p10le,split=2[foreground_color][foreground_alpha_source];"
            "[foreground_color]format=yuv444p10le[foreground];"
            "[foreground_alpha_source]alphaextract[foreground_alpha];"
            f"[1:v]scale={node.canvas_width}:{node.canvas_height}:flags=lanczos,"
            f"{matte_filter}[matte];"
            "[foreground_alpha][matte]blend=all_expr='A*B/1023':shortest=1[combined_alpha];"
            "[foreground][combined_alpha]alphamerge=shortest=1[out]"
        )
        command.extend(
            [
                "-filter_complex",
                filters,
                "-map",
                "[out]",
                "-an",
                *self._intermediate_video_args(),
                str(output),
            ]
        )
        self._run(command)
        return BackendExecution(path=output)

    def _composite(
        self,
        node: CompositeNode,
        inputs: tuple[RenderArtifact, ...],
        output: Path,
        work_dir: Path,
    ) -> BackendExecution:
        duration = _seconds(node.duration)
        rate = f"{node.frame_rate.numerator}/{node.frame_rate.denominator}"
        command = [
            self.config.ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={node.background_color}:s={node.width}x{node.height}:r={rate}:"
            f"d={_number(duration)},format=yuva444p10le",
        ]
        for artifact in inputs:
            command.extend(["-i", str(artifact.path)])
        filters: list[str] = ["[0:v]format=yuva444p10le[base]"]
        current = "[base]"
        for index, layer in enumerate(node.layers, start=1):
            start = _seconds(layer.timeline_range.start)
            end = _seconds(layer.timeline_range.end)
            prepared = f"[layer{index}]"
            layer_filter = f"[{index}:v]format=yuva444p10le,setpts=PTS-STARTPTS+{_number(start)}/TB"
            if layer.opacity != 1 and layer.blend_mode == "normal":
                layer_filter += f",format=gbrap10le,colorchannelmixer=aa={_number(layer.opacity)}"
            layer_filter += prepared
            filters.append(layer_filter)
            next_label = f"[v{index}]"
            enable = f"gte(t,{_number(start)})*lt(t,{_number(end)})"
            if layer.blend_mode == "normal":
                filters.append(
                    f"{current}{prepared}overlay=x={layer.x}:y={layer.y}:"
                    f"enable='{enable}':"
                    f"eof_action=pass:repeatlast=1{next_label}"
                )
            else:
                base_for_blend = f"[base_blend_{index}]"
                base_for_output = f"[base_output_{index}]"
                top_for_blend = f"[top_blend_{index}]"
                top_for_alpha = f"[top_alpha_{index}]"
                blended = f"[blended_{index}]"
                blended_rgb = f"[blended_rgb_{index}]"
                alpha = f"[alpha_{index}]"
                blended_rgba = f"[blended_rgba_{index}]"
                filters.append(f"{current}split=2{base_for_blend}{base_for_output}")
                filters.append(f"{prepared}split=2{top_for_blend}{top_for_alpha}")
                filters.append(
                    f"{base_for_blend}{top_for_blend}blend=all_mode={layer.blend_mode}:"
                    f"all_opacity=1{blended}"
                )
                filters.append(f"{blended}format=yuv444p10le{blended_rgb}")
                filters.append(
                    f"{top_for_alpha}alphaextract,lut=y='val*{_number(layer.opacity)}'{alpha}"
                )
                filters.append(f"{blended_rgb}{alpha}alphamerge{blended_rgba}")
                filters.append(
                    f"{base_for_output}{blended_rgba}overlay=x={layer.x}:y={layer.y}:"
                    f"enable='{enable}':eof_action=pass:repeatlast=1{next_label}"
                )
            current = next_label
        filters.append(f"{current}trim=duration={_number(duration)},setpts=PTS-STARTPTS[outv]")
        script = work_dir / "filtergraph.txt"
        script.write_text(";\n".join(filters) + "\n", encoding="utf-8")
        command.extend(
            [
                "-filter_complex_script",
                str(script),
                "-map",
                "[outv]",
                "-an",
                *self._intermediate_video_args(),
                str(output),
            ]
        )
        self._run(command)
        return BackendExecution(path=output, metadata={"filtergraph": str(script)})

    def _concat(
        self,
        node: ConcatNode,
        inputs: tuple[RenderArtifact, ...],
        output: Path,
    ) -> BackendExecution:
        command = [self.config.ffmpeg_path, "-y"]
        for artifact in inputs:
            command.extend(["-i", str(artifact.path)])
        filters: list[str] = []
        labels: list[str] = []
        if node.artifact_type is ArtifactType.VIDEO:
            assert node.frame_rate is not None
            for index, duration in enumerate(node.segment_durations):
                label = f"[segment_{index}]"
                filters.append(
                    f"[{index}:v:0]trim=duration={_number(_seconds(duration))},"
                    f"setpts=PTS-STARTPTS{label}"
                )
                labels.append(label)
            filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[out]")
            command.extend(
                [
                    "-filter_complex",
                    ";".join(filters),
                    "-map",
                    "[out]",
                    "-an",
                    *self._intermediate_video_args(),
                    str(output),
                ]
            )
        else:
            assert node.sample_rate is not None
            for index, duration in enumerate(node.segment_durations):
                sample_count = AudioSampleTime.from_time(
                    duration, node.sample_rate, RoundingMode.NEAREST
                ).samples
                label = f"[segment_{index}]"
                filters.append(
                    f"[{index}:a:0]atrim=end_sample={sample_count},asetpts=PTS-STARTPTS{label}"
                )
                labels.append(label)
            filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[out]")
            command.extend(
                [
                    "-filter_complex",
                    ";".join(filters),
                    "-map",
                    "[out]",
                    "-vn",
                    "-c:a",
                    "pcm_f32le",
                    "-ar",
                    str(node.sample_rate),
                    str(output),
                ]
            )
        self._run(command)
        return BackendExecution(path=output)

    def _transition(
        self,
        node: TransitionNode,
        inputs: tuple[RenderArtifact, ...],
        output: Path,
    ) -> BackendExecution:
        duration = _seconds(node.duration)
        offset = _seconds(node.offset)
        if node.artifact_type is ArtifactType.AUDIO:
            sample_rate = node.audio_sample_rate or 48_000
            duration_samples = AudioSampleTime.from_time(
                node.duration, sample_rate, RoundingMode.EXACT
            ).samples
            allowed_curves = {
                "tri",
                "qsin",
                "esin",
                "hsin",
                "log",
                "ipar",
                "qua",
                "cub",
                "squ",
                "cbr",
                "par",
                "exp",
                "iqsin",
                "ihsin",
                "dese",
                "desi",
                "losi",
                "nofade",
            }
            curve_from = str(node.parameters.get("curve_from", "tri"))
            curve_to = str(node.parameters.get("curve_to", "tri"))
            if curve_from not in allowed_curves or curve_to not in allowed_curves:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "audio crossfade curve is unsupported",
                    context={"curve_from": curve_from, "curve_to": curve_to},
                )
            self._run(
                [
                    self.config.ffmpeg_path,
                    "-y",
                    "-i",
                    str(inputs[0].path),
                    "-i",
                    str(inputs[1].path),
                    "-filter_complex",
                    f"[0:a][1:a]acrossfade=ns={duration_samples}:c1={curve_from}:c2={curve_to}[a]",
                    "-map",
                    "[a]",
                    "-c:a",
                    "pcm_f32le",
                    "-ar",
                    str(sample_rate),
                    str(output),
                ]
            )
        else:
            transition = self._xfade_name(node)
            self._run(
                [
                    self.config.ffmpeg_path,
                    "-y",
                    "-i",
                    str(inputs[0].path),
                    "-i",
                    str(inputs[1].path),
                    "-filter_complex",
                    f"[0:v][1:v]xfade=transition={transition}:duration={_number(duration)}:"
                    f"offset={_number(offset)}[v]",
                    "-map",
                    "[v]",
                    "-an",
                    *self._intermediate_video_args(),
                    str(output),
                ]
            )
        return BackendExecution(path=output)

    @staticmethod
    def _xfade_name(node: TransitionNode) -> str:
        if node.transition.value == "dip_to_color":
            return "fadewhite" if node.parameters.get("color") == "white" else "fadeblack"
        if node.transition.value in {"wipe", "slide", "push"}:
            direction = str(node.parameters.get("direction", "left"))
            prefix = "wipe" if node.transition.value == "wipe" else "slide"
            return f"{prefix}{direction}"
        names = {
            "cut": "fadefast",
            "dissolve": "fade",
            "zoom": "zoomin",
            "audio_crossfade": "fade",
        }
        return names[node.transition.value]

    def _caption(
        self,
        node: CaptionNode,
        source: RenderArtifact,
        output: Path,
        work_dir: Path,
    ) -> BackendExecution:
        subtitle = Path(node.subtitle_path) if node.subtitle_path else work_dir / "captions.ass"
        if node.subtitle_path is None:
            write_ass(node, subtitle)
        if not subtitle.is_file():
            raise EngineError(
                ErrorCode.MEDIA_NOT_FOUND,
                "subtitle sidecar does not exist",
                context={"path": str(subtitle)},
            )
        escaped = _escape_filter_path(subtitle)
        fonts_dir = work_dir / "fonts"
        if node.font_paths:
            fonts_dir.mkdir(parents=True, exist_ok=True)
            for index, font_path in enumerate(node.font_paths):
                source_font = Path(font_path)
                if not source_font.is_file():
                    raise EngineError(
                        ErrorCode.MEDIA_NOT_FOUND,
                        "resolved caption font is missing",
                        context={"path": font_path},
                    )
                shutil.copy2(source_font, fonts_dir / f"{index}-{source_font.name}")
        font_option = f":fontsdir='{_escape_filter_path(fonts_dir)}'" if node.font_paths else ""
        offset = _number(_seconds(node.timeline_offset))
        filters = (
            f"setpts=PTS+{offset}/TB,subtitles=filename='{escaped}'{font_option},"
            f"setpts=PTS-{offset}/TB"
        )
        self._run_video_filter(source.path, output, filters)
        return BackendExecution(
            path=output,
            metadata={
                "subtitle_path": str(subtitle),
                "font_paths": list(node.font_paths),
                "timeline_offset": node.timeline_offset.model_dump(mode="json"),
            },
        )

    def _audio_process(
        self, node: AudioProcessNode, source: RenderArtifact, output: Path
    ) -> BackendExecution:
        filters: list[str] = [f"aformat=channel_layouts={node.channel_layout}"]
        for processor in node.processors:
            parameters = processor.parameters
            if processor.kind == "gain":
                gain_db = _float_parameter(parameters, "db", 0)
                if processor.automation:
                    db_expression = self._automation_expression(
                        processor.automation,
                        gain_db,
                        node.sample_rate,
                        processor.automation_offset,
                    )
                    linear_expression = f"pow(10\\,({db_expression})/20)"
                    filters.append(self._aeval_gain_filter(linear_expression, node.channel_layout))
                else:
                    filters.append(f"volume={_number(gain_db)}dB")
            elif processor.kind == "pan":
                if node.channel_layout != "stereo":
                    raise EngineError(
                        ErrorCode.UNSUPPORTED_CAPABILITY,
                        "pan processing currently requires a stereo bus",
                        context={"channel_layout": node.channel_layout},
                    )
                pan = max(-1.0, min(1.0, _float_parameter(parameters, "value", 0)))
                if processor.automation:
                    pan_expression = self._automation_expression(
                        processor.automation,
                        pan,
                        node.sample_rate,
                        processor.automation_offset,
                    )
                    left_expression = f"min(1\\,1-({pan_expression}))"
                    right_expression = f"min(1\\,1+({pan_expression}))"
                    filters.append(
                        "aeval=exprs='"
                        f"val(0)*({left_expression})|val(1)*({right_expression})'"
                        ":c=same"
                    )
                else:
                    left = min(1.0, 1.0 - pan)
                    right = min(1.0, 1.0 + pan)
                    filters.append(f"pan=stereo|c0={_number(left)}*c0|c1={_number(right)}*c1")
            elif processor.kind == "fade":
                fade_type = _string_parameter(parameters, "type", "in")
                start = _rational_parameter(parameters, "start", RationalTime.zero())
                duration = _rational_parameter(
                    parameters,
                    "duration",
                    RationalTime(value=3, timescale=100),
                )
                start_sample = AudioSampleTime.from_time(
                    start, node.sample_rate, RoundingMode.EXACT
                ).samples
                duration_samples = AudioSampleTime.from_time(
                    duration, node.sample_rate, RoundingMode.EXACT
                ).samples
                filters.append(f"afade=t={fade_type}:ss={start_sample}:ns={duration_samples}")
            elif processor.kind == "eq":
                filters.append(
                    f"equalizer=f={_float_parameter(parameters, 'frequency', 1000):g}:"
                    f"width_type=q:width={_float_parameter(parameters, 'q', 1):g}:"
                    f"g={_float_parameter(parameters, 'gain_db', 0):g}"
                )
            elif processor.kind == "compression":
                filters.append(
                    "acompressor="
                    f"threshold={_float_parameter(parameters, 'threshold_db', -18):g}dB:"
                    f"ratio={_float_parameter(parameters, 'ratio', 4):g}:"
                    f"attack={_float_parameter(parameters, 'attack_ms', 20):g}:"
                    f"release={_float_parameter(parameters, 'release_ms', 250):g}"
                )
            elif processor.kind == "limiter":
                filters.append(
                    f"alimiter=limit={_float_parameter(parameters, 'linear_peak', 0.95):g}"
                )
            elif processor.kind == "gate":
                filters.append(
                    f"agate=threshold={_float_parameter(parameters, 'threshold_db', -45):g}dB"
                )
            elif processor.kind == "de_esser":
                filters.append(f"deesser=i={_float_parameter(parameters, 'intensity', 0.5):g}")
            elif processor.kind == "noise_reduction":
                filters.append(f"afftdn=nr={_float_parameter(parameters, 'reduction_db', 12):g}")
            elif processor.kind == "channel_map":
                raw_map = parameters.get("map")
                if raw_map is not None:
                    if (
                        not isinstance(raw_map, list)
                        or not raw_map
                        or not all(
                            isinstance(channel, int)
                            and not isinstance(channel, bool)
                            and channel >= 0
                            for channel in raw_map
                        )
                    ):
                        raise EngineError(
                            ErrorCode.INVALID_TIMELINE,
                            "channel map must be a non-empty list of channel indices",
                            context={"map": raw_map},
                        )
                    layout = (
                        "mono"
                        if len(raw_map) == 1
                        else ("stereo" if len(raw_map) == 2 else f"{len(raw_map)}c")
                    )
                    routes = "|".join(
                        f"c{output_channel}=c{input_channel}"
                        for output_channel, input_channel in enumerate(raw_map)
                    )
                    filters.append(f"pan={layout}|{routes}")
                else:
                    layout = _string_parameter(parameters, "layout", "stereo")
                    filters.append(f"aformat=channel_layouts={layout}")
            elif processor.kind == "sample_rate_convert":
                filters.append(
                    f"aresample={_int_parameter(parameters, 'sample_rate', node.sample_rate)}"
                )
        filters.append(f"aresample={node.sample_rate}:async=0:first_pts=0")
        self._run_audio_filter(source.path, output, ",".join(filters))
        return BackendExecution(path=output)

    @staticmethod
    def _channel_count(channel_layout: str) -> int:
        known = {
            "mono": 1,
            "stereo": 2,
            "2.1": 3,
            "3.0": 3,
            "4.0": 4,
            "5.1": 6,
            "5.1(side)": 6,
            "7.1": 8,
        }
        try:
            return known[channel_layout]
        except KeyError as exc:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "automation requires a recognized channel layout",
                context={"channel_layout": channel_layout},
            ) from exc

    @classmethod
    def _aeval_gain_filter(cls, expression: str, channel_layout: str) -> str:
        channels = cls._channel_count(channel_layout)
        expressions = "|".join(f"val({channel})*({expression})" for channel in range(channels))
        return f"aeval=exprs='{expressions}':c=same"

    @staticmethod
    def _automation_expression(
        points: tuple[AudioAutomationPoint, ...],
        base_value: float,
        sample_rate: int,
        time_offset: RationalTime,
    ) -> str:
        sampled: list[tuple[int, float, Interpolation]] = []
        for point in points:
            try:
                sample = AudioSampleTime.from_time(
                    point.time, sample_rate, RoundingMode.EXACT
                ).samples
            except ValueError as exc:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "audio automation point is not aligned to the sample grid",
                    context={"time": point.time.model_dump(mode="json")},
                ) from exc
            sampled.append((sample, point.value, point.interpolation))
        if not sampled or sampled[0][0] > 0:
            sampled.insert(0, (0, base_value, Interpolation.LINEAR))
        try:
            offset_sample = AudioSampleTime.from_time(
                time_offset, sample_rate, RoundingMode.EXACT
            ).samples
        except ValueError as exc:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "audio automation offset is not aligned to the sample grid",
                context={"time": time_offset.model_dump(mode="json")},
            ) from exc
        time_variable = f"(n+{offset_sample})" if offset_sample else "n"
        expression = _number(sampled[-1][1])
        for (start, start_value, interpolation), (end, end_value, _) in reversed(
            list(pairwise(sampled))
        ):
            if interpolation is Interpolation.BEZIER:
                raise EngineError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "Bezier audio automation requires explicit curve control points",
                )
            progress = f"({time_variable}-{start})/{end - start}"
            if interpolation is Interpolation.HOLD:
                curve = "0"
            elif interpolation is Interpolation.EASE_IN:
                curve = f"pow({progress}\\,2)"
            elif interpolation is Interpolation.EASE_OUT:
                curve = f"1-pow(1-({progress})\\,2)"
            elif interpolation is Interpolation.EASE_IN_OUT:
                curve = (
                    f"if(lt({progress}\\,0.5)\\,2*pow({progress}\\,2)\\,"
                    f"1-pow(-2*({progress})+2\\,2)/2)"
                )
            else:
                curve = progress
            segment = f"{_number(start_value)}+({_number(end_value - start_value)})*({curve})"
            expression = f"if(lt({time_variable}\\,{end})\\,{segment}\\,{expression})"
        return f"if(lt({time_variable}\\,0)\\,{_number(base_value)}\\,{expression})"

    def _run_audio_filter(self, source: Path, output: Path, audio_filter: str) -> None:
        self._run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-i",
                str(source),
                "-vn",
                "-af",
                audio_filter,
                "-c:a",
                "pcm_f32le",
                str(output),
            ]
        )

    def _audio_sidechain(
        self,
        node: AudioSidechainNode,
        inputs: tuple[RenderArtifact, ...],
        output: Path,
    ) -> BackendExecution:
        threshold = 10 ** (node.threshold_db / 20)
        makeup = 10 ** (node.makeup_db / 20)
        filter_value = (
            "[0:a][1:a]sidechaincompress="
            f"threshold={_number(threshold)}:ratio={_number(node.ratio)}:"
            f"attack={_number(node.attack_ms)}:release={_number(node.release_ms)}:"
            f"makeup={_number(makeup)}:mix={_number(node.mix)}[outa]"
        )
        self._run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-i",
                str(inputs[0].path),
                "-i",
                str(inputs[1].path),
                "-filter_complex",
                filter_value,
                "-map",
                "[outa]",
                "-c:a",
                "pcm_f32le",
                "-ar",
                str(node.sample_rate),
                str(output),
            ]
        )
        return BackendExecution(path=output)

    def _audio_mix(
        self,
        node: AudioMixNode,
        inputs: tuple[RenderArtifact, ...],
        output: Path,
        work_dir: Path,
    ) -> BackendExecution:
        duration = _seconds(node.duration)
        target_samples = AudioSampleTime.from_time(
            node.duration, node.sample_rate, node.sample_rounding
        ).samples
        if not inputs:
            self._run(
                [
                    self.config.ffmpeg_path,
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"anullsrc=r={node.sample_rate}:cl={node.channel_layout}",
                    "-t",
                    _number(duration),
                    "-af",
                    f"atrim=end_sample={target_samples},asetpts=PTS-STARTPTS",
                    "-c:a",
                    "pcm_f32le",
                    str(output),
                ]
            )
            return BackendExecution(path=output)
        command = [self.config.ffmpeg_path, "-y"]
        for artifact in inputs:
            command.extend(["-i", str(artifact.path)])
        filters: list[str] = []
        labels: list[str] = []
        for index, item in enumerate(node.mix_inputs):
            sample_time = AudioSampleTime.from_time(
                item.start,
                node.sample_rate,
                node.sample_rounding,
            )
            chain = f"[{index}:a]asetpts=PTS-STARTPTS"
            if sample_time.samples:
                chain += f",adelay={sample_time.samples}S:all=1"
            if item.gain_db:
                chain += f",volume={_number(item.gain_db)}dB"
            if item.pan:
                left = min(1.0, 1.0 - item.pan)
                right = min(1.0, 1.0 + item.pan)
                chain += f",pan=stereo|c0={_number(left)}*c0|c1={_number(right)}*c1"
            if item.fade_in.value:
                fade_samples = AudioSampleTime.from_time(
                    item.fade_in, node.sample_rate, node.sample_rounding
                ).samples
                chain += f",afade=t=in:ss=0:ns={fade_samples}"
            if item.fade_out.value:
                if item.duration is None:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "audio mix fade-out requires the input duration",
                        context={"input_id": item.input_id},
                    )
                duration_samples = AudioSampleTime.from_time(
                    item.duration, node.sample_rate, node.sample_rounding
                ).samples
                fade_samples = AudioSampleTime.from_time(
                    item.fade_out, node.sample_rate, node.sample_rounding
                ).samples
                chain += (
                    f",afade=t=out:ss={max(0, duration_samples - fade_samples)}:ns={fade_samples}"
                )
            chain += f"[a{index}]"
            filters.append(chain)
            labels.append(f"[a{index}]")
        filters.append(
            "".join(labels)
            + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0,"
            f"apad=whole_len={target_samples},atrim=end_sample={target_samples},"
            f"asetpts=PTS-STARTPTS,aresample={node.sample_rate}:async=0:first_pts=0,"
            f"aformat=channel_layouts={node.channel_layout}[outa]"
        )
        script = work_dir / "audio_filtergraph.txt"
        script.write_text(";\n".join(filters) + "\n", encoding="utf-8")
        command.extend(
            [
                "-filter_complex_script",
                str(script),
                "-map",
                "[outa]",
                "-c:a",
                "pcm_f32le",
                "-ar",
                str(node.sample_rate),
                str(output),
            ]
        )
        self._run(command)
        return BackendExecution(path=output, metadata={"filtergraph": str(script)})

    def _loudness(
        self, node: LoudnessNode, source: RenderArtifact, output: Path
    ) -> BackendExecution:
        profile = node.profile
        base = (
            f"loudnorm=I={profile.integrated_lufs:g}:TP={profile.true_peak_dbtp:g}:"
            f"LRA={profile.loudness_range_lu:g}"
        )
        if node.mode == "single_pass":
            self._run_audio_filter(
                source.path, output, f"{base},aresample={node.sample_rate}:async=0:first_pts=0"
            )
            return BackendExecution(path=output, metadata={"mode": "single_pass"})
        measurement = self.runner.run(
            [
                self.config.ffmpeg_path,
                "-hide_banner",
                "-nostats",
                "-i",
                str(source.path),
                "-af",
                f"{base}:print_format=json",
                "-f",
                "null",
                "-",
            ],
            check=False,
        )
        match = re.search(r"\{[^{}]+\}", measurement.stderr[measurement.stderr.rfind("{") :], re.S)
        if measurement.return_code != 0 or match is None:
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "FFmpeg loudness measurement failed",
                context={"stderr": measurement.stderr[-2000:]},
            )
        measured = json.loads(match.group(0))
        required = {"input_i", "input_tp", "input_lra", "input_thresh", "target_offset"}
        if not required.issubset(measured):
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "FFmpeg loudness measurement was incomplete",
                context={"measurement": measured},
            )
        if str(measured["input_i"]).lower() in {"-inf", "inf", "nan"}:
            self._run_audio_filter(
                source.path,
                output,
                f"aresample={node.sample_rate}:async=0:first_pts=0",
            )
            return BackendExecution(
                path=output,
                metadata={"mode": "two_pass", "normalization": "skipped_silence"},
            )
        second_pass = (
            f"{base}:measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
            f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
            f"offset={measured['target_offset']}:linear=true"
        )
        self._run_audio_filter(
            source.path,
            output,
            f"{second_pass},aresample={node.sample_rate}:async=0:first_pts=0",
        )
        metadata: dict[str, JsonValue] = {str(key): str(value) for key, value in measured.items()}
        metadata["mode"] = "two_pass"
        return BackendExecution(path=output, metadata=metadata)

    def _output_transform(
        self,
        node: OutputTransformNode,
        source: RenderArtifact,
        output: Path,
    ) -> BackendExecution:
        if node.pixel_format in {"yuv420p", "yuv420p10le"} and (node.width % 2 or node.height % 2):
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "4:2:0 output dimensions must be even",
                context={"width": node.width, "height": node.height},
            )
        scale = ScaleNode(
            id=f"{node.id}-scale",
            inputs=(source.node_id,),
            artifact_type=ArtifactType.VIDEO,
            width=node.width,
            height=node.height,
            fit=node.fit,
        )
        rate = f"{node.frame_rate.numerator}/{node.frame_rate.denominator}"
        video_filter = (
            self._color_filter(
                ColorConversionNode(
                    id=f"{node.id}-color",
                    inputs=(source.node_id,),
                    artifact_type=ArtifactType.VIDEO,
                    input_space=node.input_color_space,
                    output_space=node.color_space,
                    tone_map=(
                        "hable"
                        if node.input_color_space in {ColorSpace.HLG, ColorSpace.PQ}
                        and node.color_space in {ColorSpace.REC709, ColorSpace.REC2020}
                        else "none"
                    ),
                )
            )
            + ","
            if node.input_color_space is not node.color_space
            else ""
        ) + f"{self._scale_filter(scale)},fps={rate}:round=near,format={node.pixel_format}"
        self._run_video_filter(
            source.path,
            output,
            video_filter,
            pixel_format=node.pixel_format,
        )
        return BackendExecution(
            path=output,
            metadata={
                "color_space": node.color_space.value,
                "pixel_format": node.pixel_format,
                "frame_rate": rate,
            },
        )

    def _encode(self, node: EncodeNode, source: RenderArtifact, output: Path) -> BackendExecution:
        command = [self.config.ffmpeg_path, "-y", "-i", str(source.path)]
        if node.artifact_type is ArtifactType.ENCODED_AUDIO:
            command.extend(["-vn", "-c:a", node.codec])
            if node.bitrate:
                command.extend(["-b:a", node.bitrate])
            if node.sample_rate:
                command.extend(["-ar", str(node.sample_rate)])
            if node.channels:
                command.extend(["-ac", str(node.channels)])
            if node.channel_layout:
                command.extend(["-channel_layout", node.channel_layout])
        else:
            command.extend(["-an", "-c:v", node.codec])
            if node.preset:
                command.extend(["-preset", node.preset])
            if node.crf is not None:
                command.extend(["-crf", str(node.crf)])
            if node.bitrate:
                command.extend(["-b:v", node.bitrate])
            if node.pixel_format:
                command.extend(["-pix_fmt", node.pixel_format])
            color_space = source.metadata.get("color_space")
            tags = {
                ColorSpace.REC709.value: ("bt709", "bt709", "bt709"),
                ColorSpace.REC2020.value: ("bt2020", "bt709", "bt2020nc"),
                ColorSpace.HLG.value: ("bt2020", "arib-std-b67", "bt2020nc"),
                ColorSpace.PQ.value: ("bt2020", "smpte2084", "bt2020nc"),
                ColorSpace.LINEAR.value: ("bt709", "linear", "bt709"),
            }.get(str(color_space))
            if tags is not None:
                command.extend(
                    [
                        "-color_primaries",
                        tags[0],
                        "-color_trc",
                        tags[1],
                        "-colorspace",
                        tags[2],
                        "-color_range",
                        "tv",
                    ]
                )
        command.append(str(output))
        self._run(command)
        return BackendExecution(path=output)

    def _mux(
        self, node: MuxNode, inputs: tuple[RenderArtifact, ...], output: Path
    ) -> BackendExecution:
        command = [self.config.ffmpeg_path, "-y"]
        for artifact in inputs:
            command.extend(["-i", str(artifact.path)])
        video_index = next(
            (
                index
                for index, artifact in enumerate(inputs)
                if artifact.artifact_type is ArtifactType.ENCODED_VIDEO
            ),
            None,
        )
        audio_index = next(
            (
                index
                for index, artifact in enumerate(inputs)
                if artifact.artifact_type is ArtifactType.ENCODED_AUDIO
            ),
            None,
        )
        if video_index is not None:
            command.extend(["-map", f"{video_index}:v:0"])
        if audio_index is not None:
            command.extend(["-map", f"{audio_index}:a:0"])
        if video_index is None and audio_index is None:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "mux requires an encoded video or audio artifact",
            )
        command.extend(["-c", "copy"])
        if node.shortest and video_index is not None and audio_index is not None:
            command.append("-shortest")
        if node.fast_start and node.container in {"mp4", "mov"}:
            command.extend(["-movflags", "+faststart"])
        command.append(str(output))
        self._run(command)
        return BackendExecution(path=output)
