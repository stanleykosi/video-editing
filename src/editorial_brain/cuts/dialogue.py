"""Context-aware dialogue edit eligibility."""

from __future__ import annotations

from editorial_brain.core.models import (
    PauseClass,
    PauseEvent,
    Transcript,
    TranscriptPhrase,
    TranscriptWord,
)
from editorial_brain.policies.models import DialoguePolicy


def removable_pause(pause: PauseEvent, *, aggressive: bool = False) -> bool:
    if pause.protected or pause.confidence.score < 0.6:
        return False
    if pause.classification in {PauseClass.DEAD_SPACE, PauseClass.TECHNICAL_DELAY}:
        return True
    return aggressive and pause.classification is PauseClass.UNKNOWN


def removable_phrase(phrase: TranscriptPhrase, *, repeated_evidence: bool) -> bool:
    if phrase.confidence.score < 0.7:
        return False
    if phrase.kind == "false_start":
        return True
    return phrase.kind == "repeated_attempt" and repeated_evidence


def removable_filler(
    word: TranscriptWord,
    transcript: Transcript,
    policy: DialoguePolicy,
) -> bool:
    """Decide from provider/context evidence, never from a token blacklist."""
    if policy.filler_policy == "conservative" or not word.is_filler_candidate:
        return False
    if word.confidence.score < 0.75:
        return False
    try:
        position = next(index for index, item in enumerate(transcript.words) if item.id == word.id)
    except StopIteration:
        return False
    if position in {0, len(transcript.words) - 1}:
        return False
    left = transcript.words[position - 1]
    right = transcript.words[position + 1]
    if left.speaker_id != word.speaker_id or right.speaker_id != word.speaker_id:
        return False
    natural_gap = right.source_range.start - left.source_range.end
    if natural_gap.value < 0:
        return False
    if policy.filler_policy == "aggressive":
        return True
    return natural_gap <= policy.minimum_dead_air


def repeated_attempt_pairs(transcript: Transcript) -> list[tuple[str, str]]:
    """Return only explicitly classified, adjacent repeated attempts."""
    pairs: list[tuple[str, str]] = []
    for left, right in zip(transcript.phrases, transcript.phrases[1:], strict=False):
        if right.kind != "repeated_attempt" or right.confidence.score < 0.7:
            continue
        if left.speaker_id == right.speaker_id:
            pairs.append((left.id, right.id))
    return pairs
