"""Professional top-K selects generation per editorial beat."""

from __future__ import annotations

from editorial_brain.core.confidence import conservative_confidence
from editorial_brain.core.models import (
    Confidence,
    EvidenceKind,
    MediaUnderstandingIndex,
    SelectCandidate,
    StoryMap,
)
from editorial_brain.policies.models import EditorialPolicy
from editorial_brain.selects.candidate import fit_select_duration
from editorial_brain.selects.diversity import diverse_top_k
from editorial_brain.selects.ranking import rank_selects
from editorial_brain.selects.scorer import score_select
from video_engine.api import TimeRange


def generate_selects(
    story: StoryMap,
    index: MediaUnderstandingIndex,
    policy: EditorialPolicy,
    *,
    top_k: int | None = None,
) -> dict[str, list[SelectCandidate]]:
    limit = top_k or policy.top_k
    by_beat: dict[str, list[SelectCandidate]] = {}
    usage: dict[str, int] = {}
    for beat in story.beats:
        candidates: list[SelectCandidate] = []
        for shot in index.shots:
            if not shot.evidence:
                continue
            score = score_select(beat, shot, policy.selects, prior_usage=usage.get(shot.id, 0))
            usable = fit_select_duration(shot, beat.target_duration)
            source_timed = any(
                requirement.kind == "dialogue" for requirement in beat.audio_requirements
            ) or beat.function.value in {"reaction", "breathing_space"}
            verified = (
                _verified_beat_range(beat, shot.media_id, shot.source_range)
                if source_timed
                else None
            )
            if verified is not None:
                usable = verified
            handle_before, handle_after = (
                usable.start - shot.source_range.start,
                shot.source_range.end - usable.end,
            )
            confidence = conservative_confidence(
                [shot.quality.confidence, shot.semantics.confidence],
                basis=EvidenceKind.DERIVED,
            )
            if shot.semantics.confidence.score == 0:
                confidence = Confidence(
                    score=min(0.4, shot.quality.confidence.score),
                    basis=EvidenceKind.DERIVED,
                    calibration="quality_without_semantics",
                )
            candidate = SelectCandidate(
                id=f"select:{beat.id}:{shot.id}",
                beat_id=beat.id,
                shot_id=shot.id,
                media_id=shot.media_id,
                media_sha256=shot.media_sha256,
                source_range=shot.source_range,
                inner_usable_range=usable,
                handle_before=handle_before,
                handle_after=handle_after,
                score=score,
                evidence=shot.evidence,
                reasons=_reasons(score),
                confidence=confidence,
            )
            candidates.append(candidate)
        ranked = rank_selects(candidates)
        selected = diverse_top_k(ranked, k=limit)
        selected_ids = [candidate.id for candidate in selected]
        selected = [
            candidate.model_copy(
                update={"alternative_ids": [item for item in selected_ids if item != candidate.id]}
            )
            for candidate in selected
        ]
        by_beat[beat.id] = selected
        if selected:
            usage[selected[0].shot_id] = usage.get(selected[0].shot_id, 0) + 1
    return by_beat


def _verified_beat_range(
    beat: object,
    media_id: str,
    shot_range: TimeRange,
) -> TimeRange | None:
    from editorial_brain.core.models import StoryBeat

    assert isinstance(beat, StoryBeat)
    ranges = [
        ref.source_range
        for ref in beat.evidence
        if ref.media_id == media_id and ref.source_range is not None
    ]
    if not ranges:
        return None
    span = TimeRange.from_start_end(
        min(item.start for item in ranges), max(item.end for item in ranges)
    )
    intersection = shot_range.intersection(span)
    return intersection if intersection is not None and not intersection.is_empty else None


def _reasons(score: object) -> list[str]:
    from editorial_brain.core.models import SelectScore

    assert isinstance(score, SelectScore)
    dimensions = {
        "semantically relevant": score.semantic_relevance,
        "visually clear": score.visual_clarity,
        "action completes in range": score.action_completeness,
        "strong measured quality": score.shot_quality,
        "useful reaction": score.reaction_value,
        "strong visual proof": score.evidence_value,
        "adds visual novelty": score.novelty,
    }
    reasons = [
        label
        for label, value in sorted(dimensions.items(), key=lambda item: (-item[1], item[0]))
        if value >= 0.5
    ]
    return reasons[:4] or ["best available verified source candidate"]
