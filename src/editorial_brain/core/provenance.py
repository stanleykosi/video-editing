"""Compact engine-safe editorial provenance."""

from __future__ import annotations

from editorial_brain.core.models import EditorialDecision, PlannedSegment


def segment_extensions(segment: PlannedSegment, decision: EditorialDecision) -> dict[str, object]:
    return {
        "editorial_brain:decision_id": decision.id,
        "editorial_brain:beat_id": segment.beat_id,
        "editorial_brain:role": segment.role,
        "editorial_brain:confidence": decision.confidence.score,
        "editorial_brain:select_id": segment.select_id,
        "editorial_brain:policy_ids": decision.policy_ids,
    }
