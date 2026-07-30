"""Deterministic beam search over per-beat select pools."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from fractions import Fraction

from editorial_brain.continuity.visual import continuity_score
from editorial_brain.core.models import (
    CandidateAssembly,
    EditorialBrief,
    PlannedSegment,
    SelectCandidate,
    Shot,
    StoryMap,
)
from editorial_brain.policies.models import EditorialPolicy
from editorial_brain.rhythm.pacing import samples_from_segments, score_rhythm
from editorial_brain.search.constraints import candidate_constraints, final_constraints
from editorial_brain.search.objective import assembly_score, target_duration_fit
from video_engine.api import RationalTime, TimeRange


@dataclass(frozen=True)
class _BeamState:
    candidates: tuple[SelectCandidate, ...]
    continuity: tuple[float, ...]
    score_hint: float
    source_intervals: tuple[tuple[str, tuple[tuple[Fraction, Fraction], ...]], ...] = ()


def beam_search(
    story: StoryMap,
    pools: dict[str, list[SelectCandidate]],
    shots: list[Shot],
    brief: EditorialBrief,
    policy: EditorialPolicy,
    *,
    variants: int = 3,
    seed: int = 0,
) -> list[CandidateAssembly]:
    del seed  # Deterministic tie-breaking is lexical; seed remains part of the public contract.
    shot_by_id = {shot.id: shot for shot in shots}
    pair_scores: dict[tuple[str, str], float] = {}
    states = [_BeamState(candidates=(), continuity=(), score_hint=0)]
    for beat in story.beats:
        options = [
            option
            for option in pools.get(beat.id, [])
            if candidate_constraints(option, brief.constraints).valid
        ]
        if not options and beat.mandatory:
            return []
        if not options:
            continue
        expanded: list[_BeamState] = []
        for state in states:
            for option in options:
                continuity = state.continuity
                pair_score = 1.0
                if state.candidates:
                    left = shot_by_id[state.candidates[-1].shot_id]
                    right = shot_by_id[option.shot_id]
                    pair_key = (left.id, right.id)
                    if pair_key not in pair_scores:
                        pair_scores[pair_key] = continuity_score(left, right).overall
                    pair_score = pair_scores[pair_key]
                    if right.reactions or right.semantics.reaction_value >= 0.7:
                        pair_score = 1.0
                    continuity = (*continuity, pair_score)
                source_intervals, repeated = _insert_source_interval(
                    state.source_intervals,
                    option.media_id,
                    option.source_range.start.fraction,
                    option.source_range.end.fraction,
                )
                hint = (
                    state.score_hint
                    + option.score.overall
                    + pair_score * 0.3
                    - int(repeated) * policy.selects.repetition_penalty
                )
                expanded.append(
                    _BeamState(
                        candidates=(*state.candidates, option),
                        continuity=continuity,
                        score_hint=hint,
                        source_intervals=source_intervals,
                    )
                )
        states = sorted(expanded, key=_state_rank)[: policy.beam_width]
    assemblies = [
        _to_assembly(position, state, story, brief, policy) for position, state in enumerate(states)
    ]
    valid = [assembly for assembly in assemblies if not assembly.review_flags]
    ranked = valid or assemblies
    return sorted(ranked, key=lambda item: (-item.score.overall, item.id))[:variants]


def _state_rank(state: _BeamState) -> tuple[float, tuple[str, ...]]:
    return (-state.score_hint, tuple(candidate.id for candidate in state.candidates))


def _insert_source_interval(
    source_intervals: tuple[tuple[str, tuple[tuple[Fraction, Fraction], ...]], ...],
    media_id: str,
    start: Fraction,
    end: Fraction,
) -> tuple[
    tuple[tuple[str, tuple[tuple[Fraction, Fraction], ...]], ...],
    bool,
]:
    by_media = dict(source_intervals)
    intervals = by_media.get(media_id, ())
    position = bisect_left(intervals, (start, start))
    repeated = (position > 0 and intervals[position - 1][1] > start) or (
        position < len(intervals) and intervals[position][0] < end
    )
    merged_start = start
    merged_end = end
    left = position
    if left > 0 and intervals[left - 1][1] >= start:
        left -= 1
        merged_start = min(merged_start, intervals[left][0])
        merged_end = max(merged_end, intervals[left][1])
    right = position
    while right < len(intervals) and intervals[right][0] <= merged_end:
        merged_start = min(merged_start, intervals[right][0])
        merged_end = max(merged_end, intervals[right][1])
        right += 1
    by_media[media_id] = (
        *intervals[:left],
        (merged_start, merged_end),
        *intervals[right:],
    )
    return tuple(sorted(by_media.items())), repeated


def _to_assembly(
    position: int,
    state: _BeamState,
    story: StoryMap,
    brief: EditorialBrief,
    policy: EditorialPolicy,
) -> CandidateAssembly:
    cursor = RationalTime.zero()
    segments: list[PlannedSegment] = []
    for index, candidate in enumerate(state.candidates):
        duration = candidate.inner_usable_range.duration
        timeline_range = TimeRange(start=cursor, duration=duration)
        segments.append(
            PlannedSegment(
                id=f"segment:{position:04d}:{index:04d}",
                beat_id=candidate.beat_id,
                select_id=candidate.id,
                media_id=candidate.media_id,
                media_sha256=candidate.media_sha256,
                source_range=candidate.inner_usable_range,
                timeline_range=timeline_range,
                evidence=candidate.evidence,
                confidence=candidate.confidence,
            )
        )
        cursor = timeline_range.end
    rhythm = score_rhythm(segments, samples_from_segments(segments), policy.pacing)
    minimum = (
        float(brief.constraints.minimum_duration.fraction)
        if brief.constraints.minimum_duration
        else None
    )
    maximum = (
        float(brief.constraints.maximum_duration.fraction)
        if brief.constraints.maximum_duration
        else None
    )
    target = (
        float(brief.constraints.target_duration.fraction)
        if brief.constraints.target_duration
        else None
    )
    constraint_result = final_constraints(
        [item.beat_id for item in segments],
        [item.media_id for item in segments],
        [item.shot_id for item in state.candidates],
        cursor,
        story,
        brief.constraints,
    )
    score = assembly_score(
        segments,
        list(state.candidates),
        covered_beats=len({item.beat_id for item in segments}),
        total_beats=len(story.beats),
        duration_fit=target_duration_fit(float(cursor.fraction), minimum, maximum, target),
        continuity_scores=list(state.continuity),
        pacing_score=rhythm.overall,
        constraint_penalty=min(1, len(constraint_result.violations) * 0.2),
    )
    return CandidateAssembly(
        id=f"assembly:{position:04d}",
        segments=segments,
        score=score,
        rhythm=rhythm,
        covered_beat_ids=sorted({item.beat_id for item in segments}),
        review_flags=constraint_result.violations,
    )
