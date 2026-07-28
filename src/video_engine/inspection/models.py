"""Strict requests and artifacts for project and encoded-media inspection."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import JsonValue
from video_engine.core.time import RationalTime, TimeRange


class InspectionKind(StrEnum):
    TIMELINE = "timeline"
    RANGE = "range"
    CUT = "cut"
    AUDIO = "audio"
    CAPTIONS = "captions"


class InspectionStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class InspectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: InspectionKind
    sequence_id: str | None = None
    media_path: Path | None = None
    timeline_range: TimeRange | None = None
    cut_time: RationalTime | None = None
    cut_window: RationalTime = Field(default_factory=lambda: RationalTime(value=2, timescale=1))
    output_dir: Path | None = None
    frame_count: int = Field(default=12, ge=1, le=100)
    waveform_width: int = Field(default=1600, ge=320, le=8192)
    waveform_height: int = Field(default=320, ge=80, le=2048)
    peak_buckets: int = Field(default=1000, ge=16, le=100_000)
    timeline_page_duration: RationalTime = Field(
        default_factory=lambda: RationalTime(value=300, timescale=1)
    )
    max_lanes_per_page: int = Field(default=20, ge=1, le=100)
    silence_noise_db: float = Field(default=-60, ge=-120, le=-1)
    silence_min_duration: RationalTime = Field(
        default_factory=lambda: RationalTime(value=2, timescale=5)
    )
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_kind_inputs(self) -> InspectionRequest:
        if (
            self.kind in {InspectionKind.RANGE, InspectionKind.CUT, InspectionKind.AUDIO}
            and self.media_path is None
        ):
            raise ValueError(f"{self.kind.value} inspection requires media_path")
        if self.kind is InspectionKind.RANGE and self.timeline_range is None:
            raise ValueError("range inspection requires timeline_range")
        if self.kind is InspectionKind.CUT and self.cut_time is None:
            raise ValueError("cut inspection requires cut_time")
        if self.kind is not InspectionKind.CUT and self.cut_time is not None:
            raise ValueError("cut_time is valid only for cut inspection")
        if self.cut_window.value <= 0:
            raise ValueError("cut_window must be positive")
        if self.silence_min_duration.value <= 0:
            raise ValueError("silence_min_duration must be positive")
        if self.timeline_page_duration.value <= 0:
            raise ValueError("timeline_page_duration must be positive")
        return self


class InspectionArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    media_type: str = Field(min_length=1)


class InspectionSample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    frame_index: int = Field(ge=0)
    timeline_time: RationalTime


class InspectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    inspection_id: str = Field(min_length=1)
    kind: InspectionKind
    project_id: str = Field(min_length=1)
    project_revision: int = Field(ge=1)
    sequence_id: str = Field(min_length=1)
    status: InspectionStatus
    output_dir: Path
    report_json: Path
    report_markdown: Path
    artifacts: tuple[InspectionArtifact, ...]
    summary: dict[str, JsonValue]
    warnings: tuple[str, ...] = ()
