"""Measured room-tone and dialogue continuity."""

from editorial_brain.analysis.audio_events import AudioWindow
from editorial_brain.core.models import Transcript
from video_engine.api import RationalTime


def room_tone_score(
    left_windows: list[AudioWindow],
    right_windows: list[AudioWindow],
    *,
    left_time: RationalTime,
    right_time: RationalTime,
) -> float:
    left = _nearest(left_windows, left_time)
    right = _nearest(right_windows, right_time)
    if left is None or right is None:
        return 0.5
    difference = abs(left.rms - right.rms)
    return max(0, 1 - difference / 0.1)


def dialogue_continuity(
    left_transcript: Transcript | None,
    right_transcript: Transcript | None,
) -> float:
    if left_transcript is None or right_transcript is None:
        return 0.5
    left_speaker = left_transcript.words[-1].speaker_id if left_transcript.words else None
    right_speaker = right_transcript.words[0].speaker_id if right_transcript.words else None
    if left_speaker is None or right_speaker is None:
        return 0.6
    return 1 if left_speaker == right_speaker else 0.8


def _nearest(windows: list[AudioWindow], time: RationalTime) -> AudioWindow | None:
    return min(
        windows,
        key=lambda window: abs(window.source_range.start.fraction - time.fraction),
        default=None,
    )
