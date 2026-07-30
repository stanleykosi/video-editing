"""Observable reaction cues and protection windows."""

from __future__ import annotations

from typing import Literal, cast

from editorial_brain.core.models import Confidence, EvidenceKind, Shot, VisibleReaction
from video_engine.api import RationalTime, TimeRange

REACTION_LABELS = {
    "smiles": "smiles",
    "laughs": "laughs",
    "looks_away": "looks_away",
    "surprised_visible_reaction": "surprised_visible_reaction",
    "long_silent_reaction": "long_silent_reaction",
    "head_turn": "head_turn",
    "gesture": "gesture",
}
DEFAULT_REACTION_LEAD = RationalTime(value=1, timescale=10)
DEFAULT_REACTION_TAIL = RationalTime(value=3, timescale=10)


def reactions_from_labels(shot: Shot) -> list[VisibleReaction]:
    reactions: list[VisibleReaction] = []
    for position, label in enumerate(shot.semantics.search_terms):
        normalized = label.lower().replace(" ", "_")
        cue = REACTION_LABELS.get(normalized)
        if cue is None:
            continue
        reactions.append(
            VisibleReaction(
                id=f"reaction:{shot.id}:{position:02d}",
                cue=cast(
                    Literal[
                        "smiles",
                        "laughs",
                        "looks_away",
                        "surprised_visible_reaction",
                        "long_silent_reaction",
                        "head_turn",
                        "gesture",
                        "other",
                    ],
                    cue,
                ),
                source_range=shot.inner_usable_range,
                salience=max(shot.semantics.reaction_value, 0.5),
                confidence=Confidence(
                    score=shot.semantics.confidence.score,
                    basis=EvidenceKind.MODEL_INFERRED,
                    calibration="observable_semantic_label",
                ),
            )
        )
    return reactions


def protection_window(
    reaction: VisibleReaction,
    *,
    lead: RationalTime = DEFAULT_REACTION_LEAD,
    tail: RationalTime = DEFAULT_REACTION_TAIL,
) -> TimeRange:
    start = max(RationalTime.zero(), reaction.source_range.start - lead)
    return TimeRange.from_start_end(start, reaction.source_range.end + tail)
