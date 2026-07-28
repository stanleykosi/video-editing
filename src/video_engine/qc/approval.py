"""Human visual-QC approval records bound to technical evidence and revision."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from video_engine.core.schema import Project
from video_engine.errors import EngineError, ErrorCode
from video_engine.render.cache import sha256_file
from video_engine.storage.atomic import atomic_write_text

from .models import QCOverallStatus, QCResult


class QCApproval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    approval_id: str = Field(min_length=1)
    status: Literal["approved"] = "approved"
    project_id: str = Field(min_length=1)
    project_revision: int = Field(ge=1)
    sequence_id: str = Field(min_length=1)
    preview_output_path: Path
    preview_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    qc_report_path: Path
    qc_report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    qc_status: Literal["passed", "passed_with_warnings"]
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    notes: str = Field(min_length=1)


class QCApprovalService:
    def create(
        self,
        result: QCResult,
        *,
        reviewed_by: str,
        notes: str,
        path: Path | None = None,
    ) -> tuple[QCApproval, Path]:
        if result.report.status not in {
            QCOverallStatus.PASSED,
            QCOverallStatus.PASSED_WITH_WARNINGS,
        }:
            raise EngineError(
                ErrorCode.QC_FAILED,
                "only a complete passing QC report can be approved",
                context={"status": result.report.status.value},
            )
        output = result.report.output_path
        if output is None or not output.resolve().is_file():
            raise EngineError(
                ErrorCode.QC_FAILED,
                "visual approval requires the reviewed preview output",
                context={"output": str(output) if output is not None else None},
            )
        report_path = result.json_path.resolve()
        if not report_path.is_file():
            raise EngineError(
                ErrorCode.QC_FAILED,
                "visual approval requires the persisted QC report",
                context={"report": str(report_path)},
            )
        contact_sheets = [
            evidence for evidence in result.report.evidence if evidence.kind == "contact_sheet"
        ]
        if not contact_sheets:
            raise EngineError(
                ErrorCode.QC_FAILED,
                "visual approval requires a generated contact sheet",
            )
        for evidence in contact_sheets:
            if not evidence.path.resolve().is_file() or (
                sha256_file(evidence.path.resolve()) != evidence.sha256
            ):
                raise EngineError(
                    ErrorCode.QC_FAILED,
                    "visual approval contact-sheet evidence is missing or changed",
                    context={"path": str(evidence.path)},
                )
        reviewer = reviewed_by.strip()
        review_notes = notes.strip()
        if not reviewer or not review_notes:
            raise EngineError(
                ErrorCode.CONFIGURATION,
                "visual approval requires reviewer identity and review notes",
            )
        qc_status: Literal["passed", "passed_with_warnings"] = (
            "passed" if result.report.status is QCOverallStatus.PASSED else "passed_with_warnings"
        )
        approval = QCApproval(
            approval_id=f"approval-{uuid.uuid4().hex}",
            project_id=result.report.project_id,
            project_revision=result.report.project_revision,
            sequence_id=result.report.sequence_id,
            preview_output_path=output.resolve(),
            preview_output_sha256=sha256_file(output.resolve()),
            qc_report_path=report_path,
            qc_report_sha256=sha256_file(report_path),
            qc_status=qc_status,
            reviewed_by=reviewer,
            reviewed_at=datetime.now(UTC),
            notes=review_notes,
        )
        destination = (path or report_path.parent / "qc-approval.json").resolve()
        atomic_write_text(destination, approval.model_dump_json(indent=2) + "\n")
        return approval, destination

    def validate(
        self,
        project: Project,
        sequence_id: str,
        path: Path,
    ) -> QCApproval:
        source = path.resolve()
        try:
            approval = QCApproval.model_validate_json(source.read_text(encoding="utf-8"))
        except (OSError, ValidationError, ValueError, json.JSONDecodeError) as exc:
            raise EngineError(
                ErrorCode.QC_FAILED,
                "final render QC approval is missing or invalid",
                context={"path": str(source), "detail": str(exc)},
            ) from exc
        mismatches: dict[str, object] = {}
        if approval.project_id != project.id:
            mismatches["project_id"] = {
                "approval": approval.project_id,
                "project": project.id,
            }
        if approval.project_revision != project.revision:
            mismatches["project_revision"] = {
                "approval": approval.project_revision,
                "project": project.revision,
            }
        if approval.sequence_id != sequence_id:
            mismatches["sequence_id"] = {
                "approval": approval.sequence_id,
                "render": sequence_id,
            }
        if mismatches:
            raise EngineError(
                ErrorCode.QC_FAILED,
                "final render QC approval does not match the canonical revision",
                context=mismatches,
            )
        for label, evidence, expected in (
            (
                "preview output",
                approval.preview_output_path.resolve(),
                approval.preview_output_sha256,
            ),
            ("QC report", approval.qc_report_path.resolve(), approval.qc_report_sha256),
        ):
            if not evidence.is_file() or sha256_file(evidence) != expected:
                raise EngineError(
                    ErrorCode.QC_FAILED,
                    f"approved {label} evidence is missing or changed",
                    context={"path": str(evidence), "expected_sha256": expected},
                )
        return approval
