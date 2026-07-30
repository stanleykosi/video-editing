"""Independent high-level picture/audio relationship planning."""

from __future__ import annotations

from editorial_brain.continuity.visual import continuity_score
from editorial_brain.core.models import (
    AudioPictureRelationship,
    CandidateAssembly,
    EditorialProfile,
    MediaUnderstandingIndex,
    PlannedSegment,
)
from editorial_brain.cuts.jcut import plan_jcut
from editorial_brain.cuts.lcut import plan_lcut
from video_engine.api import TimeRange


def plan_audio_picture(
    assembly: CandidateAssembly,
    index: MediaUnderstandingIndex,
    *,
    narration_media_id: str | None = None,
    profile: EditorialProfile = EditorialProfile.NEUTRAL,
) -> CandidateAssembly:
    shots = {shot.id: shot for shot in index.shots}
    select_shots = {
        segment.select_id: next(
            (shot for shot in index.shots if shot.id in segment.select_id), None
        )
        for segment in assembly.segments
    }
    del shots
    planned: list[PlannedSegment] = []
    for position, segment in enumerate(assembly.segments):
        if narration_media_id is not None:
            planned.append(
                segment.model_copy(
                    update={
                        "audio_relationship": AudioPictureRelationship.BROLL_CONTINUING_DIALOGUE,
                        "audio_source_range": None,
                    },
                    deep=True,
                )
            )
            continue
        if profile is EditorialProfile.MONTAGE and _has_music(index, segment):
            planned.append(
                segment.model_copy(
                    update={"audio_relationship": AudioPictureRelationship.MUSIC_LED},
                    deep=True,
                )
            )
            continue
        if _has_protected_pause(index, segment):
            planned.append(
                segment.model_copy(
                    update={"audio_relationship": AudioPictureRelationship.INTENTIONAL_SILENCE},
                    deep=True,
                )
            )
            continue
        if position == 0:
            planned.append(segment)
            continue
        previous = assembly.segments[position - 1]
        left = select_shots.get(previous.select_id)
        right = select_shots.get(segment.select_id)
        if left is None or right is None:
            planned.append(segment)
            continue
        continuity = continuity_score(left, right)
        incoming_dialogue = _has_dialogue(index, segment)
        outgoing_dialogue = _has_dialogue(index, previous)
        incoming_reaction = segment.role == "reaction" or bool(right.reactions)
        relationship, extension = plan_lcut(
            continuity,
            outgoing_dialogue=outgoing_dialogue,
            incoming_reaction=incoming_reaction,
            available_handle=max(
                previous.source_range.duration * 0,
                left.source_range.end - previous.source_range.end,
            ),
        )
        if relationship.value == "hard_av":
            relationship, extension = plan_jcut(
                continuity,
                incoming_dialogue=incoming_dialogue,
                available_handle=max(
                    segment.source_range.duration * 0,
                    segment.source_range.start - right.source_range.start,
                ),
            )
        if relationship is AudioPictureRelationship.HARD_AV:
            if incoming_dialogue and outgoing_dialogue and previous.media_id == segment.media_id:
                relationship = AudioPictureRelationship.AUDIO_BRIDGE
            elif not incoming_dialogue and previous.media_id == segment.media_id:
                relationship = AudioPictureRelationship.AMBIENCE_CONTINUATION
        audio_range = None
        if relationship.value == "j_cut":
            start = max(right.source_range.start, segment.source_range.start - extension)
            audio_range = TimeRange.from_start_end(start, segment.source_range.end)
        elif relationship.value in {"l_cut", "reaction_continuing_dialogue"}:
            audio_range = TimeRange(
                start=previous.source_range.start,
                duration=previous.source_range.duration + extension,
            )
        planned.append(
            segment.model_copy(
                update={"audio_relationship": relationship, "audio_source_range": audio_range},
                deep=True,
            )
        )
    return assembly.model_copy(update={"segments": planned}, deep=True)


def _has_dialogue(index: MediaUnderstandingIndex, segment: PlannedSegment) -> bool:
    for transcript in index.transcripts:
        if transcript.media_id == segment.media_id and any(
            word.source_range.overlaps(segment.source_range) for word in transcript.words
        ):
            return True
        synchronization = next(
            (
                item
                for item in index.synchronizations
                if item.reference_media_id == transcript.media_id
                and item.target_media_id == segment.media_id
                and item.confidence.score >= 0.4
            ),
            None,
        )
        if synchronization is not None:
            aligned = TimeRange(
                start=max(
                    segment.source_range.start - synchronization.target_offset,
                    segment.source_range.duration * 0,
                ),
                duration=segment.source_range.duration,
            )
            if any(word.source_range.overlaps(aligned) for word in transcript.words):
                return True
    return False


def _has_music(index: MediaUnderstandingIndex, segment: PlannedSegment) -> bool:
    return any(
        event.media_id == segment.media_id and event.source_range.overlaps(segment.source_range)
        for event in index.music_events
    )


def _has_protected_pause(index: MediaUnderstandingIndex, segment: PlannedSegment) -> bool:
    return any(
        pause.media_id == segment.media_id
        and pause.protected
        and pause.source_range.overlaps(segment.source_range)
        for pause in index.pauses
    )
