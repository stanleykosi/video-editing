"""Evidence-backed beat construction for script-led and source-led edits."""

from __future__ import annotations

import re

from editorial_brain.core.models import (
    Confidence,
    EditorialBrief,
    EvidenceKind,
    EvidenceRef,
    MediaUnderstandingIndex,
    NarrativeFunction,
    PauseEvent,
    StoryBeat,
    StoryMap,
    Transcript,
    TranscriptPhrase,
)
from editorial_brain.story.narrative import narrative_function
from editorial_brain.story.requirements import audio_requirements, visual_requirements
from editorial_brain.story.script_alignment import align_script
from video_engine.api import RationalTime, TimeRange

SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")


def build_story_map(
    brief: EditorialBrief,
    index: MediaUnderstandingIndex,
) -> StoryMap:
    if brief.script_text:
        return _script_story(brief, index)
    events = _source_events(index)
    if not events:
        raise ValueError("source-led story requires transcript phrases or supplied script")
    beats: list[StoryBeat] = []
    previous_id: str | None = None
    phrase_count = sum(isinstance(item[2], TranscriptPhrase) for item in events)
    phrase_position = 0
    for position, (media_id, _, event) in enumerate(events):
        beat_id = f"beat:{position:04d}"
        evidence = _event_evidence(index, media_id, event)
        if isinstance(event, PauseEvent):
            beat = StoryBeat(
                id=beat_id,
                function=(
                    NarrativeFunction.REACTION
                    if event.classification.value in {"reaction_hold", "comedic_pause"}
                    else NarrativeFunction.BREATHING_SPACE
                ),
                purpose=f"Preserve {event.classification.value.replace('_', ' ')}",
                importance=0.8 if event.protected else 0.3,
                mandatory=event.protected,
                evidence=evidence,
                target_duration=event.source_range.duration,
                must_follow=[previous_id] if previous_id else [],
                audio_requirements=[],
                confidence=event.confidence,
            )
            beats.append(beat)
            previous_id = beat_id
            continue
        phrase = event
        beat = StoryBeat(
            id=beat_id,
            function=narrative_function(phrase, position=phrase_position, total=phrase_count),
            purpose=phrase.text,
            importance=max(0.3, phrase.emphasis),
            mandatory=not (
                phrase.kind in {"false_start", "repeated_attempt"}
                and phrase.confidence.score >= 0.7
            ),
            source_text=phrase.text,
            source_phrase_kind=phrase.kind,
            evidence=evidence,
            target_duration=phrase.source_range.duration,
            must_follow=[previous_id] if previous_id else [],
            visual_requirements=visual_requirements(
                beat_id,
                phrase.text,
                narration_range=phrase.source_range,
                phrase=phrase,
            ),
            audio_requirements=audio_requirements(
                beat_id,
                narration_range=phrase.source_range,
                has_narration=False,
                source_dialogue=True,
            ),
            confidence=phrase.confidence,
        )
        beats.append(beat)
        previous_id = beat_id
        phrase_position += 1
    return StoryMap(brief_id=brief.id, beats=beats)


def _source_events(
    index: MediaUnderstandingIndex,
) -> list[tuple[str, RationalTime, TranscriptPhrase | PauseEvent]]:
    synchronized_targets = {item.target_media_id for item in index.synchronizations}
    transcripts = [
        transcript
        for transcript in index.transcripts
        if transcript.media_id not in synchronized_targets
    ] or index.transcripts
    events: list[tuple[str, RationalTime, TranscriptPhrase | PauseEvent]] = [
        (transcript.media_id, phrase.source_range.start, phrase)
        for transcript in transcripts
        for phrase in transcript.phrases
    ]
    primary_media = {transcript.media_id for transcript in transcripts}
    events.extend(
        (pause.media_id, pause.source_range.start, pause)
        for pause in index.pauses
        if pause.protected and pause.media_id in primary_media
    )
    return sorted(events, key=lambda item: (item[0], item[1], item[2].id))


def _event_evidence(
    index: MediaUnderstandingIndex,
    media_id: str,
    event: TranscriptPhrase | PauseEvent,
) -> list[EvidenceRef]:
    if isinstance(event, PauseEvent):
        return event.evidence
    return [
        ref
        for ref in index.evidence.refs
        if ref.media_id == media_id and ref.transcript_phrase_id == event.id
    ]


def _script_story(brief: EditorialBrief, index: MediaUnderstandingIndex) -> StoryMap:
    assert brief.script_text is not None
    sentences = [
        sentence.strip()
        for sentence in SENTENCE_PATTERN.split(brief.script_text)
        if sentence.strip()
    ]
    if not sentences:
        raise ValueError("script text contains no usable sentences")
    transcript = _narration_transcript(brief, index)
    transcript_cursor = 0
    beats: list[StoryBeat] = []
    previous_id: str | None = None
    for position, sentence in enumerate(sentences):
        beat_id = f"beat:{position:04d}"
        narration_range: TimeRange | None = None
        confidence = Confidence(
            score=1,
            basis=EvidenceKind.USER_SUPPLIED,
            calibration="script_supplied",
        )
        beat_evidence: list[EvidenceRef] = []
        if transcript is not None:
            window = transcript.model_copy(
                update={"words": transcript.words[transcript_cursor:], "phrases": []},
                deep=True,
            )
            alignment = align_script(sentence, window)
            narration_range = alignment.narration_range
            confidence = alignment.confidence
            matched_ids = {
                token.transcript_word_id
                for token in alignment.tokens
                if token.transcript_word_id is not None
            }
            matched_positions = [
                position for position, word in enumerate(transcript.words) if word.id in matched_ids
            ]
            beat_evidence = [
                ref
                for ref in index.evidence.refs
                if ref.transcript_id == transcript.id and ref.transcript_word_id in matched_ids
            ]
            if matched_positions:
                transcript_cursor = max(matched_positions) + 1
        target = (
            narration_range.duration
            if narration_range is not None
            else RationalTime(value=max(1, len(sentence.split())), timescale=3)
        )
        function = _script_function(position, len(sentences))
        beats.append(
            StoryBeat(
                id=beat_id,
                function=function,
                purpose=sentence,
                importance=(
                    1 if function in {NarrativeFunction.HOOK, NarrativeFunction.PAYOFF} else 0.7
                ),
                source_text=sentence,
                evidence=beat_evidence,
                required_information=[sentence],
                visual_requirements=visual_requirements(
                    beat_id,
                    sentence,
                    narration_range=narration_range,
                    evidence=beat_evidence,
                ),
                audio_requirements=audio_requirements(
                    beat_id,
                    narration_range=narration_range,
                    has_narration=transcript is not None,
                ),
                target_duration=target,
                must_follow=[previous_id] if previous_id else [],
                confidence=confidence,
            )
        )
        previous_id = beat_id
    return StoryMap(brief_id=brief.id, beats=beats)


def _script_function(position: int, total: int) -> NarrativeFunction:
    if position == 0:
        return NarrativeFunction.HOOK
    if position == total - 1:
        return NarrativeFunction.PAYOFF
    return NarrativeFunction.CONTEXT


def _narration_transcript(
    brief: EditorialBrief, index: MediaUnderstandingIndex
) -> Transcript | None:
    if brief.narration_transcript_id:
        return next(
            (
                transcript
                for transcript in index.transcripts
                if transcript.id == brief.narration_transcript_id
            ),
            None,
        )
    if brief.narration_media_id:
        return next(
            (
                transcript
                for transcript in index.transcripts
                if transcript.media_id == brief.narration_media_id
            ),
            None,
        )
    return index.transcripts[0] if index.transcripts else None
