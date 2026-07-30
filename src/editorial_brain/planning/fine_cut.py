"""Fine-cut refinement restricted to verified structural cut candidates."""

from __future__ import annotations

from typing import Literal

from editorial_brain.core.models import (
    CandidateAssembly,
    CutPointCandidate,
    MediaUnderstandingIndex,
    PauseEvent,
    PlannedSegment,
    Transcript,
)
from editorial_brain.cuts.boundaries import boundary_rejections
from video_engine.api import RationalTime, TimeRange


def refine_assembly(
    assembly: CandidateAssembly,
    points: list[CutPointCandidate],
    index: MediaUnderstandingIndex,
) -> CandidateAssembly:
    by_media: dict[str, list[CutPointCandidate]] = {}
    for point in points:
        by_media.setdefault(point.media_id, []).append(point)
    cursor = assembly.segments[0].timeline_range.start
    refined: list[PlannedSegment] = []
    for segment in assembly.segments:
        transcript = next(
            (item for item in index.transcripts if item.media_id == segment.media_id), None
        )
        pauses = [item for item in index.pauses if item.media_id == segment.media_id]
        candidates = by_media.get(segment.media_id, [])
        start = _best_boundary(
            candidates,
            segment.source_range,
            edge="in",
            requested=segment.source_range.start,
            transcript=transcript,
            pauses=pauses,
        )
        end = _best_boundary(
            candidates,
            segment.source_range,
            edge="out",
            requested=segment.source_range.end,
            transcript=transcript,
            pauses=pauses,
        )
        source_range = (
            TimeRange.from_start_end(start.time, end.time)
            if end.time > start.time
            else segment.source_range
        )
        timeline_range = TimeRange(start=cursor, duration=source_range.duration)
        refined.append(
            segment.model_copy(
                update={"source_range": source_range, "timeline_range": timeline_range},
                deep=True,
            )
        )
        cursor = timeline_range.end
    return assembly.model_copy(update={"segments": refined}, deep=True)


def _best_boundary(
    points: list[CutPointCandidate],
    media_range: TimeRange,
    *,
    edge: Literal["in", "out"],
    requested: RationalTime,
    transcript: Transcript | None,
    pauses: list[PauseEvent],
) -> CutPointCandidate:
    usable = [
        point
        for point in points
        if point.edge in {edge, "either"}
        and media_range.contains(point.time, include_end=True)
        and not boundary_rejections(
            media_range=media_range,
            cut_time=point.time,
            transcript=transcript,
            protected_pauses=pauses,
        )
    ]
    if not usable:
        synthetic = next(
            (
                point
                for point in points
                if point.time == requested and point.edge in {edge, "either"}
            ),
            None,
        )
        if synthetic is None:
            raise ValueError("fine cut lacks a verified valid structural boundary")
        return synthetic
    return min(
        usable,
        key=lambda point: (
            abs(point.time.fraction - requested.fraction),
            -point.strength,
            point.id,
        ),
    )
