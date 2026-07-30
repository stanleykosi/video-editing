"""Enumerate, constrain, score, and retain alternative cuts per assembly boundary."""

from __future__ import annotations

from fractions import Fraction
from itertools import product

from editorial_brain.continuity.visual import continuity_score
from editorial_brain.core.models import (
    CandidateAssembly,
    CutCandidate,
    CutPointCandidate,
    MediaUnderstandingIndex,
    PauseEvent,
    PlannedSegment,
    SelectCandidate,
    Transcript,
)
from editorial_brain.cuts.boundaries import boundary_rejections
from editorial_brain.cuts.reaction import reaction_cut_rejection
from editorial_brain.cuts.scoring import score_cut
from editorial_brain.policies.models import EditorialPolicy
from video_engine.api import RationalTime

NEARBY_CUT_WINDOW = RationalTime(value=1, timescale=2)


def score_assembly_cuts(
    assembly: CandidateAssembly,
    pools: dict[str, list[SelectCandidate]],
    points: list[CutPointCandidate],
    index: MediaUnderstandingIndex,
    policy: EditorialPolicy,
) -> tuple[CandidateAssembly, list[CutCandidate]]:
    selects = {candidate.id: candidate for values in pools.values() for candidate in values}
    shots = {shot.id: shot for shot in index.shots}
    all_cuts: list[CutCandidate] = []
    chosen_ids: list[str] = []
    for position in range(1, len(assembly.segments)):
        left_segment = assembly.segments[position - 1]
        right_segment = assembly.segments[position]
        left = selects[left_segment.select_id]
        right = selects[right_segment.select_id]
        left_shot = shots[left.shot_id]
        right_shot = shots[right.shot_id]
        continuity = continuity_score(left_shot, right_shot)
        out_points = _nearby(
            points,
            left.media_id,
            left_segment.source_range.end,
            "out",
            left.source_range.start,
            left.source_range.end,
        )
        in_points = _nearby(
            points,
            right.media_id,
            right_segment.source_range.start,
            "in",
            right.source_range.start,
            right.source_range.end,
        )
        boundary_cuts: list[CutCandidate] = []
        for out_point, in_point in product(out_points[:3], in_points[:3]):
            rejections = [
                *boundary_rejections(
                    media_range=left.source_range,
                    cut_time=out_point.time,
                    transcript=_transcript(index, left.media_id),
                    protected_pauses=_pauses(index, left.media_id),
                ),
                *boundary_rejections(
                    media_range=right.source_range,
                    cut_time=in_point.time,
                    transcript=_transcript(index, right.media_id),
                    protected_pauses=_pauses(index, right.media_id),
                ),
            ]
            reaction_rejection = reaction_cut_rejection(left_shot, out_point.time)
            if reaction_rejection:
                rejections.append(reaction_rejection)
            boundary_cuts.append(
                score_cut(
                    left,
                    right,
                    in_point,
                    continuity,
                    policy.cut,
                    out_point=out_point,
                    hard_rejections=rejections,
                )
            )
        ranked = sorted(
            boundary_cuts,
            key=lambda item: (
                not item.valid,
                -item.score.overall,
                _distance(item, out_points, in_points, left_segment, right_segment),
                item.id,
            ),
        )
        valid = [item for item in ranked if item.valid]
        if not valid:
            raise ValueError(f"assembly boundary {position} has no valid cut candidate")
        chosen = min(
            valid,
            key=lambda item: (
                _chosen_distance(item, points, left_segment, right_segment),
                -item.score.overall,
                item.id,
            ),
        )
        chosen_ids.append(chosen.id)
        all_cuts.extend(ranked)
    return assembly.model_copy(update={"cut_ids": chosen_ids}, deep=True), all_cuts


def _nearby(
    points: list[CutPointCandidate],
    media_id: str,
    desired: RationalTime,
    edge: str,
    start: RationalTime,
    end: RationalTime,
) -> list[CutPointCandidate]:
    candidates = [
        point
        for point in points
        if point.media_id == media_id
        and point.edge in {edge, "either"}
        and start <= point.time <= end
        and abs(point.time.fraction - desired.fraction) <= NEARBY_CUT_WINDOW.fraction
    ]
    return sorted(
        candidates,
        key=lambda item: (
            abs(item.time.fraction - desired.fraction),
            -item.strength,
            item.id,
        ),
    )


def _transcript(index: MediaUnderstandingIndex, media_id: str) -> Transcript | None:
    return next((item for item in index.transcripts if item.media_id == media_id), None)


def _pauses(index: MediaUnderstandingIndex, media_id: str) -> list[PauseEvent]:
    return [item for item in index.pauses if item.media_id == media_id]


def _chosen_distance(
    cut: CutCandidate,
    points: list[CutPointCandidate],
    left: PlannedSegment,
    right: PlannedSegment,
) -> Fraction:
    by_id = {point.id: point for point in points}
    assert cut.out_point_id is not None
    return abs(by_id[cut.out_point_id].time.fraction - left.source_range.end.fraction) + abs(
        by_id[cut.in_point_id].time.fraction - right.source_range.start.fraction
    )


def _distance(
    cut: CutCandidate,
    out_points: list[CutPointCandidate],
    in_points: list[CutPointCandidate],
    left: PlannedSegment,
    right: PlannedSegment,
) -> Fraction:
    return _chosen_distance(cut, [*out_points, *in_points], left, right)
