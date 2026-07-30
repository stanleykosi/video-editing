"""Observable action extraction from constrained semantic labels."""

from __future__ import annotations

from editorial_brain.core.models import Confidence, EvidenceKind, Shot, VisibleAction


def actions_from_labels(shot: Shot) -> list[VisibleAction]:
    actions: list[VisibleAction] = []
    for label in shot.semantics.search_terms:
        if not label.startswith("action:"):
            continue
        action = label.removeprefix("action:").strip()
        if not action:
            continue
        actions.append(
            VisibleAction(
                label=action,
                source_range=shot.inner_usable_range,
                confidence=Confidence(
                    score=shot.semantics.confidence.score,
                    basis=EvidenceKind.MODEL_INFERRED,
                    calibration="semantic_label",
                ),
            )
        )
    return actions
