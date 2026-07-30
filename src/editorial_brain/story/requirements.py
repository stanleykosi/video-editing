"""Explicit visual/audio requirement extraction from supplied evidence."""

from __future__ import annotations

import re

from editorial_brain.core.models import (
    AudioRequirement,
    Confidence,
    EvidenceKind,
    EvidenceRef,
    RevealTiming,
    TranscriptPhrase,
    VisualRequirement,
)
from video_engine.api import RationalTime, TimeRange

VISUAL_TAG = re.compile(r"\[visual:(?P<entity>[^\]]+)\]", re.IGNORECASE)


def visual_requirements(
    beat_id: str,
    text: str,
    *,
    narration_range: TimeRange | None,
    phrase: TranscriptPhrase | None = None,
    evidence: list[EvidenceRef] | None = None,
) -> list[VisualRequirement]:
    entities = [match.group("entity").strip() for match in VISUAL_TAG.finditer(text)]
    if phrase is not None:
        entities.extend(phrase.named_visual_references)
    unique = list(dict.fromkeys(entity for entity in entities if entity))
    source_evidence = evidence or []
    return [
        VisualRequirement(
            id=f"visual-requirement:{beat_id}:{position:03d}",
            description=f"Show visible proof of {entity}",
            entity=entity,
            reveal_timing=RevealTiming.BEFORE_PHRASE,
            narration_range=narration_range,
            early_handoff=RationalTime(value=1, timescale=10),
            minimum_hold=RationalTime(value=4, timescale=5),
            evidence=source_evidence,
            confidence=Confidence(
                score=1,
                basis=(
                    EvidenceKind.USER_SUPPLIED if VISUAL_TAG.search(text) else EvidenceKind.DERIVED
                ),
                calibration="explicit_visual_reference",
            ),
        )
        for position, entity in enumerate(unique)
    ]


def audio_requirements(
    beat_id: str,
    *,
    narration_range: TimeRange | None,
    has_narration: bool,
    source_dialogue: bool = False,
) -> list[AudioRequirement]:
    if not has_narration and not source_dialogue:
        return []
    return [
        AudioRequirement(
            id=f"audio-requirement:{beat_id}:{'dialogue' if source_dialogue else 'narration'}",
            kind="dialogue" if source_dialogue else "voice_over",
            description=(
                "Preserve source dialogue without cutting spoken words"
                if source_dialogue
                else "Preserve aligned narration without cutting spoken words"
            ),
            target_range=narration_range,
        )
    ]
