"""Hard cut-boundary constraints."""

from __future__ import annotations

from editorial_brain.core.models import PauseEvent, Transcript
from video_engine.api import RationalTime, TimeRange

ZERO_TIME = RationalTime.zero()


def boundary_rejections(
    *,
    media_range: TimeRange,
    cut_time: RationalTime,
    transcript: Transcript | None = None,
    protected_pauses: list[PauseEvent] | None = None,
    required_handle_before: RationalTime = ZERO_TIME,
    required_handle_after: RationalTime = ZERO_TIME,
) -> list[str]:
    rejections: list[str] = []
    if not media_range.contains(cut_time, include_end=True):
        rejections.append("outside_source_range")
    if cut_time - media_range.start < required_handle_before:
        rejections.append("insufficient_handle_before")
    if media_range.end - cut_time < required_handle_after:
        rejections.append("insufficient_handle_after")
    if transcript is not None and any(
        word.source_range.start < cut_time < word.source_range.end for word in transcript.words
    ):
        rejections.append("inside_spoken_word")
    if protected_pauses and any(
        pause.protected and pause.source_range.contains(cut_time) for pause in protected_pauses
    ):
        rejections.append("protected_pause_or_reaction")
    return rejections
