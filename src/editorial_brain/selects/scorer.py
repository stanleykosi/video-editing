"""Visible multidimensional select scoring."""

from __future__ import annotations

import re

from editorial_brain.core.models import SelectScore, Shot, StoryBeat
from editorial_brain.policies.models import SelectScoringPolicy

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def score_select(
    beat: StoryBeat,
    shot: Shot,
    policy: SelectScoringPolicy,
    *,
    prior_usage: int = 0,
) -> SelectScore:
    query = _tokens(
        " ".join(
            [
                beat.purpose,
                beat.source_text or "",
                *(requirement.description for requirement in beat.visual_requirements),
                *(requirement.entity or "" for requirement in beat.visual_requirements),
            ]
        )
    )
    document = _tokens(" ".join([shot.semantics.summary, *shot.semantics.search_terms]))
    semantic = len(query & document) / max(1, len(query))
    clarity = (shot.quality.sharpness + shot.quality.exposure + shot.quality.composition) / 3
    action = (
        sum(1 if item.completes else 0.5 if item.completes is None else 0 for item in shot.actions)
        / len(shot.actions)
        if shot.actions
        else 0.5
    )
    quality = max(
        0,
        (
            shot.quality.sharpness
            + shot.quality.exposure
            + shot.quality.stability
            + shot.quality.composition
        )
        / 4
        - shot.quality.occlusion_penalty
        - shot.quality.watermark_risk,
    )
    reaction = max(
        [shot.semantics.reaction_value, *(item.salience for item in shot.reactions)],
        default=0,
    )
    evidence = shot.semantics.evidence_value
    novelty = 1 / (1 + prior_usage)
    repetition = min(1, prior_usage / 3)
    weighted_sum = (
        semantic * policy.semantic_relevance
        + clarity * policy.visual_clarity
        + action * policy.action_completeness
        + quality * policy.shot_quality
        + reaction * policy.reaction_value
        + evidence * policy.evidence_value
        + novelty * policy.novelty
        - repetition * policy.repetition_penalty
    )
    positive_weight = (
        policy.semantic_relevance
        + policy.visual_clarity
        + policy.action_completeness
        + policy.shot_quality
        + policy.reaction_value
        + policy.evidence_value
        + policy.novelty
    )
    overall = max(0, min(1, weighted_sum / max(positive_weight, 1e-12)))
    return SelectScore(
        semantic_relevance=semantic,
        visual_clarity=clarity,
        action_completeness=action,
        shot_quality=quality,
        reaction_value=reaction,
        evidence_value=evidence,
        novelty=novelty,
        repetition_penalty=repetition,
        overall=overall,
    )


def _tokens(value: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(value.lower()))
