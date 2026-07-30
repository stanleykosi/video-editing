"""Explicit cut scoring with hard-rejection separation."""

from __future__ import annotations

from editorial_brain.core.models import (
    Confidence,
    ContinuityScore,
    CutCandidate,
    CutPointCandidate,
    CutScore,
    EvidenceKind,
    SelectCandidate,
)
from editorial_brain.policies.models import CutScoringPolicy


def score_cut(
    left: SelectCandidate | None,
    right: SelectCandidate,
    in_point: CutPointCandidate,
    continuity: ContinuityScore,
    policy: CutScoringPolicy,
    *,
    out_point: CutPointCandidate | None = None,
    hard_rejections: list[str] | None = None,
    semantic_model_score: float | None = None,
) -> CutCandidate:
    rejection_list = sorted(set(hard_rejections or []))
    dimensions = {
        "semantic_completeness": right.score.semantic_relevance,
        "story_progression": right.score.overall,
        "visual_relevance": right.score.semantic_relevance,
        "visual_continuity": continuity.overall,
        "action_continuity": continuity.temporal_action,
        "screen_direction": continuity.screen_direction,
        "shot_scale_compatibility": continuity.shot_scale,
        "composition_compatibility": continuity.subject_position,
        "motion_compatibility": continuity.camera_motion,
        "audio_continuity": (continuity.room_tone + continuity.dialogue) / 2,
        "speech_integrity": 0 if "inside_spoken_word" in rejection_list else 1,
        "reaction_preservation": 0 if "protected_pause_or_reaction" in rejection_list else 1,
        "emotional_continuity": continuity.semantic,
        "rhythm": in_point.strength,
        "information_density": min(1, right.score.semantic_relevance + right.score.evidence_value),
        "visual_novelty": right.score.novelty,
        "shot_quality": right.score.shot_quality,
        "source_handle_safety": 0 if any("handle" in item for item in rejection_list) else 1,
        "style_profile_fit": right.score.overall,
        "technical_feasibility": 0 if rejection_list else 1,
    }
    deterministic = _weighted(dimensions, policy.weights)
    model_weight = policy.semantic_model_weight if semantic_model_score is not None else 0
    overall = deterministic * (1 - model_weight) + (semantic_model_score or 0) * model_weight
    if rejection_list:
        overall = 0
    cut_score = CutScore(
        **dimensions,
        deterministic_score=deterministic,
        semantic_model_score=semantic_model_score,
        overall=overall,
    )
    evidence = [*in_point.evidence, *(out_point.evidence if out_point else []), *right.evidence]
    return CutCandidate(
        id=(
            f"cut:{left.id if left else 'start'}:{right.id}:"
            f"{out_point.id if out_point else 'start'}:{in_point.id}"
        ),
        from_select_id=left.id if left else None,
        to_select_id=right.id,
        out_point_id=out_point.id if out_point else None,
        in_point_id=in_point.id,
        score=cut_score,
        continuity=continuity,
        hard_rejections=rejection_list,
        evidence=evidence,
        confidence=Confidence(
            score=min(right.confidence.score, 1 if not rejection_list else 0),
            basis=EvidenceKind.DERIVED,
            calibration="cut_inputs_minimum",
        ),
    )


def _weighted(values: dict[str, float], weights: dict[str, float]) -> float:
    total = sum(weights.values())
    return sum(values[key] * weight for key, weight in weights.items()) / total
