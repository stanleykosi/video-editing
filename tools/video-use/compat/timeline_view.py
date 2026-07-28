"""Compatibility entrypoint for canonical timeline and range inspection.

New callers should use ``video-engine inspect``. This module preserves the
historical range command while delegating all media analysis and image creation
to :class:`video_engine.inspection.InspectionService`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from video_engine.api.engine import VideoEngine  # noqa: E402
from video_engine.core.schema import CaptionCue, CaptionTrack, Clip, VideoTrack  # noqa: E402
from video_engine.core.time import RationalTime, TimeRange  # noqa: E402
from video_engine.inspection.models import (  # noqa: E402
    InspectionArtifact,
    InspectionKind,
    InspectionRequest,
)

ENTRYPOINT_PATH = Path(__file__).resolve()


def _time(value: float) -> RationalTime:
    return RationalTime.from_fraction(Fraction(str(value)))


def _caption_track(path: Path | None) -> CaptionTrack | None:
    if path is None or not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_words = payload.get("words", []) if isinstance(payload, dict) else []
    cues: list[CaptionCue] = []
    for index, raw in enumerate(raw_words):
        if not isinstance(raw, dict) or raw.get("type", "word") != "word":
            continue
        text = str(raw.get("text") or "").strip()
        try:
            start = _time(float(raw["start"]))
            end = _time(float(raw["end"]))
        except (KeyError, TypeError, ValueError):
            continue
        if not text or end <= start:
            continue
        cues.append(
            CaptionCue(
                id=f"transcript-word-{index + 1}",
                text=text,
                timeline_range=TimeRange(start=start, duration=end - start),
            )
        )
    return (
        CaptionTrack(id="transcript-words", name="Transcript words", items=cues) if cues else None
    )


def _artifact(result: Any, kind: str) -> InspectionArtifact:
    try:
        return next(artifact for artifact in result.artifacts if artifact.kind == kind)
    except StopIteration as exc:
        raise SystemExit(f"canonical inspection did not produce {kind}") from exc


def _publish(result: Any, artifact: InspectionArtifact, output: Path) -> int:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if artifact.path.resolve() != output:
        shutil.copy2(artifact.path, output)
    print(
        json.dumps(
            {
                "ok": True,
                "deprecated_entrypoint": str(ENTRYPOINT_PATH),
                "canonical_command": f"video-engine inspect {result.kind.value}",
                "output": str(output),
                "inspection_report": str(result.report_json),
                "inspection_markdown": str(result.report_markdown),
                "artifacts": [item.model_dump(mode="json") for item in result.artifacts],
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    return 0


def _range(args: argparse.Namespace) -> int:
    if args.video is None or args.start is None or args.end is None:
        raise SystemExit("video, start, and end are required")
    video = args.video.resolve()
    if not video.is_file():
        raise SystemExit(f"video not found: {video}")
    if args.end <= args.start:
        raise SystemExit("end must be greater than start")
    output = (
        args.output.resolve()
        if args.output is not None
        else video.parent / "edit" / "verify" / f"{video.stem}_{args.start:.2f}-{args.end:.2f}.png"
    )
    output_dir = output.parent / f"{output.stem}.inspection"
    engine = VideoEngine(output_dir)
    record = engine.media().import_media(video)
    if not record.probe.video_streams or record.probe.duration is None:
        raise SystemExit("inspection source requires a video stream with a known duration")
    stream = record.probe.video_streams[0]
    rate = stream.average_frame_rate
    if rate is None or stream.width is None or stream.height is None:
        raise SystemExit("inspection source is missing frame rate or dimensions")
    selected = TimeRange(start=_time(args.start), duration=_time(args.end - args.start))
    if selected.end > record.probe.duration:
        raise SystemExit("requested inspection range exceeds media duration")
    project = engine.create_project(
        f"Inspection: {video.name}",
        width=stream.width,
        height=stream.height,
        frame_rate=rate,
    )
    project.media.append(engine.media().to_media_reference(record))
    project.sequence().timeline.tracks.append(
        VideoTrack(
            id="inspection-video",
            name="Rendered output",
            items=[
                Clip(
                    id="inspection-source",
                    media_reference_id=record.id,
                    timeline_range=TimeRange(
                        start=RationalTime.zero(), duration=record.probe.duration
                    ),
                    source_range=TimeRange(
                        start=RationalTime.zero(), duration=record.probe.duration
                    ),
                    source_audio_enabled=bool(record.probe.audio_streams),
                )
            ],
        )
    )
    transcript = args.transcript
    if transcript is None:
        candidate = video.parent / "edit" / "transcripts" / f"{video.stem}.json"
        transcript = candidate if candidate.is_file() else None
    captions = _caption_track(transcript)
    if captions is not None:
        project.sequence().timeline.tracks.append(captions)
    result = engine.inspection(project).inspect(
        InspectionRequest(
            kind=InspectionKind.RANGE,
            media_path=video,
            timeline_range=selected,
            output_dir=output_dir,
            frame_count=args.n_frames,
        )
    )
    return _publish(result, _artifact(result, "inspection_contact_sheet"), output)


def _timeline(args: argparse.Namespace) -> int:
    source = args.edl.resolve()
    if not source.is_file():
        raise SystemExit(f"EDL not found: {source}")
    output = (
        args.output.resolve()
        if args.output is not None
        else source.parent / "edit" / "verify" / f"{source.stem}_timeline.png"
    )
    output_dir = output.parent / f"{output.stem}.inspection"
    engine = VideoEngine(output_dir)
    migration = engine.adapters().import_legacy_edl(source)
    result = engine.inspection(migration.project).inspect(
        InspectionRequest(kind=InspectionKind.TIMELINE, output_dir=output_dir)
    )
    return _publish(result, _artifact(result, "timeline_map"), output)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect a video range through the canonical VideoEngine"
    )
    parser.add_argument("video", type=Path, nargs="?", help="source or rendered video")
    parser.add_argument("start", type=float, nargs="?", help="range start in seconds")
    parser.add_argument("end", type=float, nargs="?", help="range end in seconds")
    parser.add_argument("-o", "--output", type=Path, help="published contact-sheet PNG")
    parser.add_argument("--n-frames", type=int, default=10, choices=range(1, 101))
    parser.add_argument("--transcript", type=Path, help="word-timed transcript JSON")
    parser.add_argument("--edl", type=Path, help="inspect an existing-footage EDL timeline")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return _timeline(args) if args.edl is not None else _range(args)


if __name__ == "__main__":
    raise SystemExit(main())
