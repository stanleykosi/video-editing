"""Immutable, backend-neutral render node definitions."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import (
    CaptionStyle,
    CaptionStyleOverride,
    ColorSpace,
    Interpolation,
    JsonValue,
    LoudnessProfile,
    Retime,
    SpeedRampPoint,
    TransitionKind,
)
from video_engine.core.time import (
    FrameRate,
    RationalRate,
    RationalTime,
    RoundingMode,
    TimeRange,
)
from video_engine.graphics.models import GraphicAsset, GraphicBoundsPolicy, GraphicRenderer


class NodeKind(StrEnum):
    DECODE = "decode"
    TRIM = "trim"
    CONFORM = "conform"
    SCALE = "scale"
    CROP = "crop"
    TRANSFORM = "transform"
    SPEED = "speed"
    SPEED_RAMP = "speed_ramp"
    REVERSE = "reverse"
    FREEZE = "freeze"
    COLOR_CONVERSION = "color_conversion"
    GRADE = "grade"
    MASK = "mask"
    BLUR = "blur"
    SHADOW = "shadow"
    GLOW = "glow"
    PERSPECTIVE = "perspective"
    DISTORTION = "distortion"
    COMPOSITE = "composite"
    CONCAT = "concat"
    TRANSITION = "transition"
    CAPTION = "caption"
    MOTION_GRAPHIC = "motion_graphic"
    AUDIO_PROCESS = "audio_process"
    AUDIO_SIDECHAIN = "audio_sidechain"
    AUDIO_MIX = "audio_mix"
    LOUDNESS = "loudness"
    OUTPUT_TRANSFORM = "output_transform"
    ENCODE = "encode"
    MUX = "mux"


class ArtifactType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    AUDIO_VIDEO = "audio_video"
    IMAGE = "image"
    MASK = "mask"
    SUBTITLE = "subtitle"
    METADATA = "metadata"
    CONTAINER = "container"
    ENCODED_VIDEO = "encoded_video"
    ENCODED_AUDIO = "encoded_audio"


class RenderNodeBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    node_version: int = Field(default=1, ge=1)
    inputs: tuple[str, ...] = ()
    artifact_type: ArtifactType
    cacheable: bool = True
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class DecodeNode(RenderNodeBase):
    node_type: Literal[NodeKind.DECODE] = NodeKind.DECODE
    cacheable: bool = False
    source_uri: str = Field(min_length=1)
    snapshot_uri: str | None = Field(default=None, min_length=1)
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    video_stream_index: int | None = Field(default=None, ge=0)
    audio_stream_index: int | None = Field(default=None, ge=0)
    still_image: bool = False
    stream_metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def decode_has_no_inputs(self) -> DecodeNode:
        if self.inputs:
            raise ValueError("decode nodes cannot have graph inputs")
        return self


class TrimNode(RenderNodeBase):
    node_type: Literal[NodeKind.TRIM] = NodeKind.TRIM
    source_range: TimeRange
    audio_fade_in: RationalTime = Field(default_factory=RationalTime.zero)
    audio_fade_out: RationalTime = Field(default_factory=RationalTime.zero)
    audio_sample_rate: int | None = Field(default=None, gt=0)
    audio_rounding: RoundingMode = RoundingMode.NEAREST


class ConformNode(RenderNodeBase):
    node_type: Literal[NodeKind.CONFORM] = NodeKind.CONFORM
    frame_rate: FrameRate
    sample_rate: int = Field(gt=0)
    frame_policy: Literal["passthrough", "duplicate_drop", "blend"] = "duplicate_drop"


class VisualAutomationPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    property_path: Literal[
        "position_x",
        "position_y",
        "scale_x",
        "scale_y",
        "rotation_degrees",
        "opacity",
        "crop_width",
        "crop_height",
        "crop_x",
        "crop_y",
        "corner_radius",
        "focus_x",
        "focus_y",
        "reframe_zoom",
        "top_left_x",
        "top_left_y",
        "top_right_x",
        "top_right_y",
        "bottom_left_x",
        "bottom_left_y",
        "bottom_right_x",
        "bottom_right_y",
        "anchor_x",
        "anchor_y",
        "region_x",
        "region_y",
        "region_width",
        "region_height",
    ]
    time: RationalTime
    value: float
    interpolation: Interpolation = Interpolation.LINEAR
    in_tangent: tuple[float, float] | None = None
    out_tangent: tuple[float, float] | None = None


def _validate_visual_automation(
    points: tuple[VisualAutomationPoint, ...], allowed: set[str]
) -> None:
    identities: set[tuple[str, RationalTime]] = set()
    for point in points:
        if point.property_path not in allowed:
            raise ValueError(
                f"automation property {point.property_path!r} is invalid for this node"
            )
        identity = (point.property_path, point.time)
        if identity in identities:
            raise ValueError("visual automation contains duplicate property times")
        identities.add(identity)


class ScaleNode(RenderNodeBase):
    node_type: Literal[NodeKind.SCALE] = NodeKind.SCALE
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fit: Literal["cover", "contain", "stretch"] = "cover"
    focus_x: float = Field(default=0.5, ge=0, le=1)
    focus_y: float = Field(default=0.5, ge=0, le=1)
    zoom: float = Field(default=1, ge=1, le=100)
    automation: tuple[VisualAutomationPoint, ...] = ()
    automation_offset: RationalTime = Field(default_factory=RationalTime.zero)
    algorithm: Literal["bicubic", "bilinear", "lanczos", "spline"] = "lanczos"
    pad_color: str = "black"

    @model_validator(mode="after")
    def valid_reframe_automation(self) -> ScaleNode:
        _validate_visual_automation(self.automation, {"focus_x", "focus_y", "reframe_zoom"})
        if self.fit != "cover" and (
            self.zoom != 1 or self.focus_x != 0.5 or self.focus_y != 0.5 or self.automation
        ):
            raise ValueError("non-cover fit does not accept focus or zoom controls")
        return self


class CropNode(RenderNodeBase):
    node_type: Literal[NodeKind.CROP] = NodeKind.CROP
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)
    canvas_width: int | None = Field(default=None, gt=0)
    canvas_height: int | None = Field(default=None, gt=0)
    automation: tuple[VisualAutomationPoint, ...] = ()
    automation_offset: RationalTime = Field(default_factory=RationalTime.zero)

    @model_validator(mode="after")
    def complete_canvas(self) -> CropNode:
        if (self.canvas_width is None) != (self.canvas_height is None):
            raise ValueError("crop canvas dimensions must be supplied together")
        if (
            self.canvas_width is not None
            and self.canvas_height is not None
            and (
                self.x + self.width > self.canvas_width or self.y + self.height > self.canvas_height
            )
        ):
            raise ValueError("crop rectangle extends outside the fixed canvas")
        _validate_visual_automation(
            self.automation, {"crop_width", "crop_height", "crop_x", "crop_y"}
        )
        return self


class TransformNode(RenderNodeBase):
    node_type: Literal[NodeKind.TRANSFORM] = NodeKind.TRANSFORM
    position_x: float = 0.0
    position_y: float = 0.0
    scale_x: float = Field(default=1.0, gt=0)
    scale_y: float = Field(default=1.0, gt=0)
    rotation_degrees: float = 0.0
    anchor_x: float = Field(default=0.5, ge=0, le=1)
    anchor_y: float = Field(default=0.5, ge=0, le=1)
    opacity: float = Field(default=1.0, ge=0, le=1)
    canvas_width: int | None = Field(default=None, gt=0)
    canvas_height: int | None = Field(default=None, gt=0)
    automation: tuple[VisualAutomationPoint, ...] = ()
    automation_offset: RationalTime = Field(default_factory=RationalTime.zero)

    @model_validator(mode="after")
    def complete_canvas(self) -> TransformNode:
        if (self.canvas_width is None) != (self.canvas_height is None):
            raise ValueError("transform canvas dimensions must be supplied together")
        _validate_visual_automation(
            self.automation,
            {
                "position_x",
                "position_y",
                "scale_x",
                "scale_y",
                "rotation_degrees",
                "opacity",
                "anchor_x",
                "anchor_y",
            },
        )
        if self.automation and self.canvas_width is None:
            raise ValueError("automated transforms require fixed canvas dimensions")
        return self


class SpeedNode(RenderNodeBase):
    node_type: Literal[NodeKind.SPEED] = NodeKind.SPEED
    rate: RationalRate
    duration: RationalTime
    frame_rate: FrameRate
    sample_rate: int = Field(gt=0)

    @model_validator(mode="after")
    def valid_speed(self) -> SpeedNode:
        if self.artifact_type not in {ArtifactType.VIDEO, ArtifactType.AUDIO}:
            raise ValueError("speed nodes support only video or audio artifacts")
        if self.duration.value <= 0:
            raise ValueError("speed-node duration must be positive")
        return self


class SpeedRampNode(RenderNodeBase):
    node_type: Literal[NodeKind.SPEED_RAMP] = NodeKind.SPEED_RAMP
    points: tuple[SpeedRampPoint, ...] = Field(min_length=2)
    duration: RationalTime
    frame_rate: FrameRate
    sample_rate: int = Field(gt=0)

    @model_validator(mode="after")
    def valid_ramp(self) -> SpeedRampNode:
        if self.artifact_type not in {ArtifactType.VIDEO, ArtifactType.AUDIO}:
            raise ValueError("speed-ramp nodes support only video or audio artifacts")
        if self.duration.value <= 0:
            raise ValueError("speed-ramp duration must be positive")
        if self.points[0].time != RationalTime.zero():
            raise ValueError("speed-ramp node must begin at zero")
        if self.points[-1].time != self.duration:
            raise ValueError("speed-ramp node must end at its duration")
        Retime(speed_ramp=self.points)
        return self


class ReverseNode(RenderNodeBase):
    node_type: Literal[NodeKind.REVERSE] = NodeKind.REVERSE
    reverse_video: bool = True
    reverse_audio: bool = True


class FreezeNode(RenderNodeBase):
    node_type: Literal[NodeKind.FREEZE] = NodeKind.FREEZE
    frame_time: RationalTime
    duration: RationalTime
    frame_rate: FrameRate

    @model_validator(mode="after")
    def positive_duration(self) -> FreezeNode:
        if self.artifact_type is not ArtifactType.VIDEO:
            raise ValueError("freeze nodes require video artifacts")
        if self.frame_time.value < 0:
            raise ValueError("freeze frame time must be nonnegative")
        if self.duration.value <= 0:
            raise ValueError("freeze duration must be positive")
        self.frame_rate.time_to_frames(self.frame_time, RoundingMode.EXACT)
        self.frame_rate.time_to_frames(self.duration, RoundingMode.EXACT)
        return self


class ColorConversionNode(RenderNodeBase):
    node_type: Literal[NodeKind.COLOR_CONVERSION] = NodeKind.COLOR_CONVERSION
    input_space: ColorSpace
    output_space: ColorSpace
    tone_map: Literal["none", "hable", "mobius", "reinhard", "clip"] = "none"
    peak_nits: float = Field(default=100.0, gt=0)


class GradeNode(RenderNodeBase):
    node_type: Literal[NodeKind.GRADE] = NodeKind.GRADE
    exposure_stops: float = Field(default=0.0, ge=-10, le=10)
    temperature: float = Field(default=0.0, ge=-1, le=1)
    tint: float = Field(default=0.0, ge=-1, le=1)
    contrast: float = Field(default=1.0, ge=0, le=4)
    gamma: float = Field(default=1.0, ge=0.1, le=10)
    saturation: float = Field(default=1.0, ge=0, le=4)
    highlights: float = Field(default=0.0, ge=-1, le=1)
    shadows: float = Field(default=0.0, ge=-1, le=1)
    lut_path: str | None = None
    enabled_range: TimeRange | None = None


class MaskNode(RenderNodeBase):
    node_type: Literal[NodeKind.MASK] = NodeKind.MASK
    mode: Literal[
        "alpha_matte",
        "luma_matte",
        "chroma",
        "luma_key",
        "rounded_rectangle",
        "rectangle",
        "ellipse",
    ] = "alpha_matte"
    key_color: str = "0x00FF00"
    similarity: float = Field(default=0.1, ge=0, le=1)
    blend: float = Field(default=0.0, ge=0, le=1)
    threshold: float = Field(default=0.5, ge=0, le=1)
    softness: float = Field(default=0, ge=0, le=1)
    corner_radius: float = Field(default=0, ge=0)
    x: float = Field(default=0, ge=0, le=1)
    y: float = Field(default=0, ge=0, le=1)
    width: float = Field(default=1, gt=0, le=1)
    height: float = Field(default=1, gt=0, le=1)
    feather: float = Field(default=0, ge=0, le=0.5)
    canvas_width: int | None = Field(default=None, gt=0)
    canvas_height: int | None = Field(default=None, gt=0)
    invert: bool = False
    automation: tuple[VisualAutomationPoint, ...] = ()
    automation_offset: RationalTime = Field(default_factory=RationalTime.zero)

    @model_validator(mode="after")
    def valid_mask(self) -> MaskNode:
        if (self.canvas_width is None) != (self.canvas_height is None):
            raise ValueError("mask canvas dimensions must be supplied together")
        if self.mode in {
            "alpha_matte",
            "luma_matte",
            "rounded_rectangle",
            "rectangle",
            "ellipse",
        } and (self.canvas_width is None):
            raise ValueError("this mask mode requires fixed canvas dimensions")
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("mask region extends outside normalized canvas")
        _validate_visual_automation(
            self.automation,
            {"corner_radius", "region_x", "region_y", "region_width", "region_height"},
        )
        return self


class BlurNode(RenderNodeBase):
    node_type: Literal[NodeKind.BLUR] = NodeKind.BLUR
    sigma: float = Field(default=10, gt=0, le=1024)
    steps: int = Field(default=2, ge=1, le=6)
    region_shape: Literal["full", "rectangle", "ellipse"] = "full"
    region_policy: Literal["inside", "outside"] | None = None
    x: float = Field(default=0, ge=0, le=1)
    y: float = Field(default=0, ge=0, le=1)
    width: float = Field(default=1, gt=0, le=1)
    height: float = Field(default=1, gt=0, le=1)
    feather: float = Field(default=0, ge=0, le=0.5)
    canvas_width: int | None = Field(default=None, gt=0)
    canvas_height: int | None = Field(default=None, gt=0)
    automation: tuple[VisualAutomationPoint, ...] = ()
    automation_offset: RationalTime = Field(default_factory=RationalTime.zero)

    @model_validator(mode="after")
    def valid_region(self) -> BlurNode:
        if (self.canvas_width is None) != (self.canvas_height is None):
            raise ValueError("blur canvas dimensions must be supplied together")
        if self.region_shape != "full" and (
            self.canvas_width is None or self.region_policy is None
        ):
            raise ValueError("selective blur requires canvas dimensions and region policy")
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("blur region extends outside normalized canvas")
        _validate_visual_automation(
            self.automation, {"region_x", "region_y", "region_width", "region_height"}
        )
        return self


class ShadowNode(RenderNodeBase):
    node_type: Literal[NodeKind.SHADOW] = NodeKind.SHADOW
    offset_x: float = 12
    offset_y: float = 12
    blur_sigma: float = Field(default=8, gt=0, le=1024)
    opacity: float = Field(default=0.5, ge=0, le=1)
    color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")
    canvas_width: int = Field(gt=0)
    canvas_height: int = Field(gt=0)


class GlowNode(RenderNodeBase):
    node_type: Literal[NodeKind.GLOW] = NodeKind.GLOW
    blur_sigma: float = Field(default=8, gt=0, le=1024)
    intensity: float = Field(default=0.6, ge=0, le=2)
    color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")


class PerspectiveNode(RenderNodeBase):
    node_type: Literal[NodeKind.PERSPECTIVE] = NodeKind.PERSPECTIVE
    top_left_x: float = Field(default=0, ge=0, le=1)
    top_left_y: float = Field(default=0, ge=0, le=1)
    top_right_x: float = Field(default=1, ge=0, le=1)
    top_right_y: float = Field(default=0, ge=0, le=1)
    bottom_left_x: float = Field(default=0, ge=0, le=1)
    bottom_left_y: float = Field(default=1, ge=0, le=1)
    bottom_right_x: float = Field(default=1, ge=0, le=1)
    bottom_right_y: float = Field(default=1, ge=0, le=1)
    interpolation: Literal["linear", "cubic"] = "cubic"
    frame_rate: FrameRate
    automation: tuple[VisualAutomationPoint, ...] = ()
    automation_offset: RationalTime = Field(default_factory=RationalTime.zero)

    @model_validator(mode="after")
    def valid_perspective_automation(self) -> PerspectiveNode:
        _validate_visual_automation(
            self.automation,
            {
                "top_left_x",
                "top_left_y",
                "top_right_x",
                "top_right_y",
                "bottom_left_x",
                "bottom_left_y",
                "bottom_right_x",
                "bottom_right_y",
            },
        )
        return self


class DistortionNode(RenderNodeBase):
    node_type: Literal[NodeKind.DISTORTION] = NodeKind.DISTORTION
    center_x: float = Field(default=0.5, ge=0, le=1)
    center_y: float = Field(default=0.5, ge=0, le=1)
    quadratic: float = Field(default=0, ge=-1, le=1)
    double_quadratic: float = Field(default=0, ge=-1, le=1)
    interpolation: Literal["nearest", "bilinear"] = "bilinear"


class CompositeLayer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_id: str = Field(min_length=1)
    timeline_range: TimeRange
    z_index: int = 0
    x: int = 0
    y: int = 0
    opacity: float = Field(default=1.0, ge=0, le=1)
    blend_mode: Literal[
        "normal", "multiply", "screen", "overlay", "darken", "lighten", "difference"
    ] = "normal"


class CompositeNode(RenderNodeBase):
    node_type: Literal[NodeKind.COMPOSITE] = NodeKind.COMPOSITE
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_rate: FrameRate
    duration: RationalTime
    background_color: str = "black"
    layers: tuple[CompositeLayer, ...]

    @model_validator(mode="after")
    def layers_match_inputs(self) -> CompositeNode:
        if tuple(layer.input_id for layer in self.layers) != self.inputs:
            raise ValueError("composite layer input ids must match node inputs in order")
        if self.duration.value <= 0:
            raise ValueError("composite duration must be positive")
        return self


class ConcatNode(RenderNodeBase):
    node_type: Literal[NodeKind.CONCAT] = NodeKind.CONCAT
    segment_durations: tuple[RationalTime, ...]
    frame_rate: FrameRate | None = None
    sample_rate: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def valid_segments(self) -> ConcatNode:
        if len(self.inputs) < 2:
            raise ValueError("concat requires at least two inputs")
        if len(self.segment_durations) != len(self.inputs):
            raise ValueError("concat segment durations must match its inputs")
        if any(duration.value <= 0 for duration in self.segment_durations):
            raise ValueError("concat segment durations must be positive")
        if self.artifact_type is ArtifactType.VIDEO and self.frame_rate is None:
            raise ValueError("video concat requires a frame rate")
        if self.artifact_type is ArtifactType.AUDIO and self.sample_rate is None:
            raise ValueError("audio concat requires a sample rate")
        if self.artifact_type not in {ArtifactType.VIDEO, ArtifactType.AUDIO}:
            raise ValueError("concat supports only video or audio artifacts")
        return self


class TransitionNode(RenderNodeBase):
    node_type: Literal[NodeKind.TRANSITION] = NodeKind.TRANSITION
    transition: TransitionKind
    duration: RationalTime
    offset: RationalTime
    audio_sample_rate: int | None = Field(default=None, gt=0)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class CaptionRenderWord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    timeline_range: TimeRange
    highlight: bool = False
    style_id: str | None = None


class CaptionRenderCue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    timeline_range: TimeRange
    words: tuple[CaptionRenderWord, ...] = ()
    style_id: str | None = None
    position: Literal["top", "center", "bottom", "custom"] = "bottom"
    speaker: str | None = None
    language: str = "und"
    position_x: float | None = Field(default=None, ge=0, le=1)
    position_y: float | None = Field(default=None, ge=0, le=1)
    style_overrides: CaptionStyleOverride = Field(default_factory=CaptionStyleOverride)

    @model_validator(mode="after")
    def valid_timing_and_position(self) -> CaptionRenderCue:
        if self.position == "custom" and (self.position_x is None or self.position_y is None):
            raise ValueError("custom render caption position requires coordinates")
        previous_end: RationalTime | None = None
        for word in self.words:
            if word.timeline_range.duration.value <= 0:
                raise ValueError("render caption word duration must be positive")
            if (
                word.timeline_range.start < self.timeline_range.start
                or word.timeline_range.end > self.timeline_range.end
            ):
                raise ValueError("render caption word timing must fall inside its cue")
            if previous_end is not None and word.timeline_range.start < previous_end:
                raise ValueError("render caption words must be ordered and non-overlapping")
            previous_end = word.timeline_range.end
        return self


class CaptionNode(RenderNodeBase):
    node_type: Literal[NodeKind.CAPTION] = NodeKind.CAPTION
    cues: tuple[CaptionRenderCue, ...] = ()
    subtitle_path: str | None = None
    format: Literal["ass", "srt", "webvtt"] = "ass"
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    styles: tuple[CaptionStyle, ...] = ()
    default_style_id: str = "default"
    timeline_offset: RationalTime = Field(default_factory=RationalTime.zero)
    font_paths: tuple[str, ...] = ()

    @model_validator(mode="after")
    def captions_have_source(self) -> CaptionNode:
        if not self.cues and self.subtitle_path is None:
            raise ValueError("caption node requires cues or a subtitle path")
        style_ids = [style.id for style in self.styles]
        if len(style_ids) != len(set(style_ids)):
            raise ValueError("caption node style ids must be unique")
        if self.cues and self.default_style_id not in set(style_ids):
            raise ValueError("caption node default style is missing")
        known_styles = set(style_ids)
        for cue in self.cues:
            references = {
                style_id
                for style_id in [cue.style_id, *(word.style_id for word in cue.words)]
                if style_id is not None
            }
            if references - known_styles:
                raise ValueError("caption render cue references a missing style")
        return self


class MotionGraphicNode(RenderNodeBase):
    node_type: Literal[NodeKind.MOTION_GRAPHIC] = NodeKind.MOTION_GRAPHIC
    component_id: str = Field(min_length=1)
    component_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    component_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    renderer: GraphicRenderer = GraphicRenderer.REMOTION
    bounds_policy: GraphicBoundsPolicy = GraphicBoundsPolicy.SAFE_AREA
    props: dict[str, JsonValue] = Field(default_factory=dict)
    assets: tuple[GraphicAsset, ...] = ()
    duration: RationalTime
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_rate: FrameRate
    composition_duration_frames: int = Field(gt=0)
    render_start_frame: int = Field(default=0, ge=0)
    render_duration_frames: int = Field(gt=0)
    transparent: bool = True

    @model_validator(mode="after")
    def valid_graphic_range(self) -> MotionGraphicNode:
        if self.duration.value <= 0:
            raise ValueError("motion graphic duration must be positive")
        if self.render_start_frame + self.render_duration_frames > self.composition_duration_frames:
            raise ValueError("motion graphic range exceeds composition duration")
        if self.frame_rate.frames_to_time(self.render_duration_frames) != self.duration:
            raise ValueError("motion graphic duration must equal its rendered frame count")
        asset_ids = [asset.id for asset in self.assets]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("motion graphic asset ids must be unique")
        return self


class AudioAutomationPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    time: RationalTime
    value: float
    interpolation: Interpolation = Interpolation.LINEAR


class AudioProcessor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal[
        "gain",
        "pan",
        "fade",
        "eq",
        "compression",
        "limiter",
        "gate",
        "de_esser",
        "noise_reduction",
        "channel_map",
        "sample_rate_convert",
    ]
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    automation: tuple[AudioAutomationPoint, ...] = ()
    automation_offset: RationalTime = Field(default_factory=RationalTime.zero)

    @model_validator(mode="after")
    def automation_is_ordered(self) -> AudioProcessor:
        if any(point.time.value < 0 for point in self.automation):
            raise ValueError("audio automation times must be nonnegative")
        times = [point.time.fraction for point in self.automation]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ValueError("audio automation points must have unique ordered times")
        return self


class AudioProcessNode(RenderNodeBase):
    node_type: Literal[NodeKind.AUDIO_PROCESS] = NodeKind.AUDIO_PROCESS
    processors: tuple[AudioProcessor, ...]
    sample_rate: int = Field(gt=0)
    channel_layout: str = Field(default="stereo", min_length=1)


class AudioSidechainNode(RenderNodeBase):
    node_type: Literal[NodeKind.AUDIO_SIDECHAIN] = NodeKind.AUDIO_SIDECHAIN
    threshold_db: float = Field(default=-24, ge=-80, le=0)
    ratio: float = Field(default=6, ge=1, le=100)
    attack_ms: float = Field(default=20, gt=0)
    release_ms: float = Field(default=250, gt=0)
    makeup_db: float = Field(default=0, ge=0, le=24)
    mix: float = Field(default=1, ge=0, le=1)
    sample_rate: int = Field(default=48_000, gt=0)
    channel_layout: str = Field(default="stereo", min_length=1)


class AudioMixInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_id: str = Field(min_length=1)
    start: RationalTime
    duration: RationalTime | None = None
    gain_db: float = 0.0
    pan: float = Field(default=0.0, ge=-1, le=1)
    fade_in: RationalTime = Field(default_factory=RationalTime.zero)
    fade_out: RationalTime = Field(default_factory=RationalTime.zero)


class AudioMixNode(RenderNodeBase):
    node_type: Literal[NodeKind.AUDIO_MIX] = NodeKind.AUDIO_MIX
    mix_inputs: tuple[AudioMixInput, ...]
    duration: RationalTime
    sample_rate: int = Field(gt=0)
    channels: int = Field(default=2, ge=1, le=16)
    channel_layout: str = Field(default="stereo", min_length=1)
    sample_rounding: RoundingMode = RoundingMode.NEAREST

    @model_validator(mode="after")
    def mix_inputs_match(self) -> AudioMixNode:
        if tuple(item.input_id for item in self.mix_inputs) != self.inputs:
            raise ValueError("audio mix input ids must match node inputs in order")
        if self.duration.value <= 0:
            raise ValueError("audio mix duration must be positive")
        return self


class LoudnessNode(RenderNodeBase):
    node_type: Literal[NodeKind.LOUDNESS] = NodeKind.LOUDNESS
    profile: LoudnessProfile
    mode: Literal["single_pass", "two_pass"] = "two_pass"
    sample_rate: int = Field(default=48_000, gt=0)


class OutputTransformNode(RenderNodeBase):
    node_type: Literal[NodeKind.OUTPUT_TRANSFORM] = NodeKind.OUTPUT_TRANSFORM
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_rate: FrameRate
    fit: Literal["cover", "contain", "stretch"] = "cover"
    input_color_space: ColorSpace = ColorSpace.REC709
    color_space: ColorSpace = ColorSpace.REC709
    pixel_format: str = "yuv420p"


class EncodeNode(RenderNodeBase):
    node_type: Literal[NodeKind.ENCODE] = NodeKind.ENCODE
    codec: str = Field(min_length=1)
    bitrate: str | None = None
    crf: int | None = Field(default=None, ge=0, le=63)
    preset: str | None = None
    pixel_format: str | None = None
    sample_rate: int | None = Field(default=None, gt=0)
    channels: int | None = Field(default=None, ge=1, le=16)
    channel_layout: str | None = None


class MuxNode(RenderNodeBase):
    node_type: Literal[NodeKind.MUX] = NodeKind.MUX
    container: Literal["mp4", "mov", "mkv", "webm"] = "mp4"
    fast_start: bool = True
    shortest: bool = False


RenderNode = Annotated[
    DecodeNode
    | TrimNode
    | ConformNode
    | ScaleNode
    | CropNode
    | TransformNode
    | SpeedNode
    | SpeedRampNode
    | ReverseNode
    | FreezeNode
    | ColorConversionNode
    | GradeNode
    | MaskNode
    | BlurNode
    | ShadowNode
    | GlowNode
    | PerspectiveNode
    | DistortionNode
    | CompositeNode
    | ConcatNode
    | TransitionNode
    | CaptionNode
    | MotionGraphicNode
    | AudioProcessNode
    | AudioSidechainNode
    | AudioMixNode
    | LoudnessNode
    | OutputTransformNode
    | EncodeNode
    | MuxNode,
    Field(discriminator="node_type"),
]


ALL_NODE_KINDS = frozenset(NodeKind)
