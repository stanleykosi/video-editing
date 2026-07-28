"""Strict contracts for sample-accurate synthesized audio assets."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.time import AudioSampleTime


class SynthEffectKind(StrEnum):
    TICK = "tick"
    SHIMMER = "shimmer"
    GLITCH = "glitch"
    WHOOSH = "whoosh"
    REVERSE_HIT = "reverse_hit"
    POP = "pop"


class SynthEffectEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    start: AudioSampleTime
    kind: SynthEffectKind
    gain: float = Field(default=0.1, ge=0, le=1)
    duration_samples: int | None = Field(default=None, gt=0)
    seed_key: str | None = None


class SynthesisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output_path: Path
    duration: AudioSampleTime
    events: tuple[SynthEffectEvent, ...]
    recipe_version: Literal["canonical-v1", "legacy-video-use-v1"] = "canonical-v1"

    @model_validator(mode="after")
    def validate_sample_domain(self) -> SynthesisRequest:
        if self.duration.samples <= 0:
            raise ValueError("synthesis duration must be positive")
        for event in self.events:
            if event.start.sample_rate != self.duration.sample_rate:
                raise ValueError("all synthesis events must use the output sample rate")
            if event.start.samples < 0:
                raise ValueError("synthesis event starts cannot be negative")
        return self


class SynthesisResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output_path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sample_rate: int = Field(gt=0)
    sample_count: int = Field(gt=0)
    event_count: int = Field(ge=0)
