"""Maintained scene detection with exact frame-to-rational conversion."""

from __future__ import annotations

from pathlib import Path

from editorial_brain.core.models import Confidence, EvidenceKind, EvidenceRef, ShotBoundary
from video_engine.api import FrameRate, RationalTime, TimeRange


def detect_shot_ranges(
    path: Path,
    *,
    media_id: str,
    media_sha256: str,
    frame_rate: FrameRate,
    available_range: TimeRange,
    threshold: float = 27.0,
    minimum_scene_frames: int = 6,
    analysis_version: str = "shots-pyscenedetect-v1",
) -> tuple[list[TimeRange], list[ShotBoundary], list[EvidenceRef]]:
    try:
        from scenedetect import (  # type: ignore[import-untyped]
            ContentDetector,
            SceneManager,
            open_video,
        )
    except ImportError as exc:
        raise RuntimeError(
            "shot detection requires the brain-analysis optional dependencies"
        ) from exc
    if not path.is_file():
        raise FileNotFoundError(path)
    video = open_video(str(path))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=minimum_scene_frames))
    manager.detect_scenes(video, show_progress=False)
    scene_list = manager.get_scene_list(start_in_scene=True)
    source_zero = available_range.start
    ranges: list[TimeRange] = []
    boundaries: list[ShotBoundary] = []
    evidence: list[EvidenceRef] = []
    for position, (start, end) in enumerate(scene_list):
        start_time = source_zero + frame_rate.frames_to_time(start.frame_num)
        end_time = min(source_zero + frame_rate.frames_to_time(end.frame_num), available_range.end)
        if end_time <= start_time:
            continue
        source_range = TimeRange.from_start_end(start_time, end_time)
        ranges.append(source_range)
        evidence_id = f"evidence:{media_id}:shot-boundary:{position:06d}"
        ref = EvidenceRef(
            id=evidence_id,
            kind=EvidenceKind.MEASURED,
            media_id=media_id,
            media_sha256=media_sha256,
            source_range=TimeRange(start=start_time, duration=frame_rate.frame_duration),
            analysis_version=analysis_version,
            confidence=Confidence(
                score=1,
                basis=EvidenceKind.MEASURED,
                calibration="detector_boundary",
            ),
            summary="PySceneDetect content boundary",
        )
        evidence.append(ref)
        boundaries.append(
            ShotBoundary(
                id=f"boundary:{media_id}:{position:06d}",
                media_id=media_id,
                time=start_time,
                kind="source_start" if position == 0 else "hard_cut",
                strength=1,
                evidence=[ref],
            )
        )
    if not ranges:
        raise ValueError("shot detector returned no positive scene ranges")
    end_ref = EvidenceRef(
        id=f"evidence:{media_id}:source-end",
        kind=EvidenceKind.MEASURED,
        media_id=media_id,
        media_sha256=media_sha256,
        source_range=TimeRange(start=available_range.end, duration=RationalTime.zero()),
        analysis_version=analysis_version,
        confidence=Confidence(score=1, basis=EvidenceKind.MEASURED, calibration="source_range"),
        summary="canonical available range end",
    )
    evidence.append(end_ref)
    boundaries.append(
        ShotBoundary(
            id=f"boundary:{media_id}:source-end",
            media_id=media_id,
            time=available_range.end,
            kind="source_end",
            strength=1,
            evidence=[end_ref],
        )
    )
    return ranges, boundaries, evidence


def subshot_ranges(
    source_range: TimeRange,
    structural_times: list[RationalTime],
    *,
    minimum_duration: RationalTime,
) -> list[TimeRange]:
    times = sorted(
        {time for time in structural_times if source_range.start < time < source_range.end}
    )
    ranges: list[TimeRange] = []
    start = source_range.start
    for boundary in [*times, source_range.end]:
        if boundary - start >= minimum_duration:
            ranges.append(TimeRange.from_start_end(start, boundary))
            start = boundary
    if start < source_range.end:
        if ranges:
            ranges[-1] = TimeRange.from_start_end(ranges[-1].start, source_range.end)
        else:
            ranges.append(source_range)
    return ranges
