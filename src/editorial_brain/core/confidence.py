"""Confidence aggregation without fabricating certainty."""

from __future__ import annotations

from collections.abc import Iterable

from editorial_brain.core.models import Confidence, EvidenceKind


def conservative_confidence(values: Iterable[Confidence], *, basis: EvidenceKind) -> Confidence:
    items = list(values)
    if not items:
        return Confidence(score=0, basis=basis, calibration="no_evidence")
    score = min(item.score for item in items)
    return Confidence(
        score=score,
        basis=basis,
        calibration="minimum_support",
        sample_size=len(items),
    )


def weighted_confidence(
    values: Iterable[tuple[Confidence, float]], *, basis: EvidenceKind
) -> Confidence:
    items = [(confidence, weight) for confidence, weight in values if weight > 0]
    if not items:
        return Confidence(score=0, basis=basis, calibration="no_evidence")
    total = sum(weight for _, weight in items)
    score = sum(confidence.score * weight for confidence, weight in items) / total
    return Confidence(
        score=score,
        basis=basis,
        calibration="weighted_inputs",
        sample_size=len(items),
    )
