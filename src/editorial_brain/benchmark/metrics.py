"""Objective technical and golden editorial measurements."""

from __future__ import annotations

from editorial_brain.continuity.visual import continuity_score
from editorial_brain.core.models import EditorialPlan, MediaUnderstandingIndex, SelectCandidate
from video_engine.api import Project, TimelinePatch, TimeRange


def invalid_source_ranges(plan: EditorialPlan, project: Project) -> int:
    media = {item.id: item for item in project.media}
    invalid = 0
    for segment in plan.assembly.segments:
        reference = media.get(segment.media_id)
        invalid += (
            reference is None
            or reference.available_range is None
            or segment.source_range.start < reference.available_range.start
            or segment.source_range.end > reference.available_range.end
        )
    return invalid


def cuts_inside_words(plan: EditorialPlan, index: MediaUnderstandingIndex) -> int:
    cut_by_id = {item.id: item for item in plan.cut_candidates}
    points = {item.id: item for item in plan.cut_points}
    selected_points = [
        point_id
        for cut_id in plan.assembly.cut_ids
        for point_id in (
            cut_by_id[cut_id].out_point_id,
            cut_by_id[cut_id].in_point_id,
        )
        if point_id is not None
    ]
    return sum(
        word.source_range.start < points[point_id].time < word.source_range.end
        for point_id in selected_points
        for transcript in index.transcripts
        if transcript.media_id == points[point_id].media_id
        for word in transcript.words
    )


def missing_required_beats(plan: EditorialPlan) -> int:
    mandatory = {beat.id for beat in plan.story.beats if beat.mandatory}
    return len(mandatory - set(plan.assembly.covered_beat_ids))


def duration_error(plan: EditorialPlan, target_seconds: float | None) -> float:
    if target_seconds is None:
        return 0
    actual = float(plan.assembly.segments[-1].timeline_range.end.fraction)
    return abs(actual - target_seconds)


def duplicate_source_usage(plan: EditorialPlan) -> int:
    keys = [
        (segment.media_id, segment.source_range.start.fraction, segment.source_range.end.fraction)
        for segment in plan.assembly.segments
    ]
    return len(keys) - len(set(keys))


def repetition_score(plan: EditorialPlan) -> float:
    if not plan.assembly.segments:
        return 0
    return duplicate_source_usage(plan) / len(plan.assembly.segments)


def continuity_violations(plan: EditorialPlan, index: MediaUnderstandingIndex) -> int:
    shot_by_select = {
        decision.selected_id: next(
            (
                shot
                for shot in index.shots
                if decision.selected_id and shot.id in decision.selected_id
            ),
            None,
        )
        for decision in plan.decisions
        if decision.kind == "select"
    }
    violations = 0
    for left_segment, right_segment in zip(
        plan.assembly.segments, plan.assembly.segments[1:], strict=False
    ):
        left = shot_by_select.get(left_segment.select_id)
        right = shot_by_select.get(right_segment.select_id)
        if left is None or right is None:
            continue
        score = continuity_score(left, right)
        motivated = right_segment.transition != "cut" or right_segment.role in {
            "reaction",
            "montage",
            "wide_reset",
        }
        violations += score.overall < 0.35 and not motivated
    return violations


def visual_requirement_match(plan: EditorialPlan) -> float:
    required = [
        item for beat in plan.story.beats for item in beat.visual_requirements if item.required
    ]
    if not required:
        return 1
    covered = set(plan.assembly.covered_beat_ids)
    matched = sum(
        beat.id in covered
        for beat in plan.story.beats
        for item in beat.visual_requirements
        if item.required
    )
    return matched / len(required)


def reaction_preservation(plan: EditorialPlan, index: MediaUnderstandingIndex) -> float:
    significant = [
        reaction for shot in index.shots for reaction in shot.reactions if reaction.salience >= 0.6
    ]
    if not significant:
        return 1
    kept = sum(
        any(
            segment.media_id == shot.media_id
            and segment.source_range.overlaps(reaction.source_range)
            for segment in plan.assembly.segments
        )
        for shot in index.shots
        for reaction in shot.reactions
        if reaction.salience >= 0.6
    )
    return kept / len(significant)


def audio_picture_alignment(plan: EditorialPlan) -> float:
    if not plan.assembly.segments:
        return 0
    valid = sum(
        segment.audio_relationship.value not in {"j_cut", "l_cut", "reaction_continuing_dialogue"}
        or segment.audio_source_range is not None
        for segment in plan.assembly.segments
    )
    return valid / len(plan.assembly.segments)


def must_include_coverage(plan: EditorialPlan, required_media: list[str]) -> float:
    if not required_media:
        return 1
    used = {segment.media_id for segment in plan.assembly.segments}
    return len(set(required_media) & used) / len(set(required_media))


def must_exclude_violations(
    plan: EditorialPlan,
    excluded_media: list[str],
    excluded_ranges: list[TimeRange] | None = None,
) -> int:
    excluded = set(excluded_media)
    ranges = excluded_ranges or []
    return sum(
        segment.media_id in excluded or any(segment.source_range.overlaps(item) for item in ranges)
        for segment in plan.assembly.segments
    )


def patch_validation(patch: TimelinePatch, project: Project) -> bool:
    return patch.expected_project_revision == project.revision and bool(patch.operations)


def expected_select_top_k_recall(
    candidates: list[SelectCandidate], expected_shot_ids: set[str], k: int
) -> float:
    if not expected_shot_ids:
        return 1
    selected = {item.shot_id for item in candidates[:k]}
    return len(selected & expected_shot_ids) / len(expected_shot_ids)


def expected_cut_window_accuracy(
    actual_seconds: float, expected_seconds: float, tolerance: float
) -> float:
    if tolerance <= 0:
        raise ValueError("cut-window tolerance must be positive")
    return max(0, 1 - abs(actual_seconds - expected_seconds) / tolerance)


def expected_candidate_rank(candidates: list[SelectCandidate], expected_shot_id: str) -> float:
    for rank, candidate in enumerate(candidates, 1):
        if candidate.shot_id == expected_shot_id:
            return 1 / rank
    return 0
