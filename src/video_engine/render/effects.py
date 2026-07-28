"""Strict canonical effect parameter lowering models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from video_engine.core.schema import (
    ColorSpace,
    Effect,
    EffectKind,
    JsonValue,
    Transition,
    TransitionKind,
)
from video_engine.core.time import RationalTime, TimeRange
from video_engine.errors import EngineError, ErrorCode
from video_engine.render.nodes import AudioAutomationPoint, AudioProcessor


class EffectParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PositionParameters(EffectParameters):
    x: float = 0
    y: float = 0


class ScaleParameters(EffectParameters):
    x: float = Field(default=1, gt=0)
    y: float = Field(default=1, gt=0)


class RotationParameters(EffectParameters):
    degrees: float = 0


class AnchorParameters(EffectParameters):
    x: float = Field(default=0.5, ge=0, le=1)
    y: float = Field(default=0.5, ge=0, le=1)


class OpacityParameters(EffectParameters):
    value: float = Field(default=1, ge=0, le=1)


class CropParameters(EffectParameters):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)
    space: Literal["source", "canvas"] = "canvas"


class ReframeParameters(EffectParameters):
    fit: Literal["cover", "contain", "stretch"] = "cover"
    focus_x: float = Field(default=0.5, ge=0, le=1)
    focus_y: float = Field(default=0.5, ge=0, le=1)
    zoom: float = Field(default=1, ge=1, le=100)
    target_width: int | None = Field(default=None, gt=0)
    target_height: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def paired_target_dimensions(self) -> ReframeParameters:
        if (self.target_width is None) != (self.target_height is None):
            raise ValueError("reframe target width and height must be provided together")
        return self


class BlendModeParameters(EffectParameters):
    mode: Literal["normal", "multiply", "screen", "overlay", "darken", "lighten", "difference"] = (
        "normal"
    )
    opacity: float = Field(default=1, ge=0, le=1)


class MaskParameters(EffectParameters):
    shape: Literal["asset", "rectangle", "ellipse"] = "asset"
    path: str | None = Field(default=None, min_length=1)
    x: float = Field(default=0, ge=0, le=1)
    y: float = Field(default=0, ge=0, le=1)
    width: float = Field(default=1, gt=0, le=1)
    height: float = Field(default=1, gt=0, le=1)
    feather: float = Field(default=0, ge=0, le=0.5)
    invert: bool = False

    @model_validator(mode="after")
    def valid_source(self) -> MaskParameters:
        geometry_fields = {"x", "y", "width", "height", "feather"}
        if self.shape == "asset":
            if self.path is None:
                raise ValueError("asset mask requires a path")
            if self.model_fields_set & geometry_fields:
                raise ValueError("asset mask does not accept shape geometry")
        elif self.path is not None:
            raise ValueError("shape mask does not accept an asset path")
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("shape mask extends outside normalized canvas")
        return self


class TrackMatteParameters(EffectParameters):
    path: str | None = Field(default=None, min_length=1)
    item_id: str | None = Field(default=None, min_length=1)
    track_id: str | None = Field(default=None, min_length=1)
    channel: Literal["alpha", "luma"] = "alpha"
    invert: bool = False

    @model_validator(mode="after")
    def exactly_one_source(self) -> TrackMatteParameters:
        if sum(value is not None for value in (self.path, self.item_id, self.track_id)) != 1:
            raise ValueError("track matte requires exactly one path, item_id, or track_id")
        return self


class ChromaKeyParameters(EffectParameters):
    key_color: str = Field(default="0x00FF00", pattern=r"^0x[0-9A-Fa-f]{6}$")
    similarity: float = Field(default=0.1, ge=0, le=1)
    blend: float = Field(default=0, ge=0, le=1)


class LumaKeyParameters(EffectParameters):
    threshold: float = Field(default=0.5, ge=0, le=1)
    softness: float = Field(default=0, ge=0, le=1)
    invert: bool = False


class CornerRadiusParameters(EffectParameters):
    radius: float = Field(default=0, ge=0)


class BlurParameters(EffectParameters):
    sigma: float = Field(default=10, gt=0, le=1024)
    steps: int = Field(default=2, ge=1, le=6)
    region_shape: Literal["full", "rectangle", "ellipse"] = "full"
    region_policy: Literal["inside", "outside"] | None = None
    x: float = Field(default=0, ge=0, le=1)
    y: float = Field(default=0, ge=0, le=1)
    width: float = Field(default=1, gt=0, le=1)
    height: float = Field(default=1, gt=0, le=1)
    feather: float = Field(default=0, ge=0, le=0.5)

    @model_validator(mode="after")
    def valid_region(self) -> BlurParameters:
        region_fields = {"region_policy", "x", "y", "width", "height", "feather"}
        if self.region_shape == "full":
            if self.model_fields_set & region_fields:
                raise ValueError("full-frame blur does not accept region parameters")
        elif self.region_policy is None:
            raise ValueError("selective blur requires an inside or outside region policy")
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("blur region extends outside normalized canvas")
        return self


class ShadowParameters(EffectParameters):
    offset_x: float = 12
    offset_y: float = 12
    blur_sigma: float = Field(default=8, gt=0, le=1024)
    opacity: float = Field(default=0.5, ge=0, le=1)
    color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")


class GlowParameters(EffectParameters):
    blur_sigma: float = Field(default=8, gt=0, le=1024)
    intensity: float = Field(default=0.6, ge=0, le=2)
    color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")


class PerspectiveParameters(EffectParameters):
    top_left_x: float = Field(default=0, ge=0, le=1)
    top_left_y: float = Field(default=0, ge=0, le=1)
    top_right_x: float = Field(default=1, ge=0, le=1)
    top_right_y: float = Field(default=0, ge=0, le=1)
    bottom_left_x: float = Field(default=0, ge=0, le=1)
    bottom_left_y: float = Field(default=1, ge=0, le=1)
    bottom_right_x: float = Field(default=1, ge=0, le=1)
    bottom_right_y: float = Field(default=1, ge=0, le=1)
    interpolation: Literal["linear", "cubic"] = "cubic"


class DistortionParameters(EffectParameters):
    center_x: float = Field(default=0.5, ge=0, le=1)
    center_y: float = Field(default=0.5, ge=0, le=1)
    quadratic: float = Field(default=0, ge=-1, le=1)
    double_quadratic: float = Field(default=0, ge=-1, le=1)
    interpolation: Literal["nearest", "bilinear"] = "bilinear"


class FreezeParameters(EffectParameters):
    frame_time: RationalTime
    duration: RationalTime
    source_range: TimeRange | None = None
    source_reverse: bool = False

    @model_validator(mode="after")
    def valid_times(self) -> FreezeParameters:
        if self.frame_time.value < 0:
            raise ValueError("freeze frame time must be nonnegative")
        if self.duration.value <= 0:
            raise ValueError("freeze duration must be positive")
        if self.source_reverse and self.source_range is None:
            raise ValueError("freeze source_reverse requires a materialized source range")
        return self


class ColorInterpretationParameters(EffectParameters):
    input_space: ColorSpace


class ColorNormalizationParameters(EffectParameters):
    tone_map: Literal["none", "hable", "mobius", "reinhard", "clip"] = "none"
    peak_nits: float = Field(default=100, gt=0)


class GradeParameters(EffectParameters):
    exposure_stops: float = Field(default=0, ge=-10, le=10)
    temperature: float = Field(default=0, ge=-1, le=1)
    tint: float = Field(default=0, ge=-1, le=1)
    contrast: float = Field(default=1, ge=0, le=4)
    gamma: float = Field(default=1, ge=0.1, le=10)
    saturation: float = Field(default=1, ge=0, le=4)
    highlights: float = Field(default=0, ge=-1, le=1)
    shadows: float = Field(default=0, ge=-1, le=1)
    lut_path: str | None = None


class LutParameters(EffectParameters):
    path: str = Field(min_length=1)


class GainParameters(EffectParameters):
    db: float = 0


class PanParameters(EffectParameters):
    value: float = Field(default=0, ge=-1, le=1)


class FadeParameters(EffectParameters):
    type: Literal["in", "out"] = "in"
    start: RationalTime = Field(default_factory=RationalTime.zero)
    duration: RationalTime = Field(default_factory=lambda: RationalTime(value=3, timescale=100))

    @model_validator(mode="after")
    def valid_range(self) -> FadeParameters:
        if self.duration.value <= 0:
            raise ValueError("fade duration must be positive")
        if self.start.value < 0:
            raise ValueError("fade start must be nonnegative")
        return self


class EqParameters(EffectParameters):
    frequency: float = Field(default=1000, gt=0)
    q: float = Field(default=1, gt=0)
    gain_db: float = 0


class CompressionParameters(EffectParameters):
    threshold_db: float = -18
    ratio: float = Field(default=4, ge=1)
    attack_ms: float = Field(default=20, gt=0)
    release_ms: float = Field(default=250, gt=0)


class LimiterParameters(EffectParameters):
    linear_peak: float = Field(default=0.95, gt=0, le=1)


class GateParameters(EffectParameters):
    threshold_db: float = -45


class DeEsserParameters(EffectParameters):
    intensity: float = Field(default=0.5, ge=0, le=1)


class NoiseReductionParameters(EffectParameters):
    reduction_db: float = Field(default=12, ge=0, le=80)


class ChannelMapParameters(EffectParameters):
    layout: str = Field(default="stereo", min_length=1)


class SampleRateParameters(EffectParameters):
    sample_rate: int = Field(gt=0)


class SidechainParameters(EffectParameters):
    key_bus_id: str = Field(min_length=1)
    threshold_db: float = Field(default=-24, ge=-80, le=0)
    ratio: float = Field(default=6, ge=1, le=100)
    attack_ms: float = Field(default=20, gt=0)
    release_ms: float = Field(default=250, gt=0)
    makeup_db: float = Field(default=0, ge=0, le=24)
    mix: float = Field(default=1, ge=0, le=1)


class BackendOverrideParameters(EffectParameters):
    backend: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    payload: dict[str, JsonValue] = Field(default_factory=dict)


class EmptyTransitionParameters(EffectParameters):
    pass


class DirectionalTransitionParameters(EffectParameters):
    direction: Literal["left", "right", "up", "down"] = "left"


class DipToColorParameters(EffectParameters):
    color: Literal["black", "white"] = "black"


class ZoomTransitionParameters(EffectParameters):
    direction: Literal["in"] = "in"


class AudioCrossfadeParameters(EffectParameters):
    curve_from: Literal["tri", "qsin", "esin", "hsin", "log"] = "tri"
    curve_to: Literal["tri", "qsin", "esin", "hsin", "log"] = "tri"


VISUAL_PARAMETER_MODELS: dict[EffectKind, type[EffectParameters]] = {
    EffectKind.POSITION: PositionParameters,
    EffectKind.SCALE: ScaleParameters,
    EffectKind.ROTATION: RotationParameters,
    EffectKind.ANCHOR: AnchorParameters,
    EffectKind.OPACITY: OpacityParameters,
    EffectKind.CROP: CropParameters,
    EffectKind.REFRAME: ReframeParameters,
    EffectKind.BLEND_MODE: BlendModeParameters,
    EffectKind.MASK: MaskParameters,
    EffectKind.TRACK_MATTE: TrackMatteParameters,
    EffectKind.CHROMA_KEY: ChromaKeyParameters,
    EffectKind.LUMA_KEY: LumaKeyParameters,
    EffectKind.CORNER_RADIUS: CornerRadiusParameters,
    EffectKind.BACKGROUND_BLUR: BlurParameters,
    EffectKind.DROP_SHADOW: ShadowParameters,
    EffectKind.GLOW: GlowParameters,
    EffectKind.PERSPECTIVE: PerspectiveParameters,
    EffectKind.DISTORTION: DistortionParameters,
    EffectKind.FREEZE: FreezeParameters,
    EffectKind.COLOR_INTERPRETATION: ColorInterpretationParameters,
    EffectKind.COLOR_NORMALIZATION: ColorNormalizationParameters,
    EffectKind.COLOR_GRADE: GradeParameters,
    EffectKind.LUT: LutParameters,
}

AUDIO_PARAMETER_MODELS: dict[EffectKind, tuple[str, type[EffectParameters]]] = {
    EffectKind.GAIN: ("gain", GainParameters),
    EffectKind.PAN: ("pan", PanParameters),
    EffectKind.FADE: ("fade", FadeParameters),
    EffectKind.EQ: ("eq", EqParameters),
    EffectKind.COMPRESSION: ("compression", CompressionParameters),
    EffectKind.LIMITER: ("limiter", LimiterParameters),
    EffectKind.GATE: ("gate", GateParameters),
    EffectKind.DE_ESSER: ("de_esser", DeEsserParameters),
    EffectKind.NOISE_REDUCTION: ("noise_reduction", NoiseReductionParameters),
    EffectKind.CHANNEL_MAP: ("channel_map", ChannelMapParameters),
    EffectKind.SAMPLE_RATE_CONVERT: ("sample_rate_convert", SampleRateParameters),
}

TRANSITION_PARAMETER_MODELS: dict[TransitionKind, type[EffectParameters]] = {
    TransitionKind.CUT: EmptyTransitionParameters,
    TransitionKind.DISSOLVE: EmptyTransitionParameters,
    TransitionKind.DIP_TO_COLOR: DipToColorParameters,
    TransitionKind.WIPE: DirectionalTransitionParameters,
    TransitionKind.SLIDE: DirectionalTransitionParameters,
    TransitionKind.PUSH: DirectionalTransitionParameters,
    TransitionKind.ZOOM: ZoomTransitionParameters,
    TransitionKind.AUDIO_CROSSFADE: AudioCrossfadeParameters,
}


def validate_effect_parameters(effect: Effect) -> EffectParameters:
    if effect.kind is EffectKind.SIDECHAIN_DUCKING:
        model: type[EffectParameters] = SidechainParameters
    elif effect.kind is EffectKind.BACKEND_OVERRIDE:
        model = BackendOverrideParameters
    elif effect.kind in VISUAL_PARAMETER_MODELS:
        model = VISUAL_PARAMETER_MODELS[effect.kind]
    elif effect.kind in AUDIO_PARAMETER_MODELS:
        model = AUDIO_PARAMETER_MODELS[effect.kind][1]
    else:
        raise EngineError(
            ErrorCode.UNSUPPORTED_CAPABILITY,
            "effect kind has no canonical parameter contract",
            context={"effect_id": effect.id, "effect_kind": effect.kind.value},
        )
    try:
        return model.model_validate(effect.parameters)
    except ValidationError as exc:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "effect parameters are invalid",
            context={
                "effect_id": effect.id,
                "effect_kind": effect.kind.value,
                "errors": exc.errors(),
            },
        ) from exc


def parse_transition_parameters(transition: Transition) -> EffectParameters:
    model = TRANSITION_PARAMETER_MODELS[transition.kind]
    try:
        return model.model_validate(transition.parameters)
    except ValidationError as exc:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "transition parameters are invalid",
            context={
                "transition_id": transition.id,
                "transition_kind": transition.kind.value,
                "errors": exc.errors(),
            },
        ) from exc


def parse_visual_parameters(effect: Effect) -> EffectParameters:
    try:
        model = VISUAL_PARAMETER_MODELS[effect.kind]
    except KeyError as exc:
        raise EngineError(
            ErrorCode.UNSUPPORTED_CAPABILITY,
            "visual effect has no canonical renderer",
            context={"effect_id": effect.id, "effect_kind": effect.kind.value},
        ) from exc
    try:
        return model.model_validate(effect.parameters)
    except ValidationError as exc:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "visual effect parameters are invalid",
            context={
                "effect_id": effect.id,
                "effect_kind": effect.kind.value,
                "errors": exc.errors(),
            },
        ) from exc


def parse_audio_processor(
    effect: Effect, *, time_offset: RationalTime | None = None
) -> AudioProcessor:
    try:
        processor_kind, model = AUDIO_PARAMETER_MODELS[effect.kind]
    except KeyError as exc:
        raise EngineError(
            ErrorCode.UNSUPPORTED_CAPABILITY,
            "audio effect has no canonical renderer",
            context={"effect_id": effect.id, "effect_kind": effect.kind.value},
        ) from exc
    try:
        parsed = model.model_validate(effect.parameters)
    except ValidationError as exc:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "audio effect parameters are invalid",
            context={
                "effect_id": effect.id,
                "effect_kind": effect.kind.value,
                "errors": exc.errors(),
            },
        ) from exc
    automation: tuple[AudioAutomationPoint, ...] = ()
    if effect.keyframes:
        property_names = {
            EffectKind.GAIN: "db",
            EffectKind.PAN: "value",
        }
        expected_property = property_names.get(effect.kind)
        if expected_property is None:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "this audio effect does not support automation",
                context={"effect_id": effect.id, "effect_kind": effect.kind.value},
            )
        points: list[AudioAutomationPoint] = []
        for keyframe in sorted(effect.keyframes, key=lambda item: item.time):
            if keyframe.property_path != expected_property:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "audio keyframe targets the wrong property",
                    context={
                        "effect_id": effect.id,
                        "expected": expected_property,
                        "actual": keyframe.property_path,
                    },
                )
            if isinstance(keyframe.value, bool) or not isinstance(keyframe.value, (int, float)):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "audio automation values must be numeric",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            if effect.kind is EffectKind.PAN and not -1 <= float(keyframe.value) <= 1:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "pan automation values must be between -1 and 1",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            points.append(
                AudioAutomationPoint(
                    time=keyframe.time,
                    value=float(keyframe.value),
                    interpolation=keyframe.interpolation,
                )
            )
        automation = tuple(points)
    return AudioProcessor(
        kind=processor_kind,  # type: ignore[arg-type]
        parameters=parsed.model_dump(mode="json"),
        automation=automation,
        automation_offset=time_offset or RationalTime.zero(),
    )


def parse_sidechain_parameters(effect: Effect) -> SidechainParameters:
    if effect.kind is not EffectKind.SIDECHAIN_DUCKING:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "effect is not a side-chain ducking processor",
            context={"effect_id": effect.id},
        )
    if effect.keyframes:
        raise EngineError(
            ErrorCode.UNSUPPORTED_CAPABILITY,
            "side-chain parameter automation is not yet supported",
            context={"effect_id": effect.id},
        )
    try:
        return SidechainParameters.model_validate(effect.parameters)
    except ValidationError as exc:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "side-chain parameters are invalid",
            context={"effect_id": effect.id, "errors": exc.errors()},
        ) from exc
