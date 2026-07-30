"""Motivated L-cut and reaction-bridge planning."""

from editorial_brain.core.models import AudioPictureRelationship, ContinuityScore
from video_engine.api import RationalTime

DEFAULT_LCUT_EXTENSION = RationalTime(value=3, timescale=10)


def plan_lcut(
    continuity: ContinuityScore,
    *,
    outgoing_dialogue: bool,
    incoming_reaction: bool,
    available_handle: RationalTime,
    preferred_extension: RationalTime = DEFAULT_LCUT_EXTENSION,
) -> tuple[AudioPictureRelationship, RationalTime]:
    if not outgoing_dialogue or available_handle.value <= 0:
        return AudioPictureRelationship.HARD_AV, RationalTime.zero()
    if incoming_reaction:
        return (
            AudioPictureRelationship.REACTION_CONTINUING_DIALOGUE,
            min(available_handle, preferred_extension),
        )
    if (continuity.room_tone + continuity.dialogue) / 2 >= 0.5:
        return AudioPictureRelationship.L_CUT, min(available_handle, preferred_extension)
    return AudioPictureRelationship.HARD_AV, RationalTime.zero()
