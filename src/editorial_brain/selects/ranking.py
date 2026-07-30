"""Stable candidate ranking."""

from editorial_brain.core.models import SelectCandidate


def rank_selects(candidates: list[SelectCandidate]) -> list[SelectCandidate]:
    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate.score.overall,
            -candidate.score.semantic_relevance,
            -candidate.score.shot_quality,
            candidate.media_id,
            candidate.source_range.start,
            candidate.id,
        ),
    )
