"""Translate measurable reference grammar into bounded editorial priors."""

from editorial_brain.core.models import ReferenceEditProfile
from editorial_brain.policies.models import EditorialPolicy


def apply_reference_priors(
    policy: EditorialPolicy, profile: ReferenceEditProfile
) -> EditorialPolicy:
    preferred = profile.shot_duration_quantiles.get("p50")
    if preferred is None or preferred.value <= 0:
        return policy
    pacing = policy.pacing.model_copy(
        update={
            "preferred_shot_duration": preferred,
            "minimum_shot_duration": min(policy.pacing.minimum_shot_duration, preferred),
            "maximum_shot_duration": max(policy.pacing.maximum_shot_duration, preferred),
            "music_alignment_weight": min(
                0.35,
                policy.pacing.music_alignment_weight + profile.music_sync_score * 0.15,
            ),
        }
    )
    return policy.model_copy(
        update={"id": f"{policy.id}+reference:{profile.id}", "pacing": pacing},
        deep=True,
    )
