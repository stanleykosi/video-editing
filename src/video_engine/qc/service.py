"""Public technical-QC orchestration with manifest-bound expectations."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from video_engine.config import EngineConfig
from video_engine.core.schema import DeliveryProfile, Project
from video_engine.core.time import RationalTime, TimeRange
from video_engine.errors import EngineError, ErrorCode
from video_engine.process import CommandRunner
from video_engine.render.cache import sha256_file
from video_engine.render.compiler import CompiledRender, RenderCompiler
from video_engine.render.models import RenderManifest, RenderMode, RenderRequest

from .analyzers import QCContext, TechnicalQCAnalyzers, skipped_check
from .models import (
    QCCheckResult,
    QCCheckStatus,
    QCEvidenceArtifact,
    QCFinding,
    QCReport,
    QCRequest,
    QCResult,
    QCScope,
    QCSeverity,
    overall_status,
)
from .reports import generate_contact_sheet, write_reports

Analyzer = Callable[[], list[QCCheckResult]]


class QCService:
    def __init__(
        self,
        project: Project,
        project_root: Path,
        config: EngineConfig,
        runner: CommandRunner | None = None,
    ) -> None:
        self.project = project.model_copy(deep=True)
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)
        self.runner = runner or CommandRunner()

    def run(self, request: QCRequest) -> QCResult:
        started_at = datetime.now(UTC)
        run_id = f"qc-{uuid.uuid4().hex}"
        output = request.output_path.resolve() if request.output_path is not None else None
        manifest, manifest_error = self._load_manifest(output)
        sequence_id = request.sequence_id or (manifest.sequence_id if manifest else None)
        sequence_id = sequence_id or self.project.active_sequence_id
        try:
            sequence = self.project.sequence(sequence_id)
        except StopIteration as exc:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "QC sequence was not found",
                context={"sequence_id": sequence_id},
            ) from exc
        profile = self._profile(request, manifest)
        timeline_range = self._timeline_range(sequence.timeline.duration, manifest)
        report_dir = (
            request.report_dir.resolve()
            if request.report_dir is not None
            else self.project_root / "reports" / "qc" / run_id
        )
        report_dir.mkdir(parents=True, exist_ok=True)
        caption_track_ids, caption_languages = self._caption_selection(manifest)
        manifest_stale = bool(
            manifest
            and (
                manifest.project_id != self.project.id
                or manifest.project_revision != self.project.revision
                or manifest.sequence_id != sequence.id
            )
        )
        compiled = self._compile(
            sequence.id,
            profile,
            timeline_range,
            caption_track_ids,
            caption_languages,
            report_dir,
        )
        context = QCContext(
            project=self.project,
            project_root=self.project_root,
            sequence=sequence,
            profile=profile,
            timeline_range=timeline_range,
            output_path=output,
            report_dir=report_dir,
            config=self.config,
            runner=self.runner,
            compiled=compiled,
            manifest=manifest,
            manifest_output_sha256=manifest.output_sha256 if manifest else None,
            manifest_stale=manifest_stale,
            caption_track_ids=caption_track_ids,
            caption_languages=caption_languages,
        )
        analyzers = TechnicalQCAnalyzers(context, request.policy)
        methods: dict[QCScope, Analyzer] = {
            QCScope.INGEST: analyzers.ingest,
            QCScope.TIMELINE: analyzers.timeline,
            QCScope.VIDEO: analyzers.video,
            QCScope.AUDIO: analyzers.audio,
            QCScope.DELIVERY: lambda: analyzers.delivery(
                request.expected_output_sha256, request.expected_caption_paths
            ),
        }
        checks: list[QCCheckResult] = []
        for scope in request.scopes:
            check_started = time.monotonic()
            try:
                checks.extend(methods[scope]())
            except Exception as exc:
                checks.append(
                    skipped_check(
                        f"{scope.value}.analyzer",
                        scope,
                        check_started,
                        f"technical analyzer failed: {exc}",
                        error_code="qc.analyzer_failed",
                    )
                )
        if QCScope.DELIVERY in request.scopes and manifest_error is not None:
            finding = QCFinding(
                code="delivery.render_manifest_unavailable",
                scope=QCScope.DELIVERY,
                severity=QCSeverity.WARNING,
                blocking=False,
                message=manifest_error,
                path=str(self._manifest_path(output)) if output is not None else None,
            )
            checks.append(
                QCCheckResult(
                    code="delivery.render_manifest",
                    scope=QCScope.DELIVERY,
                    status=QCCheckStatus.WARNING,
                    summary="delivery is not bound to a valid successful render manifest",
                    duration_seconds=0,
                    findings=(finding,),
                )
            )
        if manifest_stale and set(request.scopes) & {
            QCScope.TIMELINE,
            QCScope.VIDEO,
            QCScope.AUDIO,
        }:
            checks.append(
                skipped_check(
                    "timeline.manifest_revision",
                    QCScope.TIMELINE,
                    time.monotonic(),
                    "render manifest revision differs from the loaded project; "
                    "correlation is incomplete",
                    error_code="qc.stale_manifest",
                )
            )
        evidence, evidence_check = self._contact_sheet(request, output, report_dir)
        if evidence_check is not None:
            checks.append(evidence_check)
        findings = [finding for check in checks for finding in check.findings]
        status = overall_status(checks, fail_on_warnings=request.policy.fail_on_warnings)
        output_sha = sha256_file(output) if output is not None and output.is_file() else None
        report = QCReport(
            run_id=run_id,
            project_id=self.project.id,
            project_revision=self.project.revision,
            sequence_id=sequence.id,
            output_path=output,
            status=status,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            policy=request.policy,
            checks=tuple(checks),
            findings=tuple(findings),
            evidence=tuple(evidence),
            output_sha256=output_sha,
            metadata={
                "request": request.metadata,
                "manifest_path": str(self._manifest_path(output)) if output is not None else None,
                "manifest_status": manifest.status if manifest is not None else None,
                "manifest_stale": manifest_stale,
                "delivery_profile": profile.model_dump(mode="json"),
                "timeline_range": timeline_range.model_dump(mode="json"),
            },
        )
        json_path, markdown_path = write_reports(report, report_dir)
        return QCResult(report=report, json_path=json_path, markdown_path=markdown_path)

    def _load_manifest(self, output: Path | None) -> tuple[RenderManifest | None, str | None]:
        if output is None:
            return None, None
        path = self._manifest_path(output)
        if not path.is_file():
            return None, "render manifest is missing"
        try:
            manifest = RenderManifest.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError, ValueError, json.JSONDecodeError) as exc:
            return None, f"render manifest is invalid: {exc}"
        if manifest.status != "succeeded":
            return None, "render manifest does not record a successful output"
        if manifest.output_path.resolve() != output:
            return None, "render manifest output path does not match the QC target"
        return manifest, None

    @staticmethod
    def _manifest_path(output: Path | None) -> Path:
        assert output is not None
        return output.with_suffix(output.suffix + ".render-manifest.json")

    def _profile(self, request: QCRequest, manifest: RenderManifest | None) -> DeliveryProfile:
        if request.delivery_profile_id is not None:
            try:
                return next(
                    profile
                    for profile in self.project.delivery_profiles
                    if profile.id == request.delivery_profile_id
                )
            except StopIteration as exc:
                raise EngineError(
                    ErrorCode.CONFIGURATION,
                    "QC delivery profile was not found",
                    context={"profile_id": request.delivery_profile_id},
                ) from exc
        if manifest is not None:
            payload = manifest.metadata.get("delivery_profile")
            if isinstance(payload, dict):
                try:
                    return DeliveryProfile.model_validate(payload)
                except ValidationError as exc:
                    raise EngineError(
                        ErrorCode.QC_FAILED,
                        "render manifest delivery profile is invalid",
                        context={"detail": str(exc)},
                    ) from exc
        if request.output_path is not None:
            raise EngineError(
                ErrorCode.CONFIGURATION,
                "output QC without a valid render manifest requires delivery_profile_id",
            )
        if not self.project.delivery_profiles:
            raise EngineError(
                ErrorCode.CONFIGURATION,
                "timeline QC requires at least one delivery profile",
            )
        return next(
            (profile for profile in self.project.delivery_profiles if profile.id == "preview"),
            self.project.delivery_profiles[0],
        )

    @staticmethod
    def _timeline_range(
        sequence_duration: RationalTime, manifest: RenderManifest | None
    ) -> TimeRange:
        if manifest is not None:
            payload = manifest.metadata.get("timeline_range")
            if isinstance(payload, dict):
                try:
                    return TimeRange.model_validate(payload)
                except ValidationError as exc:
                    raise EngineError(
                        ErrorCode.QC_FAILED,
                        "render manifest timeline range is invalid",
                        context={"detail": str(exc)},
                    ) from exc
        return TimeRange(start=RationalTime.zero(), duration=sequence_duration)

    @staticmethod
    def _caption_selection(
        manifest: RenderManifest | None,
    ) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None]:
        if manifest is None:
            return None, None
        track_ids = manifest.metadata.get("caption_track_ids")
        languages = manifest.metadata.get("caption_languages")
        return (
            tuple(str(value) for value in track_ids) if isinstance(track_ids, list) else None,
            tuple(str(value) for value in languages) if isinstance(languages, list) else None,
        )

    def _compile(
        self,
        sequence_id: str,
        profile: DeliveryProfile,
        timeline_range: TimeRange,
        caption_track_ids: tuple[str, ...] | None,
        caption_languages: tuple[str, ...] | None,
        report_dir: Path,
    ) -> CompiledRender | None:
        if not any(existing.id == profile.id for existing in self.project.delivery_profiles):
            return None
        request = RenderRequest(
            output_path=report_dir / ".qc-compile-probe.mp4",
            mode=RenderMode.PREVIEW,
            sequence_id=sequence_id,
            delivery_profile_id=profile.id,
            timeline_range=timeline_range,
            caption_track_ids=caption_track_ids,
            caption_languages=caption_languages,
        )
        try:
            return RenderCompiler(self.project, self.project_root, self.config).compile(request)
        except EngineError:
            return None

    def _contact_sheet(
        self,
        request: QCRequest,
        output: Path | None,
        report_dir: Path,
    ) -> tuple[list[QCEvidenceArtifact], QCCheckResult | None]:
        if (
            not request.policy.generate_contact_sheet
            or output is None
            or not set(request.scopes) & {QCScope.VIDEO, QCScope.DELIVERY}
        ):
            return [], None
        started = time.monotonic()
        try:
            artifact = generate_contact_sheet(output, report_dir, self.config, self.runner)
        except EngineError as exc:
            return [], skipped_check(
                "video.contact_sheet",
                QCScope.VIDEO,
                started,
                exc.message,
                error_code=exc.code.value,
            )
        return [artifact], QCCheckResult(
            code="video.contact_sheet",
            scope=QCScope.VIDEO,
            status=QCCheckStatus.PASSED,
            summary="generated and hashed encoded-output contact sheet",
            duration_seconds=time.monotonic() - started,
            evidence_ids=(artifact.id,),
        )
