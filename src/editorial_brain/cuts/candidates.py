"""Structural cut-point enumeration; no arbitrary timestamps."""

from __future__ import annotations

from collections import defaultdict
from typing import Literal, cast

from editorial_brain.core.models import (
    CutPointCandidate,
    EvidenceKind,
    EvidenceRef,
    MediaUnderstandingIndex,
)


def generate_cut_points(index: MediaUnderstandingIndex) -> list[CutPointCandidate]:
    points: list[CutPointCandidate] = []
    for transcript in index.transcripts:
        for word in transcript.words:
            evidence = _word_evidence(index, transcript.id, word.id)
            points.extend(
                [
                    CutPointCandidate(
                        id=f"cut-point:{word.id}:in",
                        media_id=transcript.media_id,
                        time=word.source_range.start,
                        kind="word",
                        edge="in",
                        strength=0.9,
                        evidence=evidence,
                    ),
                    CutPointCandidate(
                        id=f"cut-point:{word.id}:out",
                        media_id=transcript.media_id,
                        time=word.source_range.end,
                        kind="word",
                        edge="out",
                        strength=0.9,
                        evidence=evidence,
                    ),
                ]
            )
        for phrase in transcript.phrases:
            evidence = _phrase_evidence(index, transcript.id, phrase.id)
            points.extend(
                [
                    CutPointCandidate(
                        id=f"cut-point:{phrase.id}:in",
                        media_id=transcript.media_id,
                        time=phrase.source_range.start,
                        kind="sentence" if phrase.kind in {"sentence", "question"} else "phrase",
                        edge="in",
                        strength=1,
                        evidence=evidence,
                    ),
                    CutPointCandidate(
                        id=f"cut-point:{phrase.id}:out",
                        media_id=transcript.media_id,
                        time=phrase.source_range.end,
                        kind="sentence" if phrase.kind in {"sentence", "question"} else "phrase",
                        edge="out",
                        strength=1,
                        evidence=evidence,
                    ),
                ]
            )
    for boundary in index.shot_boundaries:
        points.append(
            CutPointCandidate(
                id=f"cut-point:{boundary.id}",
                media_id=boundary.media_id,
                time=boundary.time,
                kind="shot",
                strength=boundary.strength,
                evidence=boundary.evidence,
            )
        )
    for pause in index.pauses:
        points.extend(
            [
                CutPointCandidate(
                    id=f"cut-point:{pause.id}:in",
                    media_id=pause.media_id,
                    time=pause.source_range.start,
                    kind="pause",
                    edge="out",
                    strength=0.8 if not pause.protected else 0.35,
                    evidence=pause.evidence,
                ),
                CutPointCandidate(
                    id=f"cut-point:{pause.id}:out",
                    media_id=pause.media_id,
                    time=pause.source_range.end,
                    kind="pause",
                    edge="in",
                    strength=0.8 if not pause.protected else 0.35,
                    evidence=pause.evidence,
                ),
            ]
        )
    for event in index.audio_events:
        if event.kind != "transient":
            continue
        points.append(
            CutPointCandidate(
                id=f"cut-point:{event.id}",
                media_id=event.media_id,
                time=event.source_range.start,
                kind="audio_transient",
                strength=min(1, event.energy * 10),
                evidence=event.evidence,
            )
        )
    for music_event in index.music_events:
        points.append(
            CutPointCandidate(
                id=f"cut-point:{music_event.id}",
                media_id=music_event.media_id,
                time=music_event.source_range.start,
                kind="music_bar" if music_event.kind in {"bar", "downbeat"} else "music_beat",
                strength=music_event.strength,
                evidence=_music_evidence(index, music_event.id),
            )
        )
    for shot in index.shots:
        points.extend(
            [
                CutPointCandidate(
                    id=f"cut-point:{shot.id}:safe-in",
                    media_id=shot.media_id,
                    time=shot.inner_usable_range.start,
                    kind="source_handle",
                    edge="in",
                    strength=0.95,
                    evidence=shot.evidence,
                ),
                CutPointCandidate(
                    id=f"cut-point:{shot.id}:safe-out",
                    media_id=shot.media_id,
                    time=shot.inner_usable_range.end,
                    kind="source_handle",
                    edge="out",
                    strength=0.95,
                    evidence=shot.evidence,
                ),
            ]
        )
        for action_position, action in enumerate(shot.actions):
            for edge, time, kind in [
                ("in", action.source_range.start, "motion_start"),
                ("out", action.source_range.end, "motion_end"),
            ]:
                points.append(
                    CutPointCandidate(
                        id=f"cut-point:{shot.id}:action:{action_position}:{edge}",
                        media_id=shot.media_id,
                        time=time,
                        kind=cast(Literal["motion_start", "motion_end"], kind),
                        edge=cast(Literal["in", "out"], edge),
                        strength=action.confidence.score,
                        evidence=shot.evidence,
                    )
                )
        for reaction in shot.reactions:
            points.extend(
                [
                    CutPointCandidate(
                        id=f"cut-point:{reaction.id}:in",
                        media_id=shot.media_id,
                        time=reaction.source_range.start,
                        kind="reaction_start",
                        edge="in",
                        strength=reaction.salience,
                        evidence=shot.evidence,
                    ),
                    CutPointCandidate(
                        id=f"cut-point:{reaction.id}:out",
                        media_id=shot.media_id,
                        time=reaction.source_range.end,
                        kind="reaction_end",
                        edge="out",
                        strength=reaction.salience,
                        evidence=shot.evidence,
                    ),
                ]
            )
    return _stable_deduplicate(points)


def _stable_deduplicate(points: list[CutPointCandidate]) -> list[CutPointCandidate]:
    grouped: dict[tuple[str, object, str], list[CutPointCandidate]] = defaultdict(list)
    for point in points:
        grouped[(point.media_id, point.time.fraction, point.edge)].append(point)
    selected = [
        sorted(values, key=lambda value: (-value.strength, value.id))[0]
        for _, values in sorted(
            grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2])
        )
    ]
    return selected


def _word_evidence(
    index: MediaUnderstandingIndex, transcript_id: str, word_id: str
) -> list[EvidenceRef]:
    return [
        ref
        for ref in index.evidence.refs
        if ref.transcript_id == transcript_id and ref.transcript_word_id == word_id
    ] or _transcript_provider_evidence(index, transcript_id, word_id=word_id)


def _phrase_evidence(
    index: MediaUnderstandingIndex, transcript_id: str, phrase_id: str
) -> list[EvidenceRef]:
    return [
        ref
        for ref in index.evidence.refs
        if ref.transcript_id == transcript_id and ref.transcript_phrase_id == phrase_id
    ] or _transcript_provider_evidence(index, transcript_id, phrase_id=phrase_id)


def _transcript_provider_evidence(
    index: MediaUnderstandingIndex,
    transcript_id: str,
    *,
    word_id: str | None = None,
    phrase_id: str | None = None,
) -> list[EvidenceRef]:
    transcript = next(item for item in index.transcripts if item.id == transcript_id)
    if transcript.provider_evidence is None:
        raise ValueError(f"transcript {transcript_id!r} has no provider evidence")
    source_range = (
        next(word.source_range for word in transcript.words if word.id == word_id)
        if word_id
        else next(phrase.source_range for phrase in transcript.phrases if phrase.id == phrase_id)
    )
    return [
        EvidenceRef(
            id=f"evidence:{word_id or phrase_id}",
            kind=EvidenceKind.MODEL_INFERRED,
            media_id=transcript.media_id,
            media_sha256=transcript.media_sha256,
            source_range=source_range,
            transcript_id=transcript.id,
            transcript_word_id=word_id,
            transcript_phrase_id=phrase_id,
            provider_evidence=transcript.provider_evidence,
            analysis_version=index.analysis_version,
            confidence=(
                next(word.confidence for word in transcript.words if word.id == word_id)
                if word_id
                else next(
                    phrase.confidence for phrase in transcript.phrases if phrase.id == phrase_id
                )
            ),
            summary="word-timed transcription boundary",
        )
    ]


def _music_evidence(index: MediaUnderstandingIndex, event_id: str) -> list[EvidenceRef]:
    suffix = event_id.split(":")[-1]
    refs = [
        ref for ref in index.evidence.refs if ref.audio_window_id and suffix in ref.audio_window_id
    ]
    if not refs:
        raise ValueError(f"music event {event_id!r} lacks source evidence")
    return refs
