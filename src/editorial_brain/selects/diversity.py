"""Deterministic maximal-marginal-relevance select diversity."""

from __future__ import annotations

from editorial_brain.core.models import SelectCandidate


def diverse_top_k(
    candidates: list[SelectCandidate],
    *,
    k: int,
    diversity_weight: float = 0.2,
) -> list[SelectCandidate]:
    if k <= 0:
        raise ValueError("top-K must be positive")
    remaining = {candidate.id: candidate for candidate in candidates}
    selected: list[SelectCandidate] = []
    while remaining and len(selected) < k:
        best = max(
            remaining.values(),
            key=lambda candidate: (
                _marginal_score(candidate, selected, diversity_weight),
                candidate.score.overall,
                _reverse_id(candidate.id),
            ),
        )
        selected.append(best)
        remaining.pop(best.id)
    return selected


def _marginal_score(
    candidate: SelectCandidate,
    selected: list[SelectCandidate],
    weight: float,
) -> float:
    if not selected:
        return candidate.score.overall
    maximum_similarity = max(_similarity(candidate, existing) for existing in selected)
    return candidate.score.overall - weight * maximum_similarity


def _similarity(left: SelectCandidate, right: SelectCandidate) -> float:
    if left.shot_id == right.shot_id:
        return 1
    if left.media_id == right.media_id and left.source_range.overlaps(right.source_range):
        return 0.8
    if left.media_id == right.media_id:
        return 0.25
    return 0


def _reverse_id(value: str) -> tuple[int, ...]:
    return tuple(-ord(character) for character in value)
