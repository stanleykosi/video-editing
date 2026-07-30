"""Source and framing repetition penalties."""

from editorial_brain.core.models import PlannedSegment


def repetition_score(segments: list[PlannedSegment]) -> float:
    if not segments:
        return 0
    seen: set[tuple[str, object, object]] = set()
    repeats = 0
    for segment in segments:
        key = (
            segment.media_id,
            segment.source_range.start.fraction,
            segment.source_range.end.fraction,
        )
        repeats += key in seen
        seen.add(key)
    return repeats / len(segments)
