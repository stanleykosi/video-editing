"""Backend-neutral tracking and reframing contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import Interpolation, JsonValue
from video_engine.core.time import FrameRate, RationalTime, TimeRange
from video_engine.operations.models import TimelinePatch


class VisualModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NormalizedPoint(VisualModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class NormalizedBox(VisualModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def fits_frame(self) -> NormalizedBox:
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("normalized box extends outside the frame")
        return self

    @property
    def center(self) -> NormalizedPoint:
        return NormalizedPoint(x=self.x + self.width / 2, y=self.y + self.height / 2)


class TrackingObservation(VisualModel):
    time: RationalTime
    subject_id: str = Field(min_length=1)
    confidence: float = Field(default=1, ge=0, le=1)
    box: NormalizedBox | None = None
    focus: NormalizedPoint | None = None
    manual: bool = False
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def has_geometry(self) -> TrackingObservation:
        if self.box is None and self.focus is None:
            raise ValueError("tracking observation requires a box or focus point")
        return self

    @property
    def center(self) -> NormalizedPoint:
        if self.focus is not None:
            return self.focus
        assert self.box is not None
        return self.box.center


class TrackingRequest(VisualModel):
    id: str = Field(min_length=1)
    media_reference_id: str = Field(min_length=1)
    source_range: TimeRange
    subject_ids: tuple[str, ...] = ()
    sample_interval: RationalTime
    minimum_confidence: float = Field(default=0.4, ge=0, le=1)
    manual_observations: tuple[TrackingObservation, ...] = ()
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def positive_interval(self) -> TrackingRequest:
        if self.source_range.duration.value <= 0:
            raise ValueError("tracking source range must be positive")
        if self.sample_interval.value <= 0:
            raise ValueError("tracking sample interval must be positive")
        return self


class TrackingResult(VisualModel):
    id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    media_reference_id: str = Field(min_length=1)
    backend: str = Field(min_length=1)
    backend_version: str = Field(min_length=1)
    source_range: TimeRange
    observations: tuple[TrackingObservation, ...]
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def ordered_unique_observations(self) -> TrackingResult:
        identities: set[tuple[str, RationalTime]] = set()
        previous: RationalTime | None = None
        for observation in self.observations:
            if not self.source_range.contains(observation.time, include_end=True):
                raise ValueError("tracking observation lies outside the source range")
            identity = (observation.subject_id, observation.time)
            if identity in identities:
                raise ValueError("tracking result contains duplicate subject times")
            identities.add(identity)
            if previous is not None and observation.time < previous:
                raise ValueError("tracking observations must be ordered by time")
            previous = observation.time
        return self


class ReframeMode(StrEnum):
    COVER = "cover"
    CONTAIN = "contain"
    STRETCH = "stretch"


class MultiSubjectFallback(StrEnum):
    CENTER = "center"
    CONTAIN = "contain"
    SPLIT_SCREEN = "split_screen"


class ReframeSettings(VisualModel):
    mode: ReframeMode = ReframeMode.COVER
    subject_margin: float = Field(default=0.12, ge=0, le=1)
    smoothing: float = Field(default=0.7, ge=0, lt=1)
    minimum_confidence: float = Field(default=0.4, ge=0, le=1)
    maximum_source_gap: RationalTime | None = None
    missing_policy: Literal["error", "hold", "interpolate"] = "error"
    multi_subject_fallback: MultiSubjectFallback = MultiSubjectFallback.CONTAIN
    multi_subject_max_span: float = Field(default=0.75, gt=0, le=1)


class CropKeyframe(VisualModel):
    time: RationalTime
    crop: NormalizedBox
    confidence: float = Field(ge=0, le=1)
    subject_ids: tuple[str, ...] = ()
    manual: bool = False


class SplitScreenPanel(VisualModel):
    time: RationalTime
    subject_id: str
    crop: NormalizedBox
    confidence: float = Field(ge=0, le=1)


class ReframeDecision(VisualModel):
    time: RationalTime
    mode: Literal["tracked", "center", "contain", "split_screen"]
    reason: str = Field(min_length=1)
    subject_ids: tuple[str, ...] = ()


class ReframePlan(VisualModel):
    id: str = Field(min_length=1)
    tracking_result_id: str = Field(min_length=1)
    source_width: int = Field(gt=0)
    source_height: int = Field(gt=0)
    output_width: int = Field(gt=0)
    output_height: int = Field(gt=0)
    mode: ReframeMode
    keyframes: tuple[CropKeyframe, ...]
    split_screen_panels: tuple[SplitScreenPanel, ...] = ()
    decisions: tuple[ReframeDecision, ...] = ()
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def ordered_keyframes(self) -> ReframePlan:
        if not self.keyframes:
            raise ValueError("reframe plan requires at least one crop keyframe")
        if any(
            right.time <= left.time
            for left, right in zip(self.keyframes, self.keyframes[1:], strict=False)
        ):
            raise ValueError("reframe keyframes must have strictly increasing times")
        return self


class TrackingGeometry(VisualModel):
    source_width: int = Field(gt=0)
    source_height: int = Field(gt=0)
    canvas_width: int = Field(gt=0)
    canvas_height: int = Field(gt=0)
    fit: ReframeMode = ReframeMode.COVER
    focus_x: float = Field(default=0.5, ge=0, le=1)
    focus_y: float = Field(default=0.5, ge=0, le=1)
    zoom: float = Field(default=1, ge=1, le=100)

    @model_validator(mode="after")
    def executable_geometry(self) -> TrackingGeometry:
        if self.fit is not ReframeMode.COVER and self.zoom != 1:
            raise ValueError("tracking zoom is supported only with cover geometry")
        if self.fit is ReframeMode.CONTAIN and (self.focus_x != 0.5 or self.focus_y != 0.5):
            raise ValueError("contain geometry is centered and requires focus_x=focus_y=0.5")
        return self


class TrackingBinding(VisualModel):
    id: str = Field(min_length=1)
    tracking_result_id: str = Field(min_length=1)
    source_item_id: str = Field(min_length=1)
    target_item_id: str | None = Field(default=None, min_length=1)
    target_track_id: str | None = Field(default=None, min_length=1)
    driver: Literal[
        "crop",
        "position",
        "mask",
        "blur",
        "graphic_attachment",
        "caption_exclusion",
    ]
    geometry: TrackingGeometry
    timeline_frame_rate: FrameRate
    subject_id: str | None = None
    minimum_confidence: float = Field(default=0.4, ge=0, le=1)
    maximum_source_gap: RationalTime | None = None
    missing_policy: Literal["error", "hold", "interpolate"] = "error"
    padding_ratio: float = Field(default=0, ge=0, le=1)
    interpolation: Interpolation = Interpolation.EASE_IN_OUT
    blur_sigma: float = Field(default=18, gt=0, le=1024)
    blur_steps: int = Field(default=3, ge=1, le=6)
    blur_region: Literal["inside", "outside"] | None = None
    blur_shape: Literal["rectangle", "ellipse"] = "rectangle"
    mask_shape: Literal["rectangle", "ellipse"] = "rectangle"
    mask_region: Literal["inside", "outside"] = "inside"
    feather: float = Field(default=0, ge=0, le=0.5)
    position_offset_x: float = 0
    position_offset_y: float = 0
    caption_region_kind: Literal["subject", "face", "graphic", "proof", "ui", "custom"] = "subject"
    inverse_timescale: int = Field(default=1_000_000, ge=1_000, le=1_000_000_000)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_target(self) -> TrackingBinding:
        if self.driver == "caption_exclusion":
            if self.target_track_id is None or self.target_item_id is not None:
                raise ValueError("caption-exclusion binding requires only a target caption track")
            if self.interpolation is not Interpolation.HOLD:
                raise ValueError("caption-exclusion binding requires hold interpolation")
        elif self.target_item_id is None or self.target_track_id is not None:
            raise ValueError("visual tracking binding requires only a target item")
        if self.driver == "blur" and self.blur_region is None:
            raise ValueError("blur tracking binding requires an inside or outside region")
        if self.driver != "blur" and self.model_fields_set & {"blur_region", "blur_shape"}:
            raise ValueError("blur options are valid only for blur tracking bindings")
        if self.driver != "mask" and self.model_fields_set & {"mask_shape", "mask_region"}:
            raise ValueError("mask options are valid only for mask tracking bindings")
        if self.maximum_source_gap is not None and self.maximum_source_gap.value <= 0:
            raise ValueError("maximum_source_gap must be positive")
        return self


class TrackingMappingEvidence(VisualModel):
    subject_id: str = Field(min_length=1)
    source_time: RationalTime
    timeline_time: RationalTime
    target_time: RationalTime
    frame_number: int = Field(ge=0)
    source_mapping_error: RationalTime
    confidence: float = Field(ge=0, le=1)
    manual: bool = False


class TrackingBindingApplication(VisualModel):
    binding_id: str
    patch: TimelinePatch
    effect_ids: tuple[str, ...] = ()
    collision_region_ids: tuple[str, ...] = ()
    evidence: tuple[TrackingMappingEvidence, ...] = Field(min_length=1)

    @property
    def observation_count(self) -> int:
        return len(self.evidence)
