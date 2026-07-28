"""Backend-neutral color pipeline requests."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import (
    ColorSpace,
    DeliveryProfile,
    Effect,
    EffectKind,
    ProjectSettings,
)
from video_engine.core.time import TimeRange
from video_engine.render.effects import parse_visual_parameters


class TechnicalNormalization(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tone_map: Literal["none", "hable", "mobius", "reinhard", "clip"] = "none"
    peak_nits: float = Field(default=100, gt=0)


class CreativeGrade(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    exposure_stops: float = Field(default=0, ge=-10, le=10)
    temperature: float = Field(default=0, ge=-1, le=1)
    tint: float = Field(default=0, ge=-1, le=1)
    contrast: float = Field(default=1, ge=0, le=4)
    gamma: float = Field(default=1, ge=0.1, le=10)
    saturation: float = Field(default=1, ge=0, le=4)
    highlights: float = Field(default=0, ge=-1, le=1)
    shadows: float = Field(default=0, ge=-1, le=1)


class ColorMeasurements(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    analyzer_version: Literal["signalstats-v3"] = "signalstats-v3"
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_range: TimeRange
    requested_samples: int = Field(ge=1, le=256)
    frames_analyzed: int = Field(ge=1)
    bit_depth: int = Field(ge=8, le=32)
    y_mean: float = Field(ge=0, le=1)
    y_range: float = Field(ge=0, le=1)
    y_std: float = Field(ge=0, le=1)
    saturation_mean: float = Field(ge=0)
    ffmpeg_fingerprint: str = Field(min_length=1)
    ffprobe_fingerprint: str = Field(min_length=1)
    cache_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    cache_hit: bool = False

    @model_validator(mode="after")
    def bounded_sample_count(self) -> ColorMeasurements:
        if self.frames_analyzed > self.requested_samples:
            raise ValueError("analyzed frame count exceeds the requested sample bound")
        return self


class AutoGradePolicy(BaseModel):
    """Caller-visible measured correction policy with no editorial inference."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default="legacy-clean-v1", min_length=1)
    flat_range_floor: float = Field(default=0.50, ge=0, le=1)
    flat_range_threshold: float = Field(default=0.65, ge=0, le=1)
    baseline_contrast: float = Field(default=1.03, ge=0, le=4)
    maximum_contrast: float = Field(default=1.08, ge=0, le=4)
    dark_mean_floor: float = Field(default=0.30, ge=0, le=1)
    dark_mean_threshold: float = Field(default=0.42, ge=0, le=1)
    threshold_gamma: float = Field(default=1.02, ge=0.1, le=10)
    maximum_gamma: float = Field(default=1.10, ge=0.1, le=10)
    bright_mean_threshold: float = Field(default=0.60, ge=0, le=1)
    bright_gamma: float = Field(default=0.97, ge=0.1, le=10)
    baseline_saturation: float = Field(default=0.98, ge=0, le=4)
    low_saturation_threshold: float = Field(default=0.18, ge=0)
    low_saturation_adjustment: float = Field(default=1.04, ge=0, le=4)
    high_saturation_threshold: float = Field(default=0.38, ge=0)
    high_saturation_adjustment: float = Field(default=0.96, ge=0, le=4)
    minimum_contrast: float = Field(default=0.94, ge=0, le=4)
    minimum_gamma: float = Field(default=0.94, ge=0.1, le=10)
    minimum_saturation: float = Field(default=0.94, ge=0, le=4)
    maximum_saturation: float = Field(default=1.06, ge=0, le=4)

    @model_validator(mode="after")
    def ordered_thresholds(self) -> AutoGradePolicy:
        if self.flat_range_floor >= self.flat_range_threshold:
            raise ValueError("flat range floor must be below its threshold")
        if self.dark_mean_floor >= self.dark_mean_threshold:
            raise ValueError("dark mean floor must be below its threshold")
        if self.dark_mean_threshold >= self.bright_mean_threshold:
            raise ValueError("dark threshold must be below bright threshold")
        if self.low_saturation_threshold >= self.high_saturation_threshold:
            raise ValueError("low saturation threshold must be below high threshold")
        if self.maximum_contrast < self.baseline_contrast:
            raise ValueError("maximum contrast must not be below baseline contrast")
        if self.minimum_contrast > self.baseline_contrast:
            raise ValueError("minimum contrast must not exceed baseline contrast")
        if self.maximum_gamma < max(self.threshold_gamma, 1.0):
            raise ValueError("maximum gamma must cover the threshold and neutral values")
        if self.minimum_gamma > min(self.bright_gamma, 1.0):
            raise ValueError("minimum gamma must cover the bright and neutral values")
        if self.minimum_saturation > min(
            self.baseline_saturation,
            self.low_saturation_adjustment,
            self.high_saturation_adjustment,
        ) or self.maximum_saturation < max(
            self.baseline_saturation,
            self.low_saturation_adjustment,
            self.high_saturation_adjustment,
        ):
            raise ValueError("saturation clamps must cover every policy adjustment")
        return self

    def grade(self, measurements: ColorMeasurements) -> CreativeGrade:
        contrast = self.baseline_contrast
        if measurements.y_range < self.flat_range_threshold:
            progress = max(
                0.0,
                min(
                    1.0,
                    (measurements.y_range - self.flat_range_floor)
                    / (self.flat_range_threshold - self.flat_range_floor),
                ),
            )
            contrast = (
                self.maximum_contrast - (self.maximum_contrast - self.baseline_contrast) * progress
            )

        gamma = 1.0
        if measurements.y_mean < self.dark_mean_threshold:
            progress = max(
                0.0,
                min(
                    1.0,
                    (measurements.y_mean - self.dark_mean_floor)
                    / (self.dark_mean_threshold - self.dark_mean_floor),
                ),
            )
            gamma = self.maximum_gamma - (self.maximum_gamma - self.threshold_gamma) * progress
        elif measurements.y_mean > self.bright_mean_threshold:
            gamma = self.bright_gamma

        saturation = self.baseline_saturation
        if measurements.saturation_mean < self.low_saturation_threshold:
            saturation = self.low_saturation_adjustment
        elif measurements.saturation_mean > self.high_saturation_threshold:
            saturation = self.high_saturation_adjustment

        return CreativeGrade(
            contrast=max(self.minimum_contrast, min(self.maximum_contrast, contrast)),
            gamma=max(self.minimum_gamma, min(self.maximum_gamma, gamma)),
            saturation=max(
                self.minimum_saturation,
                min(self.maximum_saturation, saturation),
            ),
        )


class MeasuredAutoGrade(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy: AutoGradePolicy
    measurements: ColorMeasurements
    grade: CreativeGrade
    effect: Effect


class ColorPipeline(BaseModel):
    """A complete color decision that lowers to canonical effects/settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_space: ColorSpace
    working_space: ColorSpace = ColorSpace.REC709
    normalization: TechnicalNormalization | None = None
    creative_grade: CreativeGrade | None = None
    lut_path: Path | None = None
    output_space: ColorSpace = ColorSpace.REC709
    output_pixel_format: str = Field(default="yuv420p", min_length=1)

    @model_validator(mode="after")
    def valid_output_format(self) -> ColorPipeline:
        if self.output_space in {ColorSpace.HLG, ColorSpace.PQ} and "10" not in (
            self.output_pixel_format
        ):
            raise ValueError("HLG and PQ output requires a 10-bit pixel format")
        return self

    def effects(self, *, id_prefix: str = "color") -> tuple[Effect, ...]:
        effects = [
            Effect(
                id=f"{id_prefix}-interpretation",
                kind=EffectKind.COLOR_INTERPRETATION,
                parameters={"input_space": self.input_space.value},
            )
        ]
        if self.normalization is not None:
            effects.append(
                Effect(
                    id=f"{id_prefix}-normalization",
                    kind=EffectKind.COLOR_NORMALIZATION,
                    parameters=self.normalization.model_dump(mode="json"),
                )
            )
        if self.creative_grade is not None:
            effects.append(
                Effect(
                    id=f"{id_prefix}-grade",
                    kind=EffectKind.COLOR_GRADE,
                    parameters=self.creative_grade.model_dump(mode="json"),
                )
            )
        if self.lut_path is not None:
            effects.append(
                Effect(
                    id=f"{id_prefix}-lut",
                    kind=EffectKind.LUT,
                    parameters={"path": str(self.lut_path)},
                )
            )
        for effect in effects:
            parse_visual_parameters(effect)
        return tuple(effects)

    def apply_project_settings(self, settings: ProjectSettings) -> ProjectSettings:
        return settings.model_copy(update={"working_color_space": self.working_space})

    def apply_delivery_profile(self, profile: DeliveryProfile) -> DeliveryProfile:
        return profile.model_copy(
            update={
                "output_color_space": self.output_space,
                "pixel_format": self.output_pixel_format,
            }
        )
