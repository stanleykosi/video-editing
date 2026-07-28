"""Atomic JSON/Markdown QC reports and diagnostic contact-sheet evidence."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from video_engine.config import EngineConfig
from video_engine.errors import EngineError, ErrorCode
from video_engine.media.probe import probe_media
from video_engine.process import CommandRunner
from video_engine.render.cache import sha256_file

from .models import QCEvidenceArtifact, QCReport


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise EngineError(
            ErrorCode.STORAGE,
            "failed to write QC report",
            context={"path": str(path), "detail": str(exc)},
        ) from exc


def report_markdown(report: QCReport) -> str:
    lines = [
        "# Technical QC Report",
        "",
        f"- Run: `{report.run_id}`",
        f"- Project: `{report.project_id}` revision {report.project_revision}",
        f"- Sequence: `{report.sequence_id}`",
        f"- Status: **{report.status.value}**",
        f"- Output: `{report.output_path}`" if report.output_path is not None else "- Output: none",
        f"- Started: {report.started_at.isoformat()}",
        f"- Completed: {report.completed_at.isoformat()}",
        "",
        "## Checks",
        "",
        "| Scope | Check | Status | Summary |",
        "|---|---|---|---|",
    ]
    for check in report.checks:
        summary = check.summary.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {check.scope.value} | `{check.code}` | {check.status.value} | {summary} |")
    lines.extend(["", "## Findings", ""])
    if not report.findings:
        lines.append("No technical findings.")
    else:
        for finding in report.findings:
            disposition = "BLOCKING" if finding.blocking else "NON-BLOCKING"
            location = f" at `{finding.path}`" if finding.path else ""
            lines.append(f"- **{disposition}** `{finding.code}`{location}: {finding.message}")
            for measurement in finding.measurements:
                unit = f" {measurement.unit}" if measurement.unit else ""
                expected = (
                    f"; expected {measurement.expected}" if measurement.expected is not None else ""
                )
                lines.append(f"  - `{measurement.name}`: {measurement.value}{unit}{expected}")
    lines.extend(["", "## Evidence", ""])
    if not report.evidence:
        lines.append("No file evidence was generated.")
    else:
        for artifact in report.evidence:
            lines.append(
                f"- `{artifact.kind}`: `{artifact.path}` "
                f"(sha256 `{artifact.sha256}`, {artifact.size_bytes} bytes)"
            )
    lines.extend(["", "## Policy", "", "```json"])
    lines.append(json.dumps(report.policy.model_dump(mode="json"), indent=2, sort_keys=True))
    lines.extend(["```", ""])
    return "\n".join(lines)


def write_reports(report: QCReport, directory: Path) -> tuple[Path, Path]:
    json_path = directory / "qc-report.json"
    markdown_path = directory / "qc-report.md"
    _atomic_text(
        json_path,
        json.dumps(
            report.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        + "\n",
    )
    _atomic_text(markdown_path, report_markdown(report))
    return json_path.resolve(), markdown_path.resolve()


def generate_contact_sheet(
    output_path: Path,
    directory: Path,
    config: EngineConfig,
    runner: CommandRunner,
) -> QCEvidenceArtifact:
    started = time.monotonic()
    media_probe = probe_media(output_path, config, runner, deep_vfr=False)
    if not media_probe.video_streams:
        raise EngineError(
            ErrorCode.QC_FAILED,
            "contact sheet requires an encoded video stream",
            context={"path": str(output_path)},
        )
    duration = (
        float(media_probe.duration.fraction)
        if media_probe.duration is not None and media_probe.duration.value > 0
        else 1.0
    )
    interval = max(duration / 12, 1 / 120)
    destination = directory / "contact-sheet.png"
    result = runner.run(
        [
            config.ffmpeg_path,
            "-v",
            "error",
            "-y",
            "-i",
            output_path,
            "-vf",
            (f"fps=1/{interval:.9f},scale=320:-2," "tile=4x3:padding=4:margin=4:color=black"),
            "-frames:v",
            "1",
            destination,
        ],
        check=False,
    )
    if result.return_code != 0 or not destination.is_file():
        raise EngineError(
            ErrorCode.QC_FAILED,
            "FFmpeg failed to generate QC contact-sheet evidence",
            context={
                "path": str(output_path),
                "return_code": result.return_code,
                "stderr_tail": result.stderr[-2000:],
            },
        )
    return QCEvidenceArtifact(
        id="evidence-contact-sheet",
        kind="contact_sheet",
        path=destination.resolve(),
        sha256=sha256_file(destination),
        size_bytes=destination.stat().st_size,
        media_type="image/png",
        description=(
            "Twelve-frame encoded-output contact sheet " f"({time.monotonic() - started:.3f}s)"
        ),
    )
