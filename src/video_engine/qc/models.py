"""Strict contracts for technical quality-control runs and evidence."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import JsonValue


class QCScope(StrEnum):
    INGEST = "ingest"
    TIMELINE = "timeline"
    VIDEO = "video"
    AUDIO = "audio"
    DELIVERY = "delivery"


class QCSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class QCCheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class QCOverallStatus(StrEnum):
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


class QCPolicy(BaseModel):
    """Caller-controlled technical thresholds; no editorial policy lives here."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    duration_tolerance_frames: int = Field(default=1, ge=0, le=100)
    audio_video_tolerance_samples: int = Field(default=1_024, ge=0, le=96_000)
    black_min_duration_seconds: float = Field(default=0.5, gt=0, le=60)
    freeze_min_duration_seconds: float = Field(default=2.0, gt=0, le=3_600)
    silence_min_duration_seconds: float = Field(default=2.0, gt=0, le=3_600)
    silence_noise_db: float = Field(default=-60, ge=-120, le=-1)
    loudness_tolerance_lu: float = Field(default=1.0, ge=0, le=10)
    loudness_range_tolerance_lu: float = Field(default=3.0, ge=0, le=30)
    clipping_threshold_dbfs: float = Field(default=-0.1, ge=-12, le=0)
    channel_imbalance_db: float = Field(default=6.0, ge=0, le=60)
    mono_cancellation_db: float = Field(default=9.0, ge=0, le=60)
    boundary_pop_threshold: float = Field(default=0.35, gt=0, le=2)
    max_boundary_checks: int = Field(default=250, ge=1, le=10_000)
    black_is_blocking: bool = False
    freeze_is_blocking: bool = False
    implicit_blank_is_blocking: bool = False
    unexpected_silence_is_blocking: bool = False
    verify_source_hashes: bool = True
    decode_all_sources: bool = True
    generate_contact_sheet: bool = True
    fail_on_warnings: bool = False


class QCRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output_path: Path | None = None
    sequence_id: str | None = None
    delivery_profile_id: str | None = None
    scopes: tuple[QCScope, ...] = tuple(QCScope)
    report_dir: Path | None = None
    expected_output_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    expected_caption_paths: tuple[Path, ...] = ()
    policy: QCPolicy = Field(default_factory=QCPolicy)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_selection(self) -> QCRequest:
        if not self.scopes:
            raise ValueError("at least one QC scope is required")
        if len(self.scopes) != len(set(self.scopes)):
            raise ValueError("QC scopes must not contain duplicates")
        output_scopes = {QCScope.VIDEO, QCScope.AUDIO, QCScope.DELIVERY}
        if set(self.scopes) & output_scopes and self.output_path is None:
            raise ValueError("video, audio, and delivery QC require output_path")
        return self


class QCMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    value: JsonValue
    unit: str | None = None
    expected: JsonValue = None
    tolerance: JsonValue = None


class QCEvidenceArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    media_type: str = Field(min_length=1)
    description: str = ""


class QCFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    scope: QCScope
    severity: QCSeverity
    blocking: bool
    message: str = Field(min_length=1)
    path: str | None = None
    measurements: tuple[QCMeasurement, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class QCCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    scope: QCScope
    status: QCCheckStatus
    summary: str = Field(min_length=1)
    duration_seconds: float = Field(ge=0)
    findings: tuple[QCFinding, ...] = ()
    measurements: tuple[QCMeasurement, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    error: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def status_matches_findings(self) -> QCCheckResult:
        blocking = any(finding.blocking for finding in self.findings)
        warnings = any(not finding.blocking for finding in self.findings)
        if self.status is QCCheckStatus.FAILED and not blocking:
            raise ValueError("failed QC checks require a blocking finding")
        if self.status is QCCheckStatus.WARNING and (blocking or not warnings):
            raise ValueError("warning QC checks require only non-blocking findings")
        if self.status is QCCheckStatus.PASSED and self.findings:
            raise ValueError("passing QC checks cannot contain findings")
        if self.status is QCCheckStatus.SKIPPED and self.error is None:
            raise ValueError("skipped QC checks require structured error evidence")
        return self


class QCReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    run_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    project_revision: int = Field(ge=1)
    sequence_id: str = Field(min_length=1)
    output_path: Path | None = None
    status: QCOverallStatus
    started_at: datetime
    completed_at: datetime
    policy: QCPolicy
    checks: tuple[QCCheckResult, ...]
    findings: tuple[QCFinding, ...]
    evidence: tuple[QCEvidenceArtifact, ...] = ()
    output_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class QCResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report: QCReport
    json_path: Path
    markdown_path: Path


def check_status(findings: list[QCFinding]) -> QCCheckStatus:
    if any(finding.blocking for finding in findings):
        return QCCheckStatus.FAILED
    if findings:
        return QCCheckStatus.WARNING
    return QCCheckStatus.PASSED


def overall_status(checks: list[QCCheckResult], *, fail_on_warnings: bool) -> QCOverallStatus:
    if any(check.status is QCCheckStatus.FAILED for check in checks):
        return QCOverallStatus.FAILED
    if any(check.status is QCCheckStatus.SKIPPED for check in checks):
        return QCOverallStatus.INCOMPLETE
    if any(check.status is QCCheckStatus.WARNING for check in checks):
        return QCOverallStatus.FAILED if fail_on_warnings else QCOverallStatus.PASSED_WITH_WARNINGS
    return QCOverallStatus.PASSED
