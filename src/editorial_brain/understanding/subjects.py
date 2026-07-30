"""Non-identifying visible-subject extraction."""

from __future__ import annotations

from editorial_brain.core.models import Confidence, EvidenceKind, Shot, VisibleSubject


def subjects_from_labels(shot: Shot) -> list[VisibleSubject]:
    labels = [
        label.removeprefix("subject:").strip()
        for label in shot.semantics.search_terms
        if label.startswith("subject:")
    ]
    return [
        VisibleSubject(
            label=label,
            role="main" if position == 0 else "secondary",
            salience=max(0, 1 - position * 0.2),
            confidence=Confidence(
                score=shot.semantics.confidence.score,
                basis=EvidenceKind.MODEL_INFERRED,
                calibration="semantic_label",
            ),
        )
        for position, label in enumerate(labels)
        if label
    ]
