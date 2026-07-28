"""Strict media probe, registry, and derivative records."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import JsonValue
from video_engine.core.time import FrameRate, RationalTime


class MediaKind(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    SUBTITLE = "subtitle"
    DATA = "data"
    UNKNOWN = "unknown"


class MediaStreamProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    kind: MediaKind
    codec_name: str | None = None
    codec_long_name: str | None = None
    profile: str | None = None
    duration: RationalTime | None = None
    time_base: RationalTime | None = None
    average_frame_rate: FrameRate | None = None
    real_frame_rate: FrameRate | None = None
    frame_count: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    pixel_format: str | None = None
    sample_aspect_ratio: str | None = None
    display_aspect_ratio: str | None = None
    color_range: str | None = None
    color_space: str | None = None
    color_transfer: str | None = None
    color_primaries: str | None = None
    bits_per_raw_sample: int | None = Field(default=None, ge=0)
    sample_rate: int | None = Field(default=None, gt=0)
    channels: int | None = Field(default=None, gt=0)
    channel_layout: str | None = None
    rotation_degrees: int = 0
    language: str | None = None
    disposition: dict[str, int] = Field(default_factory=dict)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class MediaProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format_name: str
    format_long_name: str | None = None
    duration: RationalTime | None = None
    size_bytes: int = Field(ge=0)
    bit_rate: int | None = Field(default=None, ge=0)
    streams: list[MediaStreamProbe]
    variable_frame_rate: bool = False
    hdr: bool = False
    warnings: list[str] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)

    @property
    def video_streams(self) -> list[MediaStreamProbe]:
        return [stream for stream in self.streams if stream.kind is MediaKind.VIDEO]

    @property
    def audio_streams(self) -> list[MediaStreamProbe]:
        return [stream for stream in self.streams if stream.kind is MediaKind.AUDIO]


class DerivedAssetKind(StrEnum):
    PROXY = "proxy"
    THUMBNAILS = "thumbnails"
    WAVEFORM = "waveform"
    CONFORMED = "conformed"


class DerivedAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[0-9a-f]{64}$")
    kind: DerivedAssetKind
    paths: list[Path] = Field(min_length=1)
    parameters: dict[str, JsonValue]
    created_at: datetime
    tool_fingerprint: str
    sha256: list[str] = Field(default_factory=list)
    size_bytes: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_matches_paths(self) -> DerivedAsset:
        if len(self.sha256) != len(self.paths):
            raise ValueError("derived asset checksums must match paths")
        if len(self.size_bytes) != len(self.paths):
            raise ValueError("derived asset sizes must match paths")
        return self


class MediaRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^media-[0-9a-f]{16}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_paths: list[Path] = Field(min_length=1)
    canonical_path: Path
    size_bytes: int = Field(ge=0)
    imported_at: datetime
    probe: MediaProbe
    derivatives: list[DerivedAsset] = Field(default_factory=list)
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class MediaRegistryData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    records: list[MediaRecord] = Field(default_factory=list)


class SourceValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_id: str
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
