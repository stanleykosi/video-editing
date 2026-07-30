"""Motivated J-cut planning."""

from editorial_brain.core.models import AudioPictureRelationship, ContinuityScore
from video_engine.api import RationalTime

DEFAULT_JCUT_EXTENSION = RationalTime(value=1, timescale=4)


def plan_jcut(
    continuity: ContinuityScore,
    *,
    incoming_dialogue: bool,
    available_handle: RationalTime,
    preferred_extension: RationalTime = DEFAULT_JCUT_EXTENSION,
) -> tuple[AudioPictureRelationship, RationalTime]:
    if not incoming_dialogue or available_handle.value <= 0:
        return AudioPictureRelationship.HARD_AV, RationalTime.zero()
    if continuity.overall < 0.75 or continuity.dialogue >= 0.75:
        return AudioPictureRelationship.J_CUT, min(available_handle, preferred_extension)
    return AudioPictureRelationship.HARD_AV, RationalTime.zero()
