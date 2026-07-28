"""Strict migration results and loss accounting for legacy/interchange adapters."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import JsonValue, Project
from video_engine.core.validation import validate_project


class AdapterKind(StrEnum):
    LEGACY_EDL = "legacy_edl"
    FACELESS = "faceless"
    CAPTION = "caption"
    CMX_EDL = "cmx_edl"
    FCPXML = "fcpxml"
    OTIO = "otio"


class MigrationDisposition(StrEnum):
    EXECUTED = "executed"
    APPROXIMATED = "approximated"
    PRESERVED = "preserved"
    IMPROVED = "improved"
    DROPPED = "dropped"


class MigrationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class MigrationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    severity: MigrationSeverity
    disposition: MigrationDisposition
    message: str = Field(min_length=1)
    source_path: str | None = None
    canonical_path: str | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)


class MigrationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    adapter: AdapterKind
    adapter_version: str = "1.0.0"
    source_path: Path
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sidecar_sha256: dict[str, str] = Field(default_factory=dict)
    source_schema: str
    project_id: str
    project_schema_version: str
    issues: tuple[MigrationIssue, ...] = ()
    preserved_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    resolved_assets: tuple[str, ...] = ()
    offline_assets: tuple[str, ...] = ()

    @model_validator(mode="after")
    def valid_digests(self) -> MigrationReport:
        if any(
            len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest)
            for digest in self.sidecar_sha256.values()
        ):
            raise ValueError("sidecar hashes must be lowercase SHA-256 digests")
        return self

    @property
    def valid(self) -> bool:
        return not any(issue.severity is MigrationSeverity.ERROR for issue in self.issues)


class MigrationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project: Project
    report: MigrationReport

    @model_validator(mode="after")
    def consistent_report(self) -> MigrationResult:
        if self.report.project_id != self.project.id:
            raise ValueError("migration report project_id does not match project")
        if self.report.project_schema_version != self.project.schema_version:
            raise ValueError("migration report schema version does not match project")
        if self.report.valid and not validate_project(self.project).valid:
            raise ValueError("valid migration report contains an invalid canonical project")
        return self
