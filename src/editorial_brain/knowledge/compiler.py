"""Apply source-neutral taste directives to typed editorial policy."""

from __future__ import annotations

from fractions import Fraction
from statistics import fmean

from editorial_brain.core.hashing import fingerprint
from editorial_brain.policies.models import (
    CUT_DIMENSIONS,
    EditorialDirective,
    EditorialPolicy,
    SelectScoringPolicy,
)
from video_engine.api import RationalTime


def apply_directives(
    policy: EditorialPolicy, directives: list[EditorialDirective]
) -> EditorialPolicy:
    if not directives:
        return policy
    invalid_cut = sorted(
        {
            key
            for directive in directives
            for key in directive.scoring_adjustments
            if key not in CUT_DIMENSIONS
        }
    )
    select_fields = set(SelectScoringPolicy.model_fields)
    invalid_select = sorted(
        {
            key
            for directive in directives
            for key in directive.select_adjustments
            if key not in select_fields
        }
    )
    if invalid_cut or invalid_select:
        raise ValueError(
            f"directive score dimensions invalid; cut={invalid_cut}, select={invalid_select}"
        )
    cut_delta = _aggregate(directives, "scoring_adjustments", limit=0.5)
    select_delta = _aggregate(directives, "select_adjustments", limit=0.15)
    weights = {
        key: max(0, value + cut_delta.get(key, 0)) for key, value in policy.cut.weights.items()
    }
    select_values = policy.selects.model_dump()
    for key, adjustment in select_delta.items():
        select_values[key] = max(0, float(select_values[key]) + adjustment)
    preferred = _mean_multiplier(directives, "preferred_duration_multiplier")
    minimum = _mean_multiplier(directives, "minimum_duration_multiplier")
    maximum = _mean_multiplier(directives, "maximum_duration_multiplier")
    pacing = policy.pacing.model_copy(
        update={
            "preferred_shot_duration": _scale_time(
                policy.pacing.preferred_shot_duration, preferred
            ),
            "minimum_shot_duration": _scale_time(policy.pacing.minimum_shot_duration, minimum),
            "maximum_shot_duration": _scale_time(policy.pacing.maximum_shot_duration, maximum),
            "breathing_room_weight": max(
                0,
                policy.pacing.breathing_room_weight
                + sum(item.breathing_room_adjustment for item in directives),
            ),
            "music_alignment_weight": max(
                0,
                policy.pacing.music_alignment_weight
                + sum(item.music_alignment_adjustment for item in directives),
            ),
            "allow_intentional_long_holds": _boolean_prior(
                directives,
                "allow_intentional_long_holds",
                policy.pacing.allow_intentional_long_holds,
            ),
        }
    )
    if pacing.minimum_shot_duration > pacing.preferred_shot_duration:
        pacing = pacing.model_copy(update={"minimum_shot_duration": pacing.preferred_shot_duration})
    if pacing.maximum_shot_duration < pacing.preferred_shot_duration:
        pacing = pacing.model_copy(update={"maximum_shot_duration": pacing.preferred_shot_duration})
    dialogue = policy.dialogue.model_copy(
        update={
            "preserve_reactions": _boolean_prior(
                directives, "preserve_reactions", policy.dialogue.preserve_reactions
            ),
            "preserve_breaths": _boolean_prior(
                directives, "preserve_breaths", policy.dialogue.preserve_breaths
            ),
        }
    )
    return policy.model_copy(
        update={
            "cut": policy.cut.model_copy(update={"weights": weights}),
            "selects": policy.selects.model_copy(update=select_values),
            "pacing": pacing,
            "dialogue": dialogue,
            "directive_ids": [item.id for item in directives],
            "knowledge_fingerprint": fingerprint(directives),
            "knowledge_reasons": list(
                dict.fromkeys(reason for item in directives for reason in item.reasons)
            ),
            "transition_preferences": list(
                dict.fromkeys(rule for item in directives for rule in item.transition_rules)
            ),
        },
        deep=True,
    )


def _aggregate(
    directives: list[EditorialDirective], field: str, *, limit: float
) -> dict[str, float]:
    values: dict[str, float] = {}
    for directive in directives:
        mapping = getattr(directive, field)
        for key, value in mapping.items():
            values[key] = max(-limit, min(limit, values.get(key, 0) + value * directive.confidence))
    return values


def _mean_multiplier(directives: list[EditorialDirective], field: str) -> float:
    values = [float(getattr(item, field)) for item in directives if getattr(item, field) != 1]
    return max(0.65, min(1.5, fmean(values) if values else 1.0))


def _boolean_prior(directives: list[EditorialDirective], field: str, default: bool) -> bool:
    values = [getattr(item, field) for item in directives if getattr(item, field) is not None]
    return any(values) if values else default


def _scale_time(value: RationalTime, multiplier: float) -> RationalTime:
    ticks = value.fraction * Fraction(str(multiplier)) * 1_000_000
    return RationalTime(value=round(ticks), timescale=1_000_000)
