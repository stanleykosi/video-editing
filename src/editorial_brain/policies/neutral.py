"""Balanced neutral editorial policy."""

from editorial_brain.policies.models import (
    CutScoringPolicy,
    DialoguePolicy,
    EditorialPolicy,
    PacingPolicy,
    equal_cut_weights,
)
from video_engine.api import RationalTime


def neutral_policy() -> EditorialPolicy:
    return EditorialPolicy(
        id="neutral",
        cut=CutScoringPolicy(weights=equal_cut_weights()),
        pacing=PacingPolicy(
            preferred_shot_duration=RationalTime(value=3, timescale=1),
            minimum_shot_duration=RationalTime(value=1, timescale=2),
            maximum_shot_duration=RationalTime(value=12, timescale=1),
        ),
        dialogue=DialoguePolicy(
            minimum_dead_air=RationalTime(value=2, timescale=5),
        ),
    )
