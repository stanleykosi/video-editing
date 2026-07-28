"""Compatibility CLI delegating legacy existing-footage EDLs to VideoEngine.

New code should use `video-engine migrate legacy-edl`, `video-engine render`, and
`video-engine qc` directly. This wrapper retains the historical command shape
without retaining a second renderer implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
# This directory also contains the compatibility launcher `video_engine.py`.
# Keep the package source ahead of the script directory to avoid shadowing it.
sys.path.insert(0, str(ROOT / "src"))

from video_engine.api.engine import VideoEngine  # noqa: E402
from video_engine.core.schema import DeliveryProfile  # noqa: E402
from video_engine.qc.models import QCOverallStatus, QCRequest  # noqa: E402
from video_engine.render.models import RenderMode, RenderRequest  # noqa: E402
from video_engine.storage.atomic import atomic_write_text  # noqa: E402

from .caption_styles import available_caption_styles, build_master_ass  # noqa: E402

ENTRYPOINT_PATH = Path(__file__).resolve()


def _even(value: int) -> int:
    return max(2, value - value % 2)


def _resolution(value: str) -> tuple[int, int]:
    separator = "x" if "x" in value.lower() else ""
    if not separator:
        raise argparse.ArgumentTypeError("resolution must use WIDTHxHEIGHT")
    try:
        width, height = (int(part) for part in value.lower().split("x", 1))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("resolution must use WIDTHxHEIGHT") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("resolution dimensions must be positive")
    return _even(width), _even(height)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_for_caption_probe(payload: dict[str, Any], base: Path) -> Path:
    sources = payload.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise SystemExit("--build-subtitles requires at least one EDL source")
    ranges = payload.get("ranges")
    alias = None
    if isinstance(ranges, list) and ranges and isinstance(ranges[0], dict):
        alias = ranges[0].get("source")
    raw = sources.get(alias) if alias in sources else next(iter(sources.values()))
    path = Path(str(raw))
    return (path if path.is_absolute() else base / path).resolve()


def _write_migration_artifacts(
    engine: VideoEngine,
    project: Any,
    report: Any,
    edl: Path,
) -> tuple[Path, Path]:
    project_path = edl.parent / ".video-engine" / "projects" / f"{edl.stem}.json"
    report_path = edl.parent / ".video-engine" / "migrations" / f"{edl.stem}.json"
    engine.save_project(project, project_path)
    atomic_write_text(report_path, report.model_dump_json(indent=2) + "\n")
    return project_path, report_path


def _profile_without_loudness(profile: DeliveryProfile) -> DeliveryProfile:
    return profile.model_copy(update={"loudness": None})


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a legacy EDL through the canonical VideoEngine"
    )
    parser.add_argument("edl", type=Path, nargs="?")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--build-subtitles", action="store_true")
    parser.add_argument("--caption-style")
    parser.add_argument("--resolution", type=_resolution)
    parser.add_argument("--fit", choices=["cover", "contain", "stretch"])
    parser.add_argument("--list-caption-styles", action="store_true")
    parser.add_argument("--no-subtitles", action="store_true")
    parser.add_argument("--no-loudnorm", action="store_true")
    parser.add_argument("--skip-visual-qc", action="store_true")
    parser.add_argument(
        "--approval",
        type=Path,
        help="Canonical human-reviewed QC approval required for final delivery.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.list_caption_styles:
        print(json.dumps(available_caption_styles(), indent=2, sort_keys=True))
        return 0
    if args.edl is None or args.output is None:
        parser.error("edl and --output are required unless --list-caption-styles is used")
    if args.preview and args.draft:
        parser.error("--preview and --draft are mutually exclusive")
    if args.skip_visual_qc and not (args.preview or args.draft):
        parser.error(
            "unapproved final delivery is no longer supported; render a preview, "
            "run QC with approval, then pass --approval"
        )
    if not (args.preview or args.draft) and args.approval is None:
        parser.error("final delivery requires --approval from a reviewed `video-engine qc` run")

    edl = args.edl.resolve()
    output = args.output.resolve()
    try:
        payload = json.loads(edl.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"failed to load EDL {edl}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("EDL root must be a JSON object")
    modified = False
    if args.resolution is not None:
        payload["resolution"] = f"{args.resolution[0]}x{args.resolution[1]}"
        modified = True
    if args.fit is not None:
        payload["output_fit"] = args.fit
        modified = True
    if args.no_subtitles:
        payload.pop("subtitles", None)
        modified = True
    if args.build_subtitles:
        subtitle_path = edl.parent / "master.ass"
        build_master_ass(
            payload,
            edl.parent,
            subtitle_path,
            _source_for_caption_probe(payload, edl.parent),
            explicit_style_id=args.caption_style,
        )
        payload["subtitles"] = str(subtitle_path)
        modified = True

    temporary_edl: Path | None = None
    migration_source = edl
    if modified:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{edl.stem}.",
            suffix=".json",
            dir=edl.parent,
            delete=False,
        ) as descriptor:
            json.dump(payload, descriptor, indent=2, ensure_ascii=True)
            descriptor.write("\n")
            temporary_edl = Path(descriptor.name)
        migration_source = temporary_edl

    try:
        engine = VideoEngine(edl.parent)
        migration = engine.adapters().import_legacy_edl(migration_source, name=edl.stem)
        project = migration.project
        if args.no_loudnorm:
            project.delivery_profiles = [
                _profile_without_loudness(profile) for profile in project.delivery_profiles
            ]
        project_path, report_path = _write_migration_artifacts(
            engine,
            project,
            migration.report,
            edl,
        )
        mode = (
            RenderMode.DRAFT
            if args.draft
            else RenderMode.PREVIEW if args.preview else RenderMode.FINAL
        )
        profile_id = "final" if mode is RenderMode.FINAL else "preview"
        render = engine.renderer(project).render(
            RenderRequest(
                output_path=output,
                mode=mode,
                delivery_profile_id=profile_id,
                qc_approval_path=(args.approval.resolve() if args.approval else None),
                metadata={"compatibility_entrypoint": "helpers/render.py"},
            )
        )
        qc = engine.qc(project).run(
            QCRequest(
                output_path=output,
                report_dir=(edl.parent / "visual_qc" / "canonical" / render.manifest.render_id),
            )
        )
        acceptable = {
            QCOverallStatus.PASSED,
            QCOverallStatus.PASSED_WITH_WARNINGS,
        }
        result = {
            "ok": qc.report.status in acceptable,
            "deprecated_entrypoint": str(ENTRYPOINT_PATH),
            "canonical_project": str(project_path.resolve()),
            "migration_report": str(report_path.resolve()),
            "migration_source_sha256": migration.report.source_sha256,
            "output": str(render.output_path),
            "output_sha256": render.manifest.output_sha256,
            "render_manifest": str(render.manifest_path),
            "qc_status": qc.report.status.value,
            "qc_report": str(qc.json_path),
            "source_edl_sha256": _sha256(edl),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 2
    finally:
        if temporary_edl is not None:
            temporary_edl.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
