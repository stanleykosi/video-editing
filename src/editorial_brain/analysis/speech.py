"""Deterministic phrase boundaries and speech-region enrichment."""

from __future__ import annotations

from typing import Literal, cast

from editorial_brain.core.confidence import conservative_confidence
from editorial_brain.core.models import (
    Confidence,
    EvidenceKind,
    Transcript,
    TranscriptPhrase,
    TranscriptWord,
)
from video_engine.api import RationalTime, TimeRange

DEFAULT_PHRASE_GAP = RationalTime(value=1, timescale=2)


def build_phrases(
    transcript: Transcript,
    *,
    phrase_gap: RationalTime = DEFAULT_PHRASE_GAP,
) -> Transcript:
    if phrase_gap.value < 0:
        raise ValueError("phrase gap cannot be negative")
    groups: list[list[TranscriptWord]] = []
    current: list[TranscriptWord] = []
    for word in transcript.words:
        if current:
            gap = word.source_range.start - current[-1].source_range.end
            if gap >= phrase_gap or word.speaker_id != current[-1].speaker_id:
                groups.append(current)
                current = []
        current.append(word)
    if current:
        groups.append(current)
    phrases = [
        _phrase(transcript.media_id, position, words) for position, words in enumerate(groups)
    ]
    return transcript.model_copy(update={"phrases": phrases}, deep=True)


def cuts_inside_words(transcript: Transcript, times: list[RationalTime]) -> list[RationalTime]:
    return [
        time
        for time in times
        if any(word.source_range.start < time < word.source_range.end for word in transcript.words)
    ]


def nearest_word_boundary(
    transcript: Transcript,
    requested: RationalTime,
    *,
    edge: str,
) -> RationalTime | None:
    boundaries = sorted(
        {
            word.source_range.start if edge == "in" else word.source_range.end
            for word in transcript.words
        }
    )
    if not boundaries:
        return None
    return min(boundaries, key=lambda value: (abs(value.fraction - requested.fraction), value))


def _phrase(media_id: str, position: int, words: list[TranscriptWord]) -> TranscriptPhrase:
    text = " ".join(word.punctuated_text or word.text for word in words).strip()
    kind = "question" if text.endswith("?") else "sentence"
    confidences = [word.confidence for word in words]
    confidence = conservative_confidence(confidences, basis=EvidenceKind.DERIVED)
    if not confidences:
        confidence = Confidence(score=0, basis=EvidenceKind.DERIVED, calibration="no_words")
    return TranscriptPhrase(
        id=f"{media_id}:phrase:{position:06d}",
        text=text,
        source_range=TimeRange.from_start_end(
            words[0].source_range.start, words[-1].source_range.end
        ),
        word_ids=[word.id for word in words],
        speaker_id=words[0].speaker_id,
        kind=cast(
            Literal[
                "sentence",
                "question",
                "claim",
                "punchline",
                "topic_change",
                "false_start",
                "repeated_attempt",
                "audio_event",
                "unknown",
            ],
            kind,
        ),
        confidence=confidence,
    )
