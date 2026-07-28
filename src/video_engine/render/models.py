"""Public render request, artifact, manifest, and result contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import JsonValue
from video_engine.core.time import RationalTime, TimeRange
from video_engine.render.nodes import ArtifactType, NodeKind


class RenderMode(StrEnum):
    DRAFT = "draft"
    PREVIEW = "preview"
    RANGE = "range"
    FINAL = "final"


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output_path: Path
    mode: RenderMode = RenderMode.PREVIEW
    sequence_id: str | None = None
    delivery_profile_id: str | None = None
    timeline_range: TimeRange | None = None
    caption_track_ids: tuple[str, ...] | None = None
    caption_languages: tuple[str, ...] | None = None
    chapter_id: str | None = None
    sectioning: bool = True
    section_duration: RationalTime | None = None
    backend: str = "ffmpeg"
    use_cache: bool = True
    resume: bool = True
    qc_approval_path: Path | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def range_mode_has_range(self) -> RenderRequest:
        if (
            self.mode is RenderMode.RANGE
            and self.timeline_range is None
            and self.chapter_id is None
        ):
            raise ValueError("range render mode requires timeline_range or chapter_id")
        if self.timeline_range is not None and self.chapter_id is not None:
            raise ValueError("select a timeline range or chapter, not both")
        if self.section_duration is not None and self.section_duration.value <= 0:
            raise ValueError("section duration must be positive")
        if self.caption_track_ids is not None and len(self.caption_track_ids) != len(
            set(self.caption_track_ids)
        ):
            raise ValueError("caption_track_ids must not contain duplicates")
        if self.caption_languages is not None and len(self.caption_languages) != len(
            set(self.caption_languages)
        ):
            raise ValueError("caption_languages must not contain duplicates")
        if self.caption_track_ids is not None and self.caption_languages is not None:
            raise ValueError("select captions by track ids or languages, not both")
        return self


class RenderArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str
    cache_key: str
    artifact_type: ArtifactType
    path: Path
    cached: bool = False
    size_bytes: int = Field(ge=0)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class NodeExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str
    node_type: NodeKind
    backend: str | None = None
    backend_version: str | None = None
    cache_key: str
    status: str
    cached: bool
    started_at: datetime
    duration_seconds: float = Field(ge=0)
    artifact_path: Path | None = None
    artifact_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    error: dict[str, JsonValue] | None = None


class RenderManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: str = "1.2.0"
    render_id: str
    project_id: str
    project_revision: int
    sequence_id: str
    graph_hash: str
    backend: str
    backend_version: str
    mode: RenderMode
    status: Literal["succeeded", "failed"] = "succeeded"
    output_path: Path
    started_at: datetime
    completed_at: datetime
    records: tuple[NodeExecutionRecord, ...]
    output_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    output_size_bytes: int | None = Field(default=None, ge=0)
    failure: dict[str, JsonValue] | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class RenderResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output_path: Path
    manifest_path: Path
    manifest: RenderManifest
    cache_hits: int = Field(ge=0)
    executed_nodes: int = Field(ge=0)


class PartialRenderResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    graph_hash: str
    target_node_ids: tuple[str, ...]
    artifacts: dict[str, RenderArtifact]
    records: tuple[NodeExecutionRecord, ...]
    cache_hits: int = Field(ge=0)
    executed_nodes: int = Field(ge=0)
