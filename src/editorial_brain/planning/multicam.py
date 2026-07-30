"""Evidence-gated multi-camera angle planning."""

from __future__ import annotations

from pydantic import Field

from editorial_brain.analysis.synchronization import SynchronizationResult
from editorial_brain.core.models import (
    BrainModel,
    MediaUnderstandingIndex,
    SelectCandidate,
    Shot,
    SpeakerSegment,
    StoryMap,
)
from editorial_brain.selects.ranking import rank_selects


class MulticamChoice(BrainModel):
    speaker_segment_id: str
    shot_id: str
    reason: str
    reaction_angle: bool = False
    confidence: float = Field(ge=0, le=1)


def plan_multicam(
    speakers: list[SpeakerSegment],
    shots: list[Shot],
    sync: list[SynchronizationResult],
) -> list[MulticamChoice]:
    if len({shot.media_id for shot in shots}) > 1 and not sync:
        raise ValueError("multi-camera planning requires measured synchronization evidence")
    choices: list[MulticamChoice] = []
    previous_shot: str | None = None
    for segment in speakers:
        overlapping = [shot for shot in shots if shot.source_range.overlaps(segment.source_range)]
        if not overlapping:
            continue
        ranked = sorted(
            overlapping,
            key=lambda shot: (
                -(shot.semantics.reaction_value if shot.id != previous_shot else 0),
                -(
                    shot.quality.sharpness
                    + shot.quality.exposure
                    + shot.quality.stability
                    + shot.quality.composition
                )
                / 4,
                shot.id,
            ),
        )
        selected = ranked[0]
        choices.append(
            MulticamChoice(
                speaker_segment_id=segment.id,
                shot_id=selected.id,
                reason=(
                    "meaningful listener reaction"
                    if selected.semantics.reaction_value >= 0.7
                    else "clearest synchronized speaker coverage"
                ),
                reaction_angle=selected.semantics.reaction_value >= 0.7,
                confidence=min(segment.confidence.score, selected.quality.confidence.score),
            )
        )
        previous_shot = selected.id
    return choices


def apply_multicam_preferences(
    story: StoryMap,
    pools: dict[str, list[SelectCandidate]],
    index: MediaUnderstandingIndex,
) -> dict[str, list[SelectCandidate]]:
    """Gate cross-camera candidates on sync and prefer evidenced speaker/reaction views."""
    if len({shot.media_id for shot in index.shots}) < 2:
        return pools
    phrases = {
        phrase.id: (transcript.media_id, phrase.speaker_id)
        for transcript in index.transcripts
        for phrase in transcript.phrases
    }
    words = {
        word.id: (transcript.media_id, word.speaker_id)
        for transcript in index.transcripts
        for word in transcript.words
    }
    shots = {shot.id: shot for shot in index.shots}
    output: dict[str, list[SelectCandidate]] = {}
    for beat in story.beats:
        source_item = next(
            (
                phrases[ref.transcript_phrase_id]
                for ref in beat.evidence
                if ref.transcript_phrase_id in phrases
            ),
            None,
        )
        if source_item is None:
            source_item = next(
                (
                    words[ref.transcript_word_id]
                    for ref in beat.evidence
                    if ref.transcript_word_id in words
                ),
                None,
            )
        if source_item is None:
            output[beat.id] = pools.get(beat.id, [])
            continue
        source_media_id, speaker_id = source_item
        adjusted: list[SelectCandidate] = []
        for candidate in pools.get(beat.id, []):
            if candidate.media_id != source_media_id and not _has_measured_sync(
                source_media_id, candidate.media_id, index
            ):
                continue
            shot = shots[candidate.shot_id]
            labels = {item.lower() for item in shot.semantics.search_terms}
            speaker_match = bool(speaker_id and f"speaker:{speaker_id.lower()}" in labels)
            reaction_cover = shot.semantics.reaction_value >= 0.7
            payoff_reaction = reaction_cover and beat.function.value in {
                "reaction",
                "payoff",
                "reveal",
            }
            bonus = (
                0.18
                if payoff_reaction
                else 0.18
                if speaker_match
                else 0.04
                if reaction_cover
                else 0
            )
            adjusted.append(
                candidate.model_copy(
                    update={
                        "score": candidate.score.model_copy(
                            update={"overall": min(1, candidate.score.overall + bonus)}
                        ),
                        "reasons": [
                            *candidate.reasons,
                            *(
                                ["synchronized active-speaker view"]
                                if speaker_match
                                else (
                                    ["synchronized meaningful reaction cover"]
                                    if reaction_cover
                                    else []
                                )
                            ),
                        ],
                    },
                    deep=True,
                )
            )
        output[beat.id] = rank_selects(adjusted or pools.get(beat.id, []))
    return output


def _has_measured_sync(
    reference_media_id: str,
    target_media_id: str,
    index: MediaUnderstandingIndex,
) -> bool:
    return any(
        {item.reference_media_id, item.target_media_id} == {reference_media_id, target_media_id}
        and item.confidence.score >= 0.4
        for item in index.synchronizations
    )
