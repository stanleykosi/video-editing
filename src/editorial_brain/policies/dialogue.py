"""Dialogue-focused policy."""

from editorial_brain.policies.models import DialoguePolicy, EditorialPolicy, PacingPolicy
from editorial_brain.policies.neutral import neutral_policy
from video_engine.api import RationalTime


def dialogue_policy() -> EditorialPolicy:
    policy = neutral_policy()
    weights = dict(policy.cut.weights)
    weights.update(
        speech_integrity=2.5,
        audio_continuity=2,
        reaction_preservation=2,
        emotional_continuity=1.5,
    )
    return policy.model_copy(
        update={
            "id": "dialogue",
            "cut": policy.cut.model_copy(update={"weights": weights}),
            "pacing": PacingPolicy(
                preferred_shot_duration=RationalTime(value=5, timescale=1),
                minimum_shot_duration=RationalTime(value=1, timescale=1),
                maximum_shot_duration=RationalTime(value=30, timescale=1),
                breathing_room_weight=0.3,
            ),
            "dialogue": DialoguePolicy(
                filler_policy="conservative",
                minimum_dead_air=RationalTime(value=1, timescale=2),
            ),
        }
    )
