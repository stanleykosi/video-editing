"""Narration reveal-timing validation."""

from editorial_brain.core.models import PlannedSegment, StoryBeat
from video_engine.api import RationalTime


def reveal_timing_violations(beat: StoryBeat, segment: PlannedSegment) -> list[str]:
    violations: list[str] = []
    for requirement in beat.visual_requirements:
        early_reveal = requirement.reveal_timing.value in {"before_phrase", "on_phrase"}
        if requirement.required and early_reveal and requirement.narration_range:
            latest = max(
                RationalTime.zero(),
                requirement.narration_range.start - requirement.early_handoff,
            )
            if segment.timeline_range.start > latest:
                violations.append(f"late_visual_reveal:{requirement.id}")
    return violations
