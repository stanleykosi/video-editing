"""Command tree for the stable engine CLI."""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Never

from pydantic import ValidationError

from video_engine.adapters.exporter import ExportFormat
from video_engine.api.engine import VideoEngine
from video_engine.config import EngineConfig
from video_engine.core.time import FrameRate, RationalTime, TimeRange
from video_engine.errors import EngineError, ErrorCode
from video_engine.inspection.models import InspectionKind, InspectionRequest
from video_engine.logging import configure_logging
from video_engine.operations.models import PatchEnvelope
from video_engine.qc.models import QCOverallStatus, QCPolicy, QCRequest, QCScope
from video_engine.render.models import RenderMode, RenderRequest
from video_engine.storage.atomic import atomic_write_text


class _MachineUsageError(Exception):
    pass


class _EngineArgumentParser(argparse.ArgumentParser):
    machine_errors = False

    def error(self, message: str) -> Never:
        if self.machine_errors:
            raise _MachineUsageError(message)
        super().error(message)


def _emit(payload: dict[str, Any], *, machine: bool) -> None:
    if machine:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return
    if "error" in payload:
        error = payload["error"]
        print(f"error [{error['code']}]: {error['message']}", file=sys.stderr)
        return
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"{key}: {json.dumps(value, ensure_ascii=True)}")
        else:
            print(f"{key}: {value}")


def _add_machine_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        dest="machine",
        help="Emit machine-readable JSON.",
    )


def _parse_rational_time(value: str) -> RationalTime:
    try:
        return RationalTime.from_fraction(Fraction(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise argparse.ArgumentTypeError(
            "time must be exact seconds such as 3, 0.5, or 12000/24000"
        ) from exc


def _parse_mapping(value: str) -> tuple[str, str]:
    key, separator, mapped = value.partition("=")
    if not separator or not key.strip() or not mapped.strip():
        raise argparse.ArgumentTypeError("mapping must use KEY=VALUE")
    return key.strip(), mapped.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = _EngineArgumentParser(prog="video-engine")
    parser.add_argument("--config", type=Path, help="Strict JSON or TOML engine configuration.")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create a canonical project.")
    init.add_argument("directory", type=Path, nargs="?", default=Path.cwd())
    init.add_argument("--name", default="Untitled Project")
    init.add_argument("--width", type=int, default=1920)
    init.add_argument("--height", type=int, default=1080)
    init.add_argument("--fps-num", type=int, default=24)
    init.add_argument("--fps-den", type=int, default=1)
    init.add_argument("--audio-sample-rate", type=int, default=48_000)
    init.add_argument("--force", action="store_true")
    _add_machine_flag(init)

    doctor = subparsers.add_parser("doctor", help="Validate external tools and fonts.")
    doctor.add_argument("--project-root", type=Path, default=Path.cwd())
    doctor.add_argument(
        "--require-extended-graphics",
        action="store_true",
        help="Require the locked Manim and LaTeX release toolchain; Blender remains optional.",
    )
    _add_machine_flag(doctor)

    graphics = subparsers.add_parser(
        "graphics", help="Prepare typed external graphics for canonical timelines."
    )
    graphics_subparsers = graphics.add_subparsers(dest="graphics_command", required=True)
    graphics_prepare = graphics_subparsers.add_parser(
        "prepare", help="Create a strict generator clip and media-reference bundle."
    )
    graphics_renderers = graphics_prepare.add_subparsers(dest="graphics_renderer", required=True)

    def add_graphics_common(command: argparse.ArgumentParser) -> None:
        command.add_argument("source", type=Path)
        command.add_argument("--clip-id", required=True)
        command.add_argument("--start", type=_parse_rational_time, required=True)
        command.add_argument("--duration", type=_parse_rational_time, required=True)
        command.add_argument(
            "--asset",
            type=_parse_mapping,
            action="append",
            default=[],
            metavar="RELATIVE_PATH=SOURCE",
        )
        command.add_argument("--output", type=Path)
        command.add_argument("--opaque", action="store_true")
        _add_machine_flag(command)

    hyperframes = graphics_renderers.add_parser(
        "hyperframes", help="Prepare a confined HyperFrames HTML composition."
    )
    add_graphics_common(hyperframes)
    hyperframes.add_argument("--variables", type=Path, help="JSON object passed as variables.")
    hyperframes.add_argument("--quality", choices=["draft", "standard", "high"], default="high")
    hyperframes.add_argument("--strictness", choices=["strict", "best-effort"], default="strict")
    hyperframes.add_argument("--workers", type=int, default=1)

    manim = graphics_renderers.add_parser("manim", help="Prepare a confined Manim Python scene.")
    add_graphics_common(manim)
    manim.add_argument("--scene", required=True)
    manim.add_argument("--renderer", choices=["cairo", "opengl"], default="cairo")
    manim.add_argument("--seed", type=int, default=0)

    blender = graphics_renderers.add_parser(
        "blender", help="Prepare a confined Blender project scene."
    )
    add_graphics_common(blender)
    blender.add_argument("--scene")
    blender.add_argument("--camera")
    blender.add_argument(
        "--render-engine",
        choices=["BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH", "CYCLES"],
        default="BLENDER_EEVEE_NEXT",
    )
    blender.add_argument("--source-start-frame", type=int, default=1)
    blender.add_argument("--samples", type=int, default=64)

    media = subparsers.add_parser("media", help="Content-addressed media commands.")
    media_subparsers = media.add_subparsers(dest="media_command", required=True)

    media_import = media_subparsers.add_parser("import", help="Import media by SHA-256.")
    media_import.add_argument("sources", type=Path, nargs="+")
    media_import.add_argument("--project-root", type=Path, default=Path.cwd())
    media_import.add_argument("--copy", action="store_true", dest="copy_into_store")
    media_import.add_argument("--no-deep-vfr", action="store_false", dest="deep_vfr")
    _add_machine_flag(media_import)

    media_inspect = media_subparsers.add_parser("inspect", help="Inspect media metadata.")
    media_inspect.add_argument("media")
    media_inspect.add_argument("--project-root", type=Path, default=Path.cwd())
    media_inspect.add_argument("--no-deep-vfr", action="store_false", dest="deep_vfr")
    _add_machine_flag(media_inspect)

    media_proxy = media_subparsers.add_parser("proxy", help="Generate a cached proxy.")
    media_proxy.add_argument("media_id")
    media_proxy.add_argument("--project-root", type=Path, default=Path.cwd())
    media_proxy.add_argument("--width", type=int, default=1280)
    media_proxy.add_argument("--height", type=int, default=720)
    media_proxy.add_argument("--crf", type=int, default=28)
    _add_machine_flag(media_proxy)

    media_thumbnails = media_subparsers.add_parser("thumbnails", help="Generate cached thumbnails.")
    media_thumbnails.add_argument("media_id")
    media_thumbnails.add_argument("--project-root", type=Path, default=Path.cwd())
    media_thumbnails.add_argument("--count", type=int, default=12)
    media_thumbnails.add_argument("--width", type=int, default=320)
    _add_machine_flag(media_thumbnails)

    media_waveform = media_subparsers.add_parser("waveform", help="Generate a cached waveform.")
    media_waveform.add_argument("media_id")
    media_waveform.add_argument("--project-root", type=Path, default=Path.cwd())
    media_waveform.add_argument("--width", type=int, default=1600)
    media_waveform.add_argument("--height", type=int, default=320)
    _add_machine_flag(media_waveform)

    project = subparsers.add_parser("project", help="Canonical project commands.")
    project_subparsers = project.add_subparsers(dest="project_command", required=True)
    validate = project_subparsers.add_parser("validate", help="Validate schema and invariants.")
    validate.add_argument("project", type=Path, nargs="?", default=Path("project.json"))
    _add_machine_flag(validate)

    timeline = subparsers.add_parser("timeline", help="Canonical timeline commands.")
    timeline_subparsers = timeline.add_subparsers(dest="timeline_command", required=True)

    timeline_inspect = timeline_subparsers.add_parser(
        "inspect", help="Inspect tracks, items, transitions, and markers."
    )
    timeline_inspect.add_argument("project", type=Path, nargs="?", default=Path("project.json"))
    timeline_inspect.add_argument("--sequence-id")
    timeline_inspect.add_argument("--output-dir", type=Path)
    _add_machine_flag(timeline_inspect)

    apply_patch = timeline_subparsers.add_parser(
        "apply-patch", help="Atomically apply a strict JSON timeline patch."
    )
    apply_patch.add_argument("project", type=Path)
    apply_patch.add_argument("patch", type=Path)
    apply_patch.add_argument("--output", type=Path)
    _add_machine_flag(apply_patch)

    inspect = subparsers.add_parser("inspect", help="Generate canonical inspection artifacts.")
    inspect_subparsers = inspect.add_subparsers(dest="inspect_kind", required=True)
    for kind in InspectionKind:
        command = inspect_subparsers.add_parser(
            kind.value, help=f"Inspect a canonical {kind.value} view."
        )
        command.add_argument("project", type=Path, nargs="?", default=Path("project.json"))
        if kind in {InspectionKind.RANGE, InspectionKind.CUT, InspectionKind.AUDIO}:
            command.add_argument("media", type=Path)
        command.add_argument("--sequence-id")
        command.add_argument("--output-dir", type=Path)
        if kind is InspectionKind.RANGE:
            command.add_argument("--start", type=_parse_rational_time, required=True)
            command.add_argument("--duration", type=_parse_rational_time, required=True)
        elif kind is InspectionKind.CUT:
            command.add_argument("--at", type=_parse_rational_time, required=True)
            command.add_argument(
                "--window",
                type=_parse_rational_time,
                default=RationalTime(value=2, timescale=1),
            )
        elif kind in {InspectionKind.AUDIO, InspectionKind.CAPTIONS}:
            command.add_argument("--start", type=_parse_rational_time)
            command.add_argument("--duration", type=_parse_rational_time)
        if kind in {InspectionKind.RANGE, InspectionKind.CUT}:
            command.add_argument("--frames", type=int, default=12)
        if kind is InspectionKind.TIMELINE:
            command.add_argument("--page-duration", type=_parse_rational_time)
            command.add_argument("--max-lanes", type=int, default=20)
        if kind in {InspectionKind.RANGE, InspectionKind.CUT, InspectionKind.AUDIO}:
            command.add_argument("--waveform-width", type=int, default=1600)
            command.add_argument("--waveform-height", type=int, default=320)
            command.add_argument("--peak-buckets", type=int, default=1000)
        _add_machine_flag(command)

    render = subparsers.add_parser("render", help="Compile and execute a canonical render.")
    render_subparsers = render.add_subparsers(dest="render_command", required=True)
    for mode in ("draft", "preview", "range", "final"):
        render_mode = render_subparsers.add_parser(mode, help=f"Render the {mode} delivery mode.")
        render_mode.add_argument("project", type=Path)
        render_mode.add_argument("output", type=Path)
        render_mode.add_argument("--sequence-id")
        render_mode.add_argument("--profile-id")
        render_mode.add_argument("--start", type=_parse_rational_time)
        render_mode.add_argument("--duration", type=_parse_rational_time)
        render_mode.add_argument(
            "--chapter-id",
            help="Render the range beginning at this canonical chapter marker.",
        )
        render_mode.add_argument(
            "--section-duration",
            type=_parse_rational_time,
            help="Maximum independently cacheable section duration in exact seconds.",
        )
        render_mode.add_argument(
            "--no-sectioning",
            action="store_false",
            dest="sectioning",
            help="Compile the requested range as one section.",
        )
        render_mode.add_argument(
            "--caption-track",
            action="append",
            dest="caption_track_ids",
            help="Burn one enabled caption track; repeat to select multiple tracks.",
        )
        render_mode.add_argument(
            "--caption-language",
            action="append",
            dest="caption_languages",
            help="Burn caption tracks in this language across nested sequences.",
        )
        render_mode.add_argument("--no-cache", action="store_false", dest="use_cache")
        render_mode.add_argument("--no-resume", action="store_false", dest="resume")
        render_mode.add_argument(
            "--approval",
            type=Path,
            help="Human-reviewed QC approval artifact required by final renders.",
        )
        _add_machine_flag(render_mode)

    qc = subparsers.add_parser(
        "qc", help="Run technical ingest, timeline, output, and delivery QC."
    )
    qc.add_argument("project", type=Path, nargs="?", default=Path("project.json"))
    qc.add_argument("--output", type=Path)
    qc.add_argument("--sequence-id")
    qc.add_argument("--profile-id")
    qc.add_argument(
        "--scope",
        action="append",
        choices=[scope.value for scope in QCScope],
        dest="scopes",
        help="Run one QC scope; repeat to select multiple scopes.",
    )
    qc.add_argument("--report-dir", type=Path)
    qc.add_argument("--expected-sha256")
    qc.add_argument("--caption-sidecar", type=Path, action="append", default=[])
    qc.add_argument("--fail-on-warnings", action="store_true")
    qc.add_argument("--strict-black", action="store_true")
    qc.add_argument("--strict-freeze", action="store_true")
    qc.add_argument("--strict-silence", action="store_true")
    qc.add_argument("--strict-gaps", action="store_true")
    qc.add_argument("--no-source-decode", action="store_false", dest="decode_all_sources")
    qc.add_argument("--no-contact-sheet", action="store_false", dest="generate_contact_sheet")
    qc.add_argument("--approve-by")
    qc.add_argument("--approval-notes")
    qc.add_argument("--approval-output", type=Path)
    _add_machine_flag(qc)

    migrate = subparsers.add_parser("migrate", help="Import legacy timelines.")
    migrate_subparsers = migrate.add_subparsers(dest="migrate_command", required=True)
    for command_name in ("legacy-edl", "faceless", "cmx", "fcpxml", "otio"):
        command = migrate_subparsers.add_parser(
            command_name, help=f"Import a {command_name} timeline."
        )
        command.add_argument("source", type=Path)
        command.add_argument("--project-root", type=Path)
        command.add_argument("--output", type=Path)
        command.add_argument("--report", type=Path)
        command.add_argument("--name")
        if command_name == "faceless":
            command.add_argument("--voiceover", type=Path)
            command.add_argument("--captions", type=Path)
            command.add_argument("--rich-captions", type=Path)
        if command_name in {"cmx", "otio"}:
            command.add_argument("--fps-num", type=int)
            command.add_argument("--fps-den", type=int, default=1)
        if command_name in {"cmx", "fcpxml"}:
            command.add_argument(
                "--media",
                type=_parse_mapping,
                action="append",
                default=[],
                metavar="RESOURCE=PATH",
            )
        if command_name == "cmx":
            command.add_argument(
                "--source-timecode",
                type=_parse_mapping,
                action="append",
                default=[],
                metavar="REEL=HH:MM:SS:FF",
            )
        if command_name == "otio":
            command.add_argument("--width", type=int, default=1920)
            command.add_argument("--height", type=int, default=1080)
        _add_machine_flag(command)

    export = subparsers.add_parser(
        "export", help="Export a canonical project or selected timeline data."
    )
    export.add_argument("project", type=Path)
    export.add_argument("output", type=Path)
    export.add_argument("--format", choices=[item.value for item in ExportFormat])
    export.add_argument("--sequence-id")
    export.add_argument("--caption-track")
    _add_machine_flag(export)
    return parser


def _load_config(path: Path | None) -> EngineConfig:
    return EngineConfig.from_file(path) if path is not None else EngineConfig()


def _run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    config = _load_config(args.config)
    if args.log_level:
        config.log_level = args.log_level
    configure_logging(config.log_level, json_output=bool(getattr(args, "machine", False)))

    if args.command == "init":
        directory = args.directory.resolve()
        project_path = directory / "project.json"
        if project_path.exists() and not args.force:
            raise EngineError(
                ErrorCode.STORAGE,
                "project.json already exists; pass --force to replace it",
                context={"path": str(project_path)},
            )
        engine = VideoEngine(directory, config)
        project = engine.create_project(
            args.name,
            width=args.width,
            height=args.height,
            frame_rate=FrameRate(numerator=args.fps_num, denominator=args.fps_den),
            audio_sample_rate=args.audio_sample_rate,
        )
        engine.save_project(project, project_path)
        for relative in ("media", "proxies", "cache", "renders", "reports"):
            (directory / relative).mkdir(parents=True, exist_ok=True)
        return {
            "ok": True,
            "project": str(project_path),
            "project_id": project.id,
            "schema_version": project.schema_version,
        }, 0

    if args.command == "doctor":
        doctor_report = VideoEngine(args.project_root, config).doctor(
            require_extended_graphics=args.require_extended_graphics
        )
        return {
            "ok": doctor_report.healthy,
            "summary": doctor_report.summary(),
            "checks": doctor_report.model_dump(mode="json")["checks"],
        }, (0 if doctor_report.healthy else 2)

    if args.command == "graphics" and args.graphics_command == "prepare":
        source = args.source.resolve()
        assets = {relative: Path(path).resolve() for relative, path in args.asset}
        graphic_range = TimeRange(start=args.start, duration=args.duration)
        engine = VideoEngine(source.parent, config)
        graphics = engine.graphics()
        if args.graphics_renderer == "hyperframes":
            variables: dict[str, Any] = {}
            if args.variables is not None:
                try:
                    loaded_variables = json.loads(args.variables.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise EngineError(
                        ErrorCode.STORAGE,
                        "failed to load HyperFrames variables",
                        context={"path": str(args.variables), "detail": str(exc)},
                    ) from exc
                if not isinstance(loaded_variables, dict):
                    raise EngineError(
                        ErrorCode.CONFIGURATION,
                        "HyperFrames variables must be a JSON object",
                        context={"path": str(args.variables)},
                    )
                variables = loaded_variables
            prepared = graphics.prepare_hyperframes(
                clip_id=args.clip_id,
                timeline_range=graphic_range,
                entry_path=source,
                asset_bindings=assets,
                variables=variables,
                quality=args.quality,
                strictness=args.strictness,
                workers=args.workers,
                transparent=not args.opaque,
            )
        elif args.graphics_renderer == "manim":
            prepared = graphics.prepare_manim(
                clip_id=args.clip_id,
                timeline_range=graphic_range,
                script_path=source,
                scene_name=args.scene,
                asset_bindings=assets,
                renderer=args.renderer,
                seed=args.seed,
                transparent=not args.opaque,
            )
        else:
            prepared = graphics.prepare_blender(
                clip_id=args.clip_id,
                timeline_range=graphic_range,
                blend_path=source,
                asset_bindings=assets,
                scene_name=args.scene,
                camera_name=args.camera,
                render_engine=args.render_engine,
                source_start_frame=args.source_start_frame,
                samples=args.samples,
                transparent=not args.opaque,
            )
        payload = prepared.model_dump(mode="json")
        if args.output is not None:
            destination = args.output.resolve()
            atomic_write_text(destination, json.dumps(payload, indent=2) + "\n")
        else:
            destination = None
        return {
            "ok": True,
            "renderer": args.graphics_renderer,
            "output": str(destination) if destination is not None else None,
            "prepared_graphic": payload,
        }, 0

    if args.command == "media":
        engine = VideoEngine(args.project_root, config)
        service = engine.media()
        if args.media_command == "import":
            records = [
                service.import_media(
                    source,
                    copy_into_store=args.copy_into_store,
                    deep_vfr=args.deep_vfr,
                )
                for source in args.sources
            ]
            return {
                "ok": True,
                "media": [record.model_dump(mode="json") for record in records],
            }, 0
        if args.media_command == "inspect":
            record = service.inspect(args.media, deep_vfr=args.deep_vfr)
            validation = service.validate_source(record.id)
            return {
                "ok": validation.valid,
                "media": record.model_dump(mode="json"),
                "validation": validation.model_dump(mode="json"),
            }, (0 if validation.valid else 2)
        if args.media_command == "proxy":
            asset = service.proxy(
                args.media_id,
                width=args.width,
                height=args.height,
                crf=args.crf,
            )
            return {"ok": True, "derived_asset": asset.model_dump(mode="json")}, 0
        if args.media_command == "thumbnails":
            asset = service.thumbnails(args.media_id, count=args.count, width=args.width)
            return {"ok": True, "derived_asset": asset.model_dump(mode="json")}, 0
        if args.media_command == "waveform":
            asset = service.waveform(args.media_id, width=args.width, height=args.height)
            return {"ok": True, "derived_asset": asset.model_dump(mode="json")}, 0

    if args.command == "project" and args.project_command == "validate":
        project_path = args.project.resolve()
        engine = VideoEngine(project_path.parent, config)
        project, migrations = engine.load_project(project_path)
        validation_report = engine.validate_project(project)
        return {
            "ok": validation_report.valid,
            "project": str(project_path),
            "schema_version": project.schema_version,
            "revision": project.revision,
            "migrations": migrations,
            "issues": validation_report.model_dump(mode="json")["issues"],
        }, 0

    if args.command == "timeline":
        project_path = args.project.resolve()
        engine = VideoEngine(project_path.parent, config)
        project, migrations = engine.load_project(project_path)
        if args.timeline_command == "inspect":
            sequence_id = args.sequence_id or project.active_sequence_id
            try:
                sequence = project.sequence(sequence_id)
            except StopIteration as exc:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "sequence was not found",
                    context={"sequence_id": sequence_id},
                ) from exc
            compatibility_inspection = engine.inspection(project).inspect(
                InspectionRequest(
                    kind=InspectionKind.TIMELINE,
                    sequence_id=sequence_id,
                    output_dir=(args.output_dir.resolve() if args.output_dir is not None else None),
                )
            )
            return {
                "ok": True,
                "project": str(project_path),
                "project_revision": project.revision,
                "migrations": migrations,
                "sequence": {
                    "id": sequence.id,
                    "name": sequence.name,
                    "revision": sequence.revision,
                    "duration": sequence.timeline.duration.model_dump(mode="json"),
                    "markers": [
                        marker.model_dump(mode="json") for marker in sequence.timeline.markers
                    ],
                    "tracks": [
                        {
                            "id": track.id,
                            "name": track.name,
                            "track_type": track.track_type,
                            "enabled": track.enabled,
                            "locked": track.locked,
                            "items": [item.model_dump(mode="json") for item in track.items],
                            "transitions": [
                                transition.model_dump(mode="json")
                                for transition in getattr(track, "transitions", [])
                            ],
                        }
                        for track in sequence.timeline.tracks
                    ],
                },
                "inspection": {
                    "output_dir": str(compatibility_inspection.output_dir),
                    "report_json": str(compatibility_inspection.report_json),
                    "report_markdown": str(compatibility_inspection.report_markdown),
                    "artifacts": [
                        artifact.model_dump(mode="json")
                        for artifact in compatibility_inspection.artifacts
                    ],
                },
            }, 0
        if args.timeline_command == "apply-patch":
            try:
                payload = json.loads(args.patch.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise EngineError(
                    ErrorCode.STORAGE,
                    "failed to load timeline patch",
                    context={"path": str(args.patch), "detail": str(exc)},
                ) from exc
            if isinstance(payload, dict) and "patch_id" in payload:
                payload = {"patch": payload}
            envelope = PatchEnvelope.model_validate(payload)
            editor = engine.editor(project)
            result = editor.apply_patch(envelope.patch)
            destination = (args.output or project_path).resolve()
            engine.save_project(editor.project, destination)
            return {
                "ok": True,
                "project": str(destination),
                "project_revision": result.project_revision,
                "sequence_id": result.sequence_id,
                "migrations": migrations,
                "audit_entries": [entry.model_dump(mode="json") for entry in result.audit_entries],
                "inverse_patch": result.inverse_patch.model_dump(mode="json"),
            }, 0

    if args.command == "inspect":
        project_path = args.project.resolve()
        engine = VideoEngine(project_path.parent, config)
        project, migrations = engine.load_project(project_path)
        kind = InspectionKind(args.inspect_kind)
        start = getattr(args, "start", None)
        duration = getattr(args, "duration", None)
        if (start is None) != (duration is None):
            raise EngineError(
                ErrorCode.CONFIGURATION,
                "inspection start and duration must be provided together",
            )
        selected_range = (
            TimeRange(start=start, duration=duration)
            if start is not None and duration is not None
            else None
        )
        inspection_request = InspectionRequest(
            kind=kind,
            sequence_id=args.sequence_id,
            media_path=(args.media.resolve() if hasattr(args, "media") else None),
            timeline_range=selected_range,
            cut_time=getattr(args, "at", None),
            cut_window=getattr(args, "window", RationalTime(value=2, timescale=1)),
            output_dir=(args.output_dir.resolve() if args.output_dir is not None else None),
            frame_count=getattr(args, "frames", 12),
            waveform_width=getattr(args, "waveform_width", 1600),
            waveform_height=getattr(args, "waveform_height", 320),
            peak_buckets=getattr(args, "peak_buckets", 1000),
            timeline_page_duration=(
                args.page_duration
                if getattr(args, "page_duration", None) is not None
                else RationalTime(value=300, timescale=1)
            ),
            max_lanes_per_page=getattr(args, "max_lanes", 20),
        )
        inspection_result = engine.inspection(project).inspect(inspection_request)
        return {
            "ok": True,
            "project": str(project_path),
            "migrations": migrations,
            "inspection_id": inspection_result.inspection_id,
            "kind": inspection_result.kind,
            "status": inspection_result.status,
            "output_dir": str(inspection_result.output_dir),
            "report_json": str(inspection_result.report_json),
            "report_markdown": str(inspection_result.report_markdown),
            "summary": inspection_result.summary,
            "warnings": list(inspection_result.warnings),
            "artifacts": [
                artifact.model_dump(mode="json") for artifact in inspection_result.artifacts
            ],
        }, 0

    if args.command == "render":
        project_path = args.project.resolve()
        engine = VideoEngine(project_path.parent, config)
        project, migrations = engine.load_project(project_path)
        if (args.start is None) != (args.duration is None):
            raise EngineError(
                ErrorCode.CONFIGURATION,
                "render start and duration must be provided together",
            )
        timeline_range = (
            TimeRange(start=args.start, duration=args.duration)
            if args.start is not None and args.duration is not None
            else None
        )
        mode = RenderMode(args.render_command)
        request = RenderRequest(
            output_path=args.output.resolve(),
            mode=mode,
            sequence_id=args.sequence_id,
            delivery_profile_id=args.profile_id,
            timeline_range=timeline_range,
            chapter_id=args.chapter_id,
            sectioning=args.sectioning,
            section_duration=args.section_duration,
            caption_track_ids=(
                tuple(args.caption_track_ids) if args.caption_track_ids is not None else None
            ),
            caption_languages=(
                tuple(args.caption_languages) if args.caption_languages is not None else None
            ),
            use_cache=args.use_cache,
            resume=args.resume,
            qc_approval_path=(args.approval.resolve() if args.approval else None),
        )
        render_result = engine.renderer(project).render(request)
        return {
            "ok": True,
            "project": str(project_path),
            "migrations": migrations,
            "output": str(render_result.output_path),
            "manifest": str(render_result.manifest_path),
            "render_id": render_result.manifest.render_id,
            "graph_hash": render_result.manifest.graph_hash,
            "output_sha256": render_result.manifest.output_sha256,
            "cache_hits": render_result.cache_hits,
            "executed_nodes": render_result.executed_nodes,
            "sections": render_result.manifest.metadata.get("sections", []),
        }, 0

    if args.command == "qc":
        project_path = args.project.resolve()
        engine = VideoEngine(project_path.parent, config)
        project, migrations = engine.load_project(project_path)
        scopes = (
            tuple(QCScope(value) for value in args.scopes)
            if args.scopes is not None
            else (tuple(QCScope) if args.output is not None else (QCScope.INGEST, QCScope.TIMELINE))
        )
        policy = QCPolicy(
            fail_on_warnings=args.fail_on_warnings,
            black_is_blocking=args.strict_black,
            freeze_is_blocking=args.strict_freeze,
            unexpected_silence_is_blocking=args.strict_silence,
            implicit_blank_is_blocking=args.strict_gaps,
            decode_all_sources=args.decode_all_sources,
            generate_contact_sheet=args.generate_contact_sheet,
        )
        qc_request = QCRequest(
            output_path=args.output.resolve() if args.output is not None else None,
            sequence_id=args.sequence_id,
            delivery_profile_id=args.profile_id,
            scopes=scopes,
            report_dir=args.report_dir.resolve() if args.report_dir is not None else None,
            expected_output_sha256=args.expected_sha256,
            expected_caption_paths=tuple(args.caption_sidecar),
            policy=policy,
        )
        qc_result = engine.qc(project).run(qc_request)
        acceptable = {
            QCOverallStatus.PASSED,
            QCOverallStatus.PASSED_WITH_WARNINGS,
        }
        approval_payload: dict[str, Any] | None = None
        if args.approve_by is not None or args.approval_notes is not None:
            if args.approve_by is None or args.approval_notes is None:
                raise EngineError(
                    ErrorCode.CONFIGURATION,
                    "--approve-by and --approval-notes must be provided together",
                )
            approval, approval_path = engine.approvals().create(
                qc_result,
                reviewed_by=args.approve_by,
                notes=args.approval_notes,
                path=(args.approval_output.resolve() if args.approval_output is not None else None),
            )
            approval_payload = {
                "path": str(approval_path),
                "approval": approval.model_dump(mode="json"),
            }
        return {
            "ok": qc_result.report.status in acceptable,
            "project": str(project_path),
            "migrations": migrations,
            "run_id": qc_result.report.run_id,
            "status": qc_result.report.status,
            "report_json": str(qc_result.json_path),
            "report_markdown": str(qc_result.markdown_path),
            "output_sha256": qc_result.report.output_sha256,
            "checks": [check.model_dump(mode="json") for check in qc_result.report.checks],
            "findings": [finding.model_dump(mode="json") for finding in qc_result.report.findings],
            "evidence": [
                artifact.model_dump(mode="json") for artifact in qc_result.report.evidence
            ],
            "approval": approval_payload,
        }, (0 if qc_result.report.status in acceptable else 2)

    if args.command == "migrate":
        source = args.source.resolve()
        source_parent = source if source.is_dir() else source.parent
        destination = (args.output or source_parent / "canonical-project.json").resolve()
        project_root = (args.project_root or destination.parent).resolve()
        engine = VideoEngine(project_root, config)
        if args.migrate_command == "legacy-edl":
            migration = engine.adapters().import_legacy_edl(source, name=args.name)
        elif args.migrate_command == "faceless":
            migration = engine.adapters().import_faceless(
                source,
                name=args.name,
                voiceover=(args.voiceover.resolve() if args.voiceover else None),
                captions=(args.captions.resolve() if args.captions else None),
                rich_captions=(args.rich_captions.resolve() if args.rich_captions else None),
            )
        elif args.migrate_command == "cmx":
            frame_rate = (
                FrameRate(numerator=args.fps_num, denominator=args.fps_den)
                if args.fps_num is not None
                else None
            )
            migration = engine.adapters().import_cmx(
                source,
                frame_rate=frame_rate,
                name=args.name,
                media_paths={key: Path(value).resolve() for key, value in args.media},
                source_timecodes=dict(args.source_timecode),
            )
        elif args.migrate_command == "fcpxml":
            migration = engine.adapters().import_fcpxml(
                source,
                name=args.name,
                media_paths={key: Path(value).resolve() for key, value in args.media},
            )
        else:
            frame_rate = (
                FrameRate(numerator=args.fps_num, denominator=args.fps_den)
                if args.fps_num is not None
                else None
            )
            migration = engine.adapters().import_otio(
                source,
                frame_rate=frame_rate,
                name=args.name,
                width=args.width,
                height=args.height,
            )
        engine.save_project(migration.project, destination)
        report_path = (
            args.report.resolve()
            if args.report is not None
            else destination.with_suffix(".migration.json")
        )
        atomic_write_text(report_path, migration.report.model_dump_json(indent=2) + "\n")
        return {
            "ok": migration.report.valid,
            "adapter": migration.report.adapter,
            "project": str(destination),
            "project_id": migration.project.id,
            "report": str(report_path),
            "source_sha256": migration.report.source_sha256,
            "sidecar_sha256": migration.report.sidecar_sha256,
            "issues": [issue.model_dump(mode="json") for issue in migration.report.issues],
        }, (0 if migration.report.valid else 2)

    if args.command == "export":
        project_path = args.project.resolve()
        engine = VideoEngine(project_path.parent, config)
        project, migrations = engine.load_project(project_path)
        export_result = engine.exporter().export(
            project,
            args.output,
            format=args.format,
            sequence_id=args.sequence_id,
            caption_track_id=args.caption_track,
        )
        return {
            "ok": True,
            "project": str(project_path),
            "migrations": migrations,
            "output": str(export_result.path),
            "format": export_result.format,
            "issues": [issue.model_dump(mode="json") for issue in export_result.issues],
            "metadata": export_result.metadata,
        }, 0

    raise AssertionError("unreachable command")


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else sys.argv[1:]
    _EngineArgumentParser.machine_errors = "--json" in arguments
    parser = build_parser()
    try:
        args = parser.parse_args(arguments)
    except _MachineUsageError as exc:
        _emit(
            {
                "error": {
                    "code": ErrorCode.CONFIGURATION.value,
                    "message": "invalid command-line arguments",
                    "context": {"detail": str(exc)},
                }
            },
            machine=True,
        )
        return 2
    machine = bool(getattr(args, "machine", False))
    try:
        payload, return_code = _run(args)
    except EngineError as exc:
        payload, return_code = exc.to_dict(), 2
    except ValidationError as exc:
        payload, return_code = (
            {
                "error": {
                    "code": ErrorCode.INVALID_PROJECT.value,
                    "message": "schema validation failed",
                    "context": {"errors": exc.errors()},
                }
            },
            2,
        )
    _emit(payload, machine=machine)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
