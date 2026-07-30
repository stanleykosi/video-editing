"""Evidence-backed picture-role assignment."""

from editorial_brain.continuity.visual import continuity_score
from editorial_brain.core.models import (
    CandidateAssembly,
    EditorialProfile,
    MediaUnderstandingIndex,
    NarrativeFunction,
    StoryMap,
)
from editorial_brain.cuts.transitions import transition_for_cut


def assign_picture_roles(
    assembly: CandidateAssembly,
    story: StoryMap,
    index: MediaUnderstandingIndex,
    *,
    profile: EditorialProfile = EditorialProfile.NEUTRAL,
) -> CandidateAssembly:
    beats = {beat.id: beat for beat in story.beats}
    shots = {shot.id: shot for shot in index.shots}
    segments = []
    for segment in assembly.segments:
        role = "primary"
        beat = beats[segment.beat_id]
        shot = next((item for item in shots.values() if item.id in segment.select_id), None)
        protected = segment.protected
        has_significant_reaction = bool(
            shot and shot.reactions and max(item.salience for item in shot.reactions) >= 0.6
        )
        if profile is EditorialProfile.MONTAGE:
            role = "montage"
        elif has_significant_reaction:
            role = "reaction"
            protected = True
        elif (
            shot is not None
            and any(item.required for item in beat.visual_requirements)
            and shot.semantics.evidence_value >= 0.6
        ):
            role = "proof"
            protected = any(
                requirement.minimum_hold.value > 0
                and segment.timeline_range.duration >= requirement.minimum_hold
                for requirement in beat.visual_requirements
            )
        elif beat.function is NarrativeFunction.REACTION:
            role = "reaction"
            protected = True
        elif shot is not None and shot.semantics.cutaway_value >= 0.65:
            role = "cutaway"
        segments.append(
            segment.model_copy(update={"role": role, "protected": protected}, deep=True)
        )
    return assembly.model_copy(update={"segments": segments}, deep=True)


def assign_motivated_transitions(
    assembly: CandidateAssembly,
    story: StoryMap,
    index: MediaUnderstandingIndex,
) -> CandidateAssembly:
    beats = {beat.id: beat for beat in story.beats}
    selected_shots = {
        segment.select_id: next(
            (shot for shot in index.shots if shot.id in segment.select_id), None
        )
        for segment in assembly.segments
    }
    segments = []
    for position, segment in enumerate(assembly.segments):
        if position == 0:
            segments.append(segment)
            continue
        previous = assembly.segments[position - 1]
        left = selected_shots[previous.select_id]
        right = selected_shots[segment.select_id]
        if left is None or right is None:
            segments.append(segment)
            continue
        source_gap = (
            right.source_range.start - left.source_range.end
            if left.media_id == right.media_id
            else right.source_range.duration * 0
        )
        transition = transition_for_cut(
            continuity_score(left, right),
            next_function=beats[segment.beat_id].function,
            time_jump=source_gap.fraction >= 2,
        )
        segments.append(segment.model_copy(update={"transition": transition}, deep=True))
    return assembly.model_copy(update={"segments": segments}, deep=True)
