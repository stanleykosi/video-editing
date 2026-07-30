"""Hard assembly constraints evaluated before soft objectives."""

from __future__ import annotations

from pydantic import Field

from editorial_brain.core.models import BrainModel, EditorialConstraints, SelectCandidate, StoryMap
from video_engine.api import RationalTime


class ConstraintEvaluation(BrainModel):
    valid: bool
    violations: list[str] = Field(default_factory=list)


def candidate_constraints(
    candidate: SelectCandidate,
    constraints: EditorialConstraints,
) -> ConstraintEvaluation:
    violations: list[str] = []
    if candidate.media_id in constraints.must_exclude_media_ids:
        violations.append("must_not_use_media")
    if candidate.source_range.duration.value <= 0:
        violations.append("invalid_source_range")
    if candidate.inner_usable_range.start < candidate.source_range.start:
        violations.append("usable_range_before_source")
    if candidate.inner_usable_range.end > candidate.source_range.end:
        violations.append("usable_range_after_source")
    if any(candidate.source_range.overlaps(item) for item in constraints.must_exclude_ranges):
        violations.append("must_not_use_range")
    return ConstraintEvaluation(valid=not violations, violations=violations)


def final_constraints(
    beat_ids: list[str],
    media_ids: list[str],
    shot_ids: list[str],
    duration: RationalTime,
    story: StoryMap,
    constraints: EditorialConstraints,
) -> ConstraintEvaluation:
    violations: list[str] = []
    mandatory = {beat.id for beat in story.beats if beat.mandatory}
    missing = sorted(mandatory - set(beat_ids))
    if missing:
        violations.extend(f"missing_required_beat:{beat_id}" for beat_id in missing)
    missing_locked = sorted(set(constraints.locked_beat_ids) - set(beat_ids))
    if missing_locked:
        violations.extend(f"missing_locked_beat:{beat_id}" for beat_id in missing_locked)
    missing_media = sorted(set(constraints.must_include_media_ids) - set(media_ids))
    if missing_media:
        violations.extend(f"missing_must_use_media:{media_id}" for media_id in missing_media)
    missing_shots = sorted(set(constraints.must_include_shot_ids) - set(shot_ids))
    if missing_shots:
        violations.extend(f"missing_must_use_shot:{shot_id}" for shot_id in missing_shots)
    if constraints.maximum_duration and duration > constraints.maximum_duration:
        violations.append("maximum_duration_exceeded")
    if constraints.minimum_duration and duration < constraints.minimum_duration:
        violations.append("minimum_duration_not_met")
    return ConstraintEvaluation(valid=not violations, violations=violations)
