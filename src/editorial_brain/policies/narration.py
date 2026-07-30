"""Narration-led visual-proof policy."""

from editorial_brain.policies.models import EditorialPolicy, PacingPolicy
from editorial_brain.policies.neutral import neutral_policy
from video_engine.api import RationalTime


def narration_policy() -> EditorialPolicy:
    policy = neutral_policy()
    weights = dict(policy.cut.weights)
    weights.update(
        visual_relevance=2.5,
        semantic_completeness=2,
        story_progression=1.5,
        visual_novelty=1.25,
    )
    return policy.model_copy(
        update={
            "id": "narration",
            "cut": policy.cut.model_copy(update={"weights": weights}),
            "pacing": PacingPolicy(
                preferred_shot_duration=RationalTime(value=5, timescale=2),
                minimum_shot_duration=RationalTime(value=3, timescale=5),
                maximum_shot_duration=RationalTime(value=10, timescale=1),
            ),
        }
    )
