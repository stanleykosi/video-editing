"""Music/motion-aware montage policy."""

from editorial_brain.policies.models import EditorialPolicy, PacingPolicy
from editorial_brain.policies.neutral import neutral_policy
from video_engine.api import RationalTime


def montage_policy() -> EditorialPolicy:
    policy = neutral_policy()
    weights = dict(policy.cut.weights)
    weights.update(
        motion_compatibility=2,
        rhythm=2,
        visual_novelty=1.75,
        action_continuity=1.5,
    )
    return policy.model_copy(
        update={
            "id": "montage",
            "cut": policy.cut.model_copy(update={"weights": weights}),
            "pacing": PacingPolicy(
                preferred_shot_duration=RationalTime(value=3, timescale=2),
                minimum_shot_duration=RationalTime(value=1, timescale=4),
                maximum_shot_duration=RationalTime(value=8, timescale=1),
                music_alignment_weight=0.35,
            ),
        }
    )
