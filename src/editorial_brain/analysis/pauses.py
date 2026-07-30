"""Conservative pause classification and protection."""

from __future__ import annotations

from editorial_brain.analysis.audio_events import AudioWindow
from editorial_brain.core.models import (
    AudioEvent,
    Confidence,
    EvidenceKind,
    EvidenceRef,
    PauseClass,
    PauseEvent,
    Transcript,
)
from video_engine.api import RationalTime, TimeRange

DEFAULT_MINIMUM_PAUSE = RationalTime(value=3, timescale=20)


def classify_pauses(
    transcript: Transcript,
    *,
    audio_windows: list[AudioWindow],
    audio_events: list[AudioEvent],
    minimum_pause: RationalTime = DEFAULT_MINIMUM_PAUSE,
    analysis_version: str = "pause-context-v1",
) -> list[PauseEvent]:
    pauses: list[PauseEvent] = []
    for position, (left, right) in enumerate(
        zip(transcript.words, transcript.words[1:], strict=False)
    ):
        duration = right.source_range.start - left.source_range.end
        if duration < minimum_pause:
            continue
        source_range = TimeRange(start=left.source_range.end, duration=duration)
        overlapping_windows = [
            window for window in audio_windows if window.source_range.overlaps(source_range)
        ]
        mean_rms = (
            sum(window.rms for window in overlapping_windows) / len(overlapping_windows)
            if overlapping_windows
            else 0
        )
        nearby_events = [
            event for event in audio_events if event.source_range.overlaps(source_range)
        ]
        reaction = any(event.kind in {"laugh", "applause"} for event in nearby_events)
        if reaction:
            classification = PauseClass.REACTION_HOLD
            protected = True
            score = 0.8
        elif duration >= RationalTime(value=6, timescale=5) and mean_rms < 0.008:
            classification = PauseClass.DEAD_SPACE
            protected = False
            score = 0.7
        elif duration >= RationalTime(value=2, timescale=5):
            classification = PauseClass.THINKING_PAUSE
            protected = True
            score = 0.55
        else:
            classification = PauseClass.UNKNOWN
            protected = True
            score = 0.35
        evidence = EvidenceRef(
            id=f"evidence:{transcript.media_id}:pause:{position:06d}",
            kind=EvidenceKind.DERIVED,
            media_id=transcript.media_id,
            media_sha256=transcript.media_sha256,
            source_range=source_range,
            transcript_id=transcript.id,
            analysis_version=analysis_version,
            confidence=Confidence(
                score=score,
                basis=EvidenceKind.DERIVED,
                calibration="pause_context_rules",
            ),
            summary=f"gap={duration.fraction}s mean_rms={mean_rms:.6f}",
        )
        pauses.append(
            PauseEvent(
                id=f"pause:{transcript.media_id}:{position:06d}",
                media_id=transcript.media_id,
                source_range=source_range,
                classification=classification,
                protected=protected,
                evidence=[evidence],
                confidence=evidence.confidence,
            )
        )
    return pauses
