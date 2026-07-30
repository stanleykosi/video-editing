"""Transparent global assembly objective."""

from __future__ import annotations

from editorial_brain.core.models import AssemblyScore, PlannedSegment, SelectCandidate


def assembly_score(
    segments: list[PlannedSegment],
    candidates: list[SelectCandidate],
    *,
    covered_beats: int,
    total_beats: int,
    duration_fit: float,
    continuity_scores: list[float],
    pacing_score: float,
    constraint_penalty: float = 0,
) -> AssemblyScore:
    story_coverage = covered_beats / total_beats if total_beats else 0
    selects_quality = sum(item.score.overall for item in candidates) / len(candidates)
    continuity = sum(continuity_scores) / len(continuity_scores) if continuity_scores else 1
    unique_sources = {
        (segment.media_id, segment.source_range.start.fraction, segment.source_range.end.fraction)
        for segment in segments
    }
    diversity = len(unique_sources) / len(segments)
    repetition_penalty = 1 - diversity
    audio_picture = (
        sum(segment.audio_relationship.value != "hard_av" for segment in segments) / len(segments)
        if segments
        else 0
    )
    weighted = (
        story_coverage * 0.27
        + duration_fit * 0.12
        + selects_quality * 0.2
        + continuity * 0.13
        + diversity * 0.1
        + pacing_score * 0.13
        + audio_picture * 0.05
    )
    overall = weighted - repetition_penalty * 0.15 - constraint_penalty
    return AssemblyScore(
        story_coverage=story_coverage,
        duration_fit=duration_fit,
        selects_quality=selects_quality,
        continuity=continuity,
        diversity=diversity,
        pacing=pacing_score,
        audio_picture=audio_picture,
        repetition_penalty=repetition_penalty,
        constraint_penalty=constraint_penalty,
        overall=overall,
    )


def target_duration_fit(
    actual_seconds: float,
    minimum: float | None,
    maximum: float | None,
    target: float | None = None,
) -> float:
    if minimum is not None and actual_seconds < minimum:
        return max(0, actual_seconds / max(minimum, 0.001))
    if maximum is not None and actual_seconds > maximum:
        return max(0, maximum / actual_seconds)
    if target is not None:
        return max(0, 1 - abs(actual_seconds - target) / max(target, 0.001))
    return 1
