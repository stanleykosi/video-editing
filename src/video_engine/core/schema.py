"""Strict, versioned canonical project and timeline schemas."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from fractions import Fraction
from itertools import pairwise
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.time import FrameRate, RationalRate, RationalTime, RoundingMode, TimeRange
from video_engine.errors import EngineError

CURRENT_SCHEMA_VERSION = "1.2.0"
JsonValue: TypeAlias = str | int | float | bool | None | list[Any] | dict[str, Any]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class TrackKind(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    CAPTION = "caption"
    GRAPHICS = "graphics"
    ADJUSTMENT = "adjustment"


class AudioRole(StrEnum):
    DIALOGUE = "dialogue"
    VOICE_OVER = "voice_over"
    SOURCE = "source"
    MUSIC = "music"
    AMBIENCE = "ambience"
    ROOM_TONE = "room_tone"
    FOLEY = "foley"
    SFX = "sfx"


class EffectKind(StrEnum):
    POSITION = "position"
    SCALE = "scale"
    ROTATION = "rotation"
    ANCHOR = "anchor"
    OPACITY = "opacity"
    CROP = "crop"
    REFRAME = "reframe"
    CORNER_RADIUS = "corner_radius"
    PERSPECTIVE = "perspective"
    BLEND_MODE = "blend_mode"
    MASK = "mask"
    TRACK_MATTE = "track_matte"
    CHROMA_KEY = "chroma_key"
    LUMA_KEY = "luma_key"
    BACKGROUND_BLUR = "background_blur"
    DROP_SHADOW = "drop_shadow"
    GLOW = "glow"
    DISTORTION = "distortion"
    FREEZE = "freeze"
    COLOR_INTERPRETATION = "color_interpretation"
    COLOR_NORMALIZATION = "color_normalization"
    COLOR_GRADE = "color_grade"
    LUT = "lut"
    GAIN = "gain"
    PAN = "pan"
    FADE = "fade"
    EQ = "eq"
    COMPRESSION = "compression"
    LIMITER = "limiter"
    GATE = "gate"
    DE_ESSER = "de_esser"
    NOISE_REDUCTION = "noise_reduction"
    SIDECHAIN_DUCKING = "sidechain_ducking"
    CHANNEL_MAP = "channel_map"
    SAMPLE_RATE_CONVERT = "sample_rate_convert"
    BACKEND_OVERRIDE = "backend_override"


class Interpolation(StrEnum):
    HOLD = "hold"
    LINEAR = "linear"
    BEZIER = "bezier"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"


class Keyframe(StrictModel):
    id: str = Field(min_length=1)
    property_path: str = Field(min_length=1)
    time: RationalTime
    value: JsonValue
    interpolation: Interpolation = Interpolation.LINEAR
    in_tangent: tuple[float, float] | None = None
    out_tangent: tuple[float, float] | None = None
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class Effect(StrictModel):
    id: str = Field(min_length=1)
    kind: EffectKind
    enabled: bool = True
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    keyframes: list[Keyframe] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_keyframes(self) -> Effect:
        ids = [keyframe.id for keyframe in self.keyframes]
        if len(ids) != len(set(ids)):
            raise ValueError("keyframe ids must be unique within an effect")
        from video_engine.render.effects import validate_effect_parameters

        try:
            validate_effect_parameters(self)
        except EngineError as exc:
            raise ValueError(exc.message) from exc
        return self


class AudioBus(StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    parent_bus_id: str | None = None
    channel_layout: str = Field(default="stereo", min_length=1)
    gain_db: float = 0.0
    pan: float = Field(default=0.0, ge=-1, le=1)
    enabled: bool = True
    effects: list[Effect] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_effect_ids(self) -> AudioBus:
        ids = [effect.id for effect in self.effects]
        if len(ids) != len(set(ids)):
            raise ValueError("effect ids must be unique within an audio bus")
        return self


class Marker(StrictModel):
    id: str = Field(min_length=1)
    time: RationalTime
    duration: RationalTime | None = None
    name: str = ""
    comment: str = ""
    color: str | None = None
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def nonnegative_duration(self) -> Marker:
        if self.duration is not None and self.duration.value < 0:
            raise ValueError("marker duration cannot be negative")
        return self


class TransitionKind(StrEnum):
    CUT = "cut"
    DISSOLVE = "dissolve"
    DIP_TO_COLOR = "dip_to_color"
    WIPE = "wipe"
    SLIDE = "slide"
    PUSH = "push"
    ZOOM = "zoom"
    AUDIO_CROSSFADE = "audio_crossfade"


class Transition(StrictModel):
    id: str = Field(min_length=1)
    kind: TransitionKind
    from_item_id: str
    to_item_id: str
    duration: RationalTime
    alignment: Literal["center", "start_at_cut", "end_at_cut"] = "center"
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def positive_duration(self) -> Transition:
        if self.duration.value <= 0:
            raise ValueError("transition duration must be positive")
        if self.from_item_id == self.to_item_id:
            raise ValueError("transition endpoints must be different items")
        from video_engine.render.effects import parse_transition_parameters

        try:
            parse_transition_parameters(self)
        except EngineError as exc:
            raise ValueError(exc.message) from exc
        return self


class LinkGroup(StrictModel):
    id: str = Field(min_length=1)
    item_ids: list[str] = Field(min_length=2)
    locked: bool = False
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_items(self) -> LinkGroup:
        if len(self.item_ids) != len(set(self.item_ids)):
            raise ValueError("link group item ids must be unique")
        return self


class BaseTimelineItem(StrictModel):
    id: str = Field(min_length=1)
    name: str = ""
    timeline_range: TimeRange
    enabled: bool = True
    locked: bool = False
    linked_group_id: str | None = None
    group_id: str | None = None
    effects: list[Effect] = Field(default_factory=list)
    markers: list[Marker] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_item(self) -> BaseTimelineItem:
        if self.timeline_range.duration.value <= 0:
            raise ValueError("timeline item duration must be positive")
        effect_ids = [effect.id for effect in self.effects]
        if len(effect_ids) != len(set(effect_ids)):
            raise ValueError("effect ids must be unique within an item")
        return self


class SpeedRampPoint(StrictModel):
    time: RationalTime
    rate: RationalRate
    interpolation: Literal["hold", "linear"] = "linear"

    @model_validator(mode="after")
    def nonnegative_time(self) -> SpeedRampPoint:
        if self.time.value < 0:
            raise ValueError("speed-ramp point time must be nonnegative")
        return self


class Retime(StrictModel):
    rate: RationalRate = Field(default_factory=lambda: RationalRate(numerator=1))
    reverse: bool = False
    preserve_audio_pitch: bool = True
    speed_ramp: tuple[SpeedRampPoint, ...] = ()
    source_curve: tuple[SpeedRampPoint, ...] = ()
    source_curve_offset: RationalTime = Field(default_factory=RationalTime.zero)

    @model_validator(mode="after")
    def valid_speed_ramp(self) -> Retime:
        if not self.speed_ramp:
            if self.source_curve or self.source_curve_offset != RationalTime.zero():
                raise ValueError("speed-ramp source context requires an active speed ramp")
            return self
        if self.rate.fraction != 1:
            raise ValueError("constant rate must be 1 when a speed ramp is present")
        if len(self.speed_ramp) < 2:
            raise ValueError("speed ramp requires at least two points")
        if self.speed_ramp[0].time != RationalTime.zero():
            raise ValueError("speed ramp must begin at item-local time zero")
        times = [point.time for point in self.speed_ramp]
        if any(left >= right for left, right in pairwise(times)):
            raise ValueError("speed-ramp point times must be strictly increasing")
        if self.source_curve:
            if len(self.source_curve) < 2:
                raise ValueError("speed-ramp source curve requires at least two points")
            if self.source_curve[0].time != RationalTime.zero():
                raise ValueError("speed-ramp source curve must begin at time zero")
            source_times = [point.time for point in self.source_curve]
            if any(left >= right for left, right in pairwise(source_times)):
                raise ValueError("speed-ramp source-curve times must be strictly increasing")
        return self

    def rate_at(self, time: RationalTime) -> Fraction:
        if not self.speed_ramp:
            return self.rate.fraction
        if self.source_curve:
            return self._rate_at_points(self.source_curve, self.source_curve_offset + time)
        return self._rate_at_points(self.speed_ramp, time)

    @staticmethod
    def _rate_at_points(points: tuple[SpeedRampPoint, ...], time: RationalTime) -> Fraction:
        value = time.fraction
        if value <= 0:
            return points[0].rate.fraction
        for left, right in pairwise(points):
            left_time = left.time.fraction
            right_time = right.time.fraction
            if value >= right_time:
                continue
            if left.interpolation == "hold":
                return left.rate.fraction
            progress = (value - left_time) / (right_time - left_time)
            return left.rate.fraction + (right.rate.fraction - left.rate.fraction) * progress
        return points[-1].rate.fraction

    def source_offset_at(self, time: RationalTime) -> RationalTime:
        if not self.speed_ramp:
            return RationalTime.from_fraction(time.fraction * self.rate.fraction)
        if self.source_curve:
            absolute_start = self._source_offset_at_points(
                self.source_curve, self.source_curve_offset
            )
            absolute_end = self._source_offset_at_points(
                self.source_curve, self.source_curve_offset + time
            )
            return absolute_end - absolute_start
        return self._source_offset_at_points(self.speed_ramp, time)

    @staticmethod
    def _source_offset_at_points(
        points: tuple[SpeedRampPoint, ...], time: RationalTime
    ) -> RationalTime:
        value = time.fraction
        first_rate = points[0].rate.fraction
        if value <= 0:
            return RationalTime.from_fraction(value * first_rate)
        area = Fraction(0)
        for left, right in pairwise(points):
            start = left.time.fraction
            end = right.time.fraction
            if value <= start:
                break
            width = min(value, end) - start
            if width > 0:
                if left.interpolation == "hold":
                    area += width * left.rate.fraction
                else:
                    end_rate = left.rate.fraction + (right.rate.fraction - left.rate.fraction) * (
                        width / (end - start)
                    )
                    area += width * (left.rate.fraction + end_rate) / 2
            if value <= end:
                return RationalTime.from_fraction(area)
        last = points[-1]
        if value > last.time.fraction:
            area += (value - last.time.fraction) * last.rate.fraction
        return RationalTime.from_fraction(area)

    def source_duration_for(self, timeline_range: TimeRange) -> RationalTime:
        return self.source_offset_at(timeline_range.end) - self.source_offset_at(
            timeline_range.start
        )

    def timeline_offset_at(
        self,
        source_offset: RationalTime,
        timeline_duration: RationalTime,
        *,
        timescale: int = 1_000_000,
    ) -> RationalTime:
        if source_offset.value < 0:
            raise ValueError("source offset must be nonnegative")
        source_duration = self.source_offset_at(timeline_duration)
        if source_offset > source_duration:
            raise ValueError("source offset exceeds the retimed timeline duration")
        if not self.speed_ramp:
            return source_offset / self.rate.fraction
        if timescale <= 0:
            raise ValueError("retime inverse timescale must be positive")

        upper = timeline_duration.rescaled_to(timescale, RoundingMode.CEIL).value
        low = 0
        high = upper
        while low < high:
            middle = (low + high) // 2
            candidate = RationalTime(value=middle, timescale=timescale)
            if self.source_offset_at(candidate) < source_offset:
                low = middle + 1
            else:
                high = middle
        candidates = {low}
        if low > 0:
            candidates.add(low - 1)
        selected = min(
            candidates,
            key=lambda tick: (
                abs(
                    (
                        self.source_offset_at(RationalTime(value=tick, timescale=timescale))
                        - source_offset
                    ).fraction
                ),
                tick,
            ),
        )
        return RationalTime(value=selected, timescale=timescale)

    def window(self, start: RationalTime, duration: RationalTime) -> Retime:
        if not self.speed_ramp:
            return self
        source_curve = self.source_curve or self.speed_ramp
        source_curve_offset = self.source_curve_offset if self.source_curve else RationalTime.zero()
        absolute_start = source_curve_offset + start
        absolute_end = absolute_start + duration
        points = [
            SpeedRampPoint(
                time=RationalTime.zero(),
                rate=RationalRate(
                    numerator=self._rate_at_points(source_curve, absolute_start).numerator,
                    denominator=self._rate_at_points(source_curve, absolute_start).denominator,
                ),
                interpolation=self._interpolation_at(source_curve, absolute_start),
            )
        ]
        points.extend(
            point.model_copy(update={"time": point.time - absolute_start})
            for point in source_curve
            if absolute_start < point.time < absolute_end
        )
        points.append(
            SpeedRampPoint(
                time=duration,
                rate=RationalRate(
                    numerator=self._rate_at_points(source_curve, absolute_end).numerator,
                    denominator=self._rate_at_points(source_curve, absolute_end).denominator,
                ),
                interpolation="hold",
            )
        )
        return self.model_copy(
            update={
                "speed_ramp": tuple(points),
                "source_curve": source_curve,
                "source_curve_offset": absolute_start,
            }
        )

    @staticmethod
    def _interpolation_at(
        points: tuple[SpeedRampPoint, ...], time: RationalTime
    ) -> Literal["hold", "linear"]:
        for left, right in pairwise(points):
            if time < right.time:
                return left.interpolation
        return points[-1].interpolation


def _validate_retime_duration(
    timeline_range: TimeRange, source_range: TimeRange, retime: Retime
) -> None:
    if retime.speed_ramp and retime.speed_ramp[-1].time != timeline_range.duration:
        raise ValueError("speed ramp must end at the item timeline duration")
    expected = retime.source_offset_at(timeline_range.duration)
    if source_range.duration != expected:
        raise ValueError("source duration must equal timeline duration multiplied by retime rate")


class Clip(BaseTimelineItem):
    item_type: Literal["clip"] = "clip"
    media_reference_id: str = Field(min_length=1)
    source_range: TimeRange
    source_audio_enabled: bool = True
    video_stream_index: int = Field(default=0, ge=0)
    source_audio_stream_index: int = Field(default=0, ge=0)
    retime: Retime = Field(default_factory=Retime)

    @model_validator(mode="after")
    def valid_retime_duration(self) -> Clip:
        freezes = [
            effect for effect in self.effects if effect.enabled and effect.kind is EffectKind.FREEZE
        ]
        if len(freezes) > 1:
            raise ValueError("a clip can have only one enabled freeze effect")
        if freezes:
            freeze_duration = RationalTime.model_validate(freezes[0].parameters["duration"])
            if freeze_duration != self.timeline_range.duration:
                raise ValueError("freeze duration must equal the owning clip duration")
        _validate_retime_duration(self.timeline_range, self.source_range, self.retime)
        return self


class Gap(BaseTimelineItem):
    item_type: Literal["gap"] = "gap"


class NestedSequenceClip(BaseTimelineItem):
    item_type: Literal["nested_sequence"] = "nested_sequence"
    sequence_id: str = Field(min_length=1)
    source_range: TimeRange
    sequence_version: int | None = Field(default=None, ge=1)
    source_audio_enabled: bool = True
    audio_bus_id: str | None = None
    audio_gain_db: float = 0
    audio_pan: float = Field(default=0, ge=-1, le=1)
    retime: Retime = Field(default_factory=Retime)

    @model_validator(mode="after")
    def valid_retime_duration(self) -> NestedSequenceClip:
        _validate_retime_duration(self.timeline_range, self.source_range, self.retime)
        return self


class GeneratorAssetReference(StrictModel):
    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")
    media_reference_id: str = Field(min_length=1)


class GeneratorClip(BaseTimelineItem):
    item_type: Literal["generator"] = "generator"
    generator_id: str = Field(min_length=1)
    generator_version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    properties: dict[str, JsonValue] = Field(default_factory=dict)
    assets: list[GeneratorAssetReference] = Field(default_factory=list)
    transparent: bool = True

    @model_validator(mode="after")
    def unique_asset_ids(self) -> GeneratorClip:
        ids = [asset.id for asset in self.assets]
        if len(ids) != len(set(ids)):
            raise ValueError("generator asset ids must be unique")
        return self


class StillImageClip(BaseTimelineItem):
    item_type: Literal["still_image"] = "still_image"
    media_reference_id: str = Field(min_length=1)


class AudioClip(BaseTimelineItem):
    item_type: Literal["audio_clip"] = "audio_clip"
    media_reference_id: str = Field(min_length=1)
    source_range: TimeRange
    role: AudioRole = AudioRole.SOURCE
    bus_id: str | None = None
    replaces_embedded_audio_item_id: str | None = None
    channel_map: list[int] | None = None
    stream_index: int = Field(default=0, ge=0)
    retime: Retime = Field(default_factory=Retime)

    @model_validator(mode="after")
    def valid_channel_map(self) -> AudioClip:
        if self.channel_map is not None and (
            not self.channel_map or any(channel < 0 for channel in self.channel_map)
        ):
            raise ValueError("channel_map must contain nonnegative channel indices")
        _validate_retime_duration(self.timeline_range, self.source_range, self.retime)
        return self


class CaptionWord(StrictModel):
    text: str
    range: TimeRange
    confidence: float | None = Field(default=None, ge=0, le=1)
    highlight: bool = False
    style_id: str | None = None
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class CaptionStyleOverride(StrictModel):
    font_size_px: int | None = Field(default=None, gt=0)
    bold: bool | None = None
    italic: bool | None = None
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    outline_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class CaptionCue(BaseTimelineItem):
    item_type: Literal["caption_cue"] = "caption_cue"
    text: str
    words: list[CaptionWord] = Field(default_factory=list)
    speaker: str | None = None
    language: str = "und"
    style_id: str | None = None
    position: Literal["top", "center", "bottom", "custom"] = "bottom"
    position_x: float | None = Field(default=None, ge=0, le=1)
    position_y: float | None = Field(default=None, ge=0, le=1)
    style_overrides: CaptionStyleOverride = Field(default_factory=CaptionStyleOverride)
    suppressed: bool = False

    @model_validator(mode="after")
    def words_fit_cue(self) -> CaptionCue:
        if self.position == "custom" and (self.position_x is None or self.position_y is None):
            raise ValueError("custom caption position requires position_x and position_y")
        previous_end: RationalTime | None = None
        for word in self.words:
            if not word.text.strip():
                raise ValueError("caption word text must not be blank")
            if word.range.duration.value <= 0:
                raise ValueError("caption word duration must be positive")
            if (
                word.range.start < self.timeline_range.start
                or word.range.end > self.timeline_range.end
            ):
                raise ValueError("caption word timing must fall inside the cue range")
            if previous_end is not None and word.range.start < previous_end:
                raise ValueError("caption word timings must be ordered and non-overlapping")
            previous_end = word.range.end
        return self


class AdjustmentClip(BaseTimelineItem):
    item_type: Literal["adjustment"] = "adjustment"


VisualItem = Annotated[
    Clip | Gap | NestedSequenceClip | GeneratorClip | StillImageClip,
    Field(discriminator="item_type"),
]
AudioItem = Annotated[AudioClip | Gap, Field(discriminator="item_type")]
CaptionItem = Annotated[CaptionCue | Gap, Field(discriminator="item_type")]
GraphicsItem = Annotated[
    Clip | Gap | GeneratorClip | StillImageClip, Field(discriminator="item_type")
]
AdjustmentItem = Annotated[AdjustmentClip | Gap, Field(discriminator="item_type")]
AnyTimelineItem: TypeAlias = (
    Clip
    | Gap
    | NestedSequenceClip
    | GeneratorClip
    | StillImageClip
    | AudioClip
    | CaptionCue
    | AdjustmentClip
)
TimelineItem = Annotated[
    Clip
    | Gap
    | NestedSequenceClip
    | GeneratorClip
    | StillImageClip
    | AudioClip
    | CaptionCue
    | AdjustmentClip,
    Field(discriminator="item_type"),
]


class VideoTrack(StrictModel):
    track_type: Literal[TrackKind.VIDEO] = TrackKind.VIDEO
    id: str = Field(min_length=1)
    name: str = "Video"
    enabled: bool = True
    locked: bool = False
    items: list[VisualItem] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class CaptionCollisionRegion(StrictModel):
    id: str = Field(min_length=1)
    timeline_range: TimeRange
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)
    kind: Literal["subject", "face", "graphic", "proof", "ui", "custom"] = "custom"
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fits_frame(self) -> CaptionCollisionRegion:
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("caption collision region extends outside the frame")
        return self


class AudioTrack(StrictModel):
    track_type: Literal[TrackKind.AUDIO] = TrackKind.AUDIO
    id: str = Field(min_length=1)
    name: str = "Audio"
    role: AudioRole = AudioRole.SOURCE
    bus_id: str = "master"
    enabled: bool = True
    locked: bool = False
    items: list[AudioItem] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_effect_ids(self) -> AudioTrack:
        ids = [effect.id for effect in self.effects]
        if len(ids) != len(set(ids)):
            raise ValueError("effect ids must be unique within an audio track")
        return self


class CaptionTrack(StrictModel):
    track_type: Literal[TrackKind.CAPTION] = TrackKind.CAPTION
    id: str = Field(min_length=1)
    name: str = "Captions"
    language: str = "und"
    default_style_id: str = "default"
    collision_regions: list[CaptionCollisionRegion] = Field(default_factory=list)
    enabled: bool = True
    locked: bool = False
    items: list[CaptionItem] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_caption_owned_ids(self) -> CaptionTrack:
        item_ids = [item.id for item in self.items]
        region_ids = [region.id for region in self.collision_regions]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("caption item ids must be unique within a track")
        if len(region_ids) != len(set(region_ids)):
            raise ValueError("caption collision region ids must be unique within a track")
        return self


class CaptionStyle(StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    font_family: str = Field(default="DejaVu Sans", min_length=1)
    fallback_families: list[str] = Field(
        default_factory=lambda: ["Liberation Sans", "FreeSans", "Sans"]
    )
    font_size_ratio: float = Field(default=0.05, gt=0, le=0.25)
    min_font_size_px: int = Field(default=16, gt=0)
    max_font_size_px: int = Field(default=120, gt=0)
    bold: bool = True
    italic: bool = False
    primary_color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    highlight_color: str = Field(default="#F4C95D", pattern=r"^#[0-9A-Fa-f]{6}$")
    outline_color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")
    background_color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")
    background_opacity: float = Field(default=0, ge=0, le=1)
    outline_ratio: float = Field(default=0.003, ge=0, le=0.03)
    shadow_ratio: float = Field(default=0.001, ge=0, le=0.03)
    margin_x_ratio: float = Field(default=0.06, ge=0, le=0.4)
    margin_y_ratio: float = Field(default=0.08, ge=0, le=0.4)
    line_spacing: float = Field(default=1.0, ge=0.5, le=3)
    max_lines: int = Field(default=2, ge=1, le=5)
    max_chars_per_line: int = Field(default=42, ge=4, le=200)
    max_reading_speed_cps: float = Field(default=20, gt=0, le=100)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def font_size_bounds(self) -> CaptionStyle:
        if self.min_font_size_px > self.max_font_size_px:
            raise ValueError("caption style minimum font size exceeds maximum")
        return self


class GraphicsTrack(StrictModel):
    track_type: Literal[TrackKind.GRAPHICS] = TrackKind.GRAPHICS
    id: str = Field(min_length=1)
    name: str = "Graphics"
    enabled: bool = True
    locked: bool = False
    items: list[GraphicsItem] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class AdjustmentTrack(StrictModel):
    track_type: Literal[TrackKind.ADJUSTMENT] = TrackKind.ADJUSTMENT
    id: str = Field(min_length=1)
    name: str = "Adjustment"
    enabled: bool = True
    locked: bool = False
    items: list[AdjustmentItem] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


Track = Annotated[
    VideoTrack | AudioTrack | CaptionTrack | GraphicsTrack | AdjustmentTrack,
    Field(discriminator="track_type"),
]


class Timeline(StrictModel):
    tracks: list[Track] = Field(default_factory=list)
    markers: list[Marker] = Field(default_factory=list)
    link_groups: list[LinkGroup] = Field(default_factory=list)
    audio_buses: list[AudioBus] = Field(
        default_factory=lambda: [AudioBus(id="master", name="Master")]
    )
    master_bus_id: str = "master"
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_ids(self) -> Timeline:
        track_ids = [track.id for track in self.tracks]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("timeline track ids must be unique")
        item_ids = [item.id for track in self.tracks for item in track.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("timeline item ids must be unique")
        item_id_set = set(item_ids)
        for track in self.tracks:
            for item in track.items:
                if (
                    isinstance(item, AudioClip)
                    and item.replaces_embedded_audio_item_id is not None
                    and item.replaces_embedded_audio_item_id not in item_id_set
                ):
                    raise ValueError(
                        f"audio clip {item.id!r} replaces a missing embedded-audio item"
                    )
        marker_ids = [marker.id for marker in self.markers]
        if len(marker_ids) != len(set(marker_ids)):
            raise ValueError("timeline marker ids must be unique")
        bus_ids = [bus.id for bus in self.audio_buses]
        if len(bus_ids) != len(set(bus_ids)):
            raise ValueError("audio bus ids must be unique")
        buses = {bus.id: bus for bus in self.audio_buses}
        if self.master_bus_id not in buses:
            raise ValueError("master_bus_id does not reference an audio bus")
        if buses[self.master_bus_id].parent_bus_id is not None:
            raise ValueError("master audio bus cannot have a parent")
        for bus in self.audio_buses:
            if bus.parent_bus_id is not None and bus.parent_bus_id not in buses:
                raise ValueError(f"audio bus {bus.id!r} references a missing parent")
        for track in self.tracks:
            if isinstance(track, AudioTrack):
                if track.bus_id not in buses:
                    raise ValueError(f"audio track {track.id!r} references a missing bus")
                for item in track.items:
                    if (
                        isinstance(item, AudioClip)
                        and item.bus_id is not None
                        and item.bus_id not in buses
                    ):
                        raise ValueError(f"audio clip {item.id!r} references a missing bus")
            if isinstance(track, (VideoTrack, GraphicsTrack)):
                for item in track.items:
                    if (
                        isinstance(item, NestedSequenceClip)
                        and item.audio_bus_id is not None
                        and item.audio_bus_id not in buses
                    ):
                        raise ValueError(
                            f"nested sequence {item.id!r} references a missing audio bus"
                        )
        for bus_id in buses:
            visited: set[str] = set()
            current: str | None = bus_id
            while current is not None:
                if current in visited:
                    raise ValueError("audio bus parent graph contains a cycle")
                visited.add(current)
                current = buses[current].parent_bus_id
            if self.master_bus_id not in visited:
                raise ValueError(f"audio bus {bus_id!r} does not route to the master audio bus")
        return self

    @property
    def duration(self) -> RationalTime:
        ends = [item.timeline_range.end for track in self.tracks for item in track.items]
        return max(ends, default=RationalTime.zero())


class ColorSpace(StrEnum):
    REC709 = "rec709"
    REC2020 = "rec2020"
    HLG = "hlg"
    PQ = "pq"
    LINEAR = "linear"


class SequenceSettingsOverride(StrictModel):
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    frame_rate: FrameRate | None = None
    audio_sample_rate: int | None = Field(default=None, gt=0)
    working_color_space: ColorSpace | None = None
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class Sequence(StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    revision: int = Field(default=1, ge=1)
    timeline: Timeline = Field(default_factory=Timeline)
    settings_override: SequenceSettingsOverride = Field(default_factory=SequenceSettingsOverride)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class SequenceSnapshot(BaseModel):
    """Immutable historical sequence revision used by pinned nested clips."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    name: str = Field(min_length=1)
    timeline: Timeline
    settings_override: SequenceSettingsOverride = Field(default_factory=SequenceSettingsOverride)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def valid_content_digest(self) -> SequenceSnapshot:
        digest = self.calculate_digest()
        if self.content_sha256 is not None and self.content_sha256 != digest:
            raise ValueError("sequence snapshot content digest does not match its payload")
        object.__setattr__(self, "content_sha256", digest)
        return self

    def calculate_digest(self) -> str:
        payload = {
            "sequence_id": self.sequence_id,
            "revision": self.revision,
            "name": self.name,
            "timeline": self.timeline.model_dump(mode="json"),
            "settings_override": self.settings_override.model_dump(mode="json"),
            "extensions": self.extensions,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @classmethod
    def from_sequence(cls, sequence: Sequence) -> SequenceSnapshot:
        return cls(
            sequence_id=sequence.id,
            revision=sequence.revision,
            name=sequence.name,
            timeline=sequence.timeline.model_copy(deep=True),
            settings_override=sequence.settings_override.model_copy(deep=True),
            extensions=sequence.extensions.copy(),
        )

    def to_sequence(self) -> Sequence:
        return Sequence(
            id=self.sequence_id,
            name=self.name,
            revision=self.revision,
            timeline=self.timeline.model_copy(deep=True),
            settings_override=self.settings_override.model_copy(deep=True),
            extensions=self.extensions.copy(),
        )


class ProjectSettings(StrictModel):
    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    frame_rate: FrameRate = Field(default_factory=lambda: FrameRate(numerator=24))
    audio_sample_rate: int = Field(default=48_000, gt=0)
    audio_bit_depth: Literal[16, 24, 32] = 24
    audio_boundary_fade: RationalTime = Field(
        default_factory=lambda: RationalTime(value=3, timescale=1000)
    )
    working_color_space: ColorSpace = ColorSpace.REC709
    pixel_aspect_ratio: RationalTime = Field(
        default_factory=lambda: RationalTime(value=1, timescale=1)
    )
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_audio_boundary_fade(self) -> ProjectSettings:
        if self.audio_boundary_fade.value < 0:
            raise ValueError("audio_boundary_fade cannot be negative")
        if self.audio_boundary_fade > RationalTime(value=1, timescale=10):
            raise ValueError("audio_boundary_fade cannot exceed 100 ms")
        return self


class StreamSummary(StrictModel):
    index: int = Field(ge=0)
    codec_type: Literal["video", "audio", "subtitle", "data", "attachment"]
    codec_name: str | None = None
    time_base: RationalTime | None = None
    frame_rate: FrameRate | None = None
    sample_rate: int | None = Field(default=None, gt=0)
    channels: int | None = Field(default=None, gt=0)
    channel_layout: str | None = None
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    pixel_format: str | None = None
    color_primaries: str | None = None
    color_transfer: str | None = None
    color_space: str | None = None
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class MediaReference(StrictModel):
    id: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    available_range: TimeRange | None = None
    streams: list[StreamSummary] = Field(default_factory=list)
    rotation_degrees: int = 0
    variable_frame_rate: bool | None = None
    hdr: bool | None = None
    offline: bool = False
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class LoudnessProfile(StrictModel):
    integrated_lufs: float
    true_peak_dbtp: float
    loudness_range_lu: float = Field(gt=0)


class DeliveryProfile(StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_rate: FrameRate
    video_codec: str = "libx264"
    pixel_format: str = "yuv420p"
    video_bitrate: str | None = None
    crf: int | None = Field(default=18, ge=0, le=63)
    preset: str = "medium"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    audio_sample_rate: int = Field(default=48_000, gt=0)
    audio_channels: int = Field(default=2, ge=1, le=16)
    audio_channel_layout: str = Field(default="stereo", min_length=1)
    fit: Literal["cover", "contain", "stretch"] = "cover"
    output_color_space: ColorSpace = ColorSpace.REC709
    loudness: LoudnessProfile | None = None
    fast_start: bool = True
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def channel_count_matches_layout(self) -> DeliveryProfile:
        known_layouts = {
            "mono": 1,
            "stereo": 2,
            "2.1": 3,
            "3.0": 3,
            "4.0": 4,
            "5.1": 6,
            "5.1(side)": 6,
            "7.1": 8,
        }
        expected = known_layouts.get(self.audio_channel_layout)
        if expected is not None and expected != self.audio_channels:
            raise ValueError("audio_channels does not match audio_channel_layout")
        if self.output_color_space in {ColorSpace.HLG, ColorSpace.PQ} and "10" not in (
            self.pixel_format
        ):
            raise ValueError("HLG and PQ delivery profiles require a 10-bit pixel format")
        return self


class Project(StrictModel):
    schema_version: Literal["1.2.0"] = "1.2.0"
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    revision: int = Field(default=1, ge=1)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    media: list[MediaReference] = Field(default_factory=list)
    caption_styles: list[CaptionStyle] = Field(
        default_factory=lambda: [CaptionStyle(id="default", name="Default")]
    )
    sequences: list[Sequence] = Field(min_length=1)
    sequence_versions: list[SequenceSnapshot] = Field(default_factory=list)
    active_sequence_id: str
    delivery_profiles: list[DeliveryProfile] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def references_are_valid(self) -> Project:
        media_ids = [media.id for media in self.media]
        sequence_ids = [sequence.id for sequence in self.sequences]
        profile_ids = [profile.id for profile in self.delivery_profiles]
        caption_style_ids = [style.id for style in self.caption_styles]
        for label, values in {
            "media": media_ids,
            "sequence": sequence_ids,
            "delivery profile": profile_ids,
            "caption style": caption_style_ids,
        }.items():
            if len(values) != len(set(values)):
                raise ValueError(f"{label} ids must be unique")
        if self.active_sequence_id not in set(sequence_ids):
            raise ValueError("active_sequence_id does not reference a sequence")
        snapshot_keys = [
            (snapshot.sequence_id, snapshot.revision) for snapshot in self.sequence_versions
        ]
        if len(snapshot_keys) != len(set(snapshot_keys)):
            raise ValueError("historical sequence revisions must be unique")
        current_revisions = {sequence.id: sequence.revision for sequence in self.sequences}
        for snapshot in self.sequence_versions:
            current_revision = current_revisions.get(snapshot.sequence_id)
            if current_revision is None:
                raise ValueError("historical revision references a missing sequence")
            if snapshot.revision >= current_revision:
                raise ValueError("historical revision must precede the current sequence revision")
        media_set = set(media_ids)
        sequence_set = set(sequence_ids)
        caption_style_set = set(caption_style_ids)
        for sequence in self.sequences:
            for track in sequence.timeline.tracks:
                if (
                    isinstance(track, CaptionTrack)
                    and track.default_style_id not in caption_style_set
                ):
                    raise ValueError(f"caption track {track.id!r} references missing default style")
                for item in track.items:
                    if (
                        isinstance(item, (Clip, StillImageClip, AudioClip))
                        and item.media_reference_id not in media_set
                    ):
                        raise ValueError(
                            f"item {item.id!r} references missing media {item.media_reference_id!r}"
                        )
                    if isinstance(item, GeneratorClip):
                        missing_asset_media = {
                            asset.media_reference_id for asset in item.assets
                        } - media_set
                        if missing_asset_media:
                            raise ValueError(
                                f"generator item {item.id!r} references missing media "
                                f"{sorted(missing_asset_media)!r}"
                            )
                    if (
                        isinstance(item, NestedSequenceClip)
                        and item.sequence_id not in sequence_set
                    ):
                        raise ValueError(
                            f"item {item.id!r} references missing sequence {item.sequence_id!r}"
                        )
                    if (
                        isinstance(item, NestedSequenceClip)
                        and item.sequence_version is not None
                        and item.sequence_id in current_revisions
                    ):
                        available_versions = {
                            current_revisions[item.sequence_id],
                            *(
                                snapshot.revision
                                for snapshot in self.sequence_versions
                                if snapshot.sequence_id == item.sequence_id
                            ),
                        }
                        if item.sequence_version not in available_versions:
                            raise ValueError(
                                f"item {item.id!r} references unavailable sequence revision "
                                f"{item.sequence_version}"
                            )
                    if isinstance(item, CaptionCue):
                        referenced_styles = {
                            style_id
                            for style_id in [
                                item.style_id,
                                *(word.style_id for word in item.words),
                            ]
                            if style_id is not None
                        }
                        missing_styles = referenced_styles - caption_style_set
                        if missing_styles:
                            raise ValueError(
                                f"caption cue {item.id!r} references missing styles "
                                f"{sorted(missing_styles)!r}"
                            )
        return self

    def sequence(self, sequence_id: str | None = None) -> Sequence:
        target = sequence_id or self.active_sequence_id
        return next(sequence for sequence in self.sequences if sequence.id == target)

    def resolve_sequence(self, sequence_id: str, revision: int | None = None) -> Sequence:
        current = self.sequence(sequence_id)
        if revision is None or revision == current.revision:
            return current
        snapshot = next(
            snapshot
            for snapshot in self.sequence_versions
            if snapshot.sequence_id == sequence_id and snapshot.revision == revision
        )
        return snapshot.to_sequence()
