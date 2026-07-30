"""Deterministic script-to-word alignment with exact narration ranges."""

from __future__ import annotations

import re

from pydantic import Field

from editorial_brain.core.models import BrainModel, Confidence, EvidenceKind, Transcript
from video_engine.api import TimeRange

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9']+")


class ScriptTokenAlignment(BrainModel):
    script_index: int = Field(ge=0)
    script_token: str
    transcript_word_id: str | None = None
    matched: bool


class ScriptAlignment(BrainModel):
    transcript_id: str
    tokens: list[ScriptTokenAlignment]
    narration_range: TimeRange | None
    confidence: Confidence


def align_script(script: str, transcript: Transcript) -> ScriptAlignment:
    script_tokens = TOKEN_PATTERN.findall(script)
    spoken_tokens = [word.text for word in transcript.words]
    pairs = _needleman_wunsch(script_tokens, spoken_tokens)
    alignments: list[ScriptTokenAlignment] = []
    matched_word_positions: list[int] = []
    for script_index, spoken_index in pairs:
        if script_index is None:
            continue
        matched = spoken_index is not None and _normalize(
            script_tokens[script_index]
        ) == _normalize(spoken_tokens[spoken_index])
        if matched and spoken_index is not None:
            matched_word_positions.append(spoken_index)
        alignments.append(
            ScriptTokenAlignment(
                script_index=script_index,
                script_token=script_tokens[script_index],
                transcript_word_id=(
                    transcript.words[spoken_index].id
                    if matched and spoken_index is not None
                    else None
                ),
                matched=matched,
            )
        )
    narration_range = None
    if matched_word_positions:
        first = transcript.words[min(matched_word_positions)]
        last = transcript.words[max(matched_word_positions)]
        narration_range = TimeRange.from_start_end(first.source_range.start, last.source_range.end)
    ratio = len(matched_word_positions) / max(1, len(script_tokens))
    return ScriptAlignment(
        transcript_id=transcript.id,
        tokens=alignments,
        narration_range=narration_range,
        confidence=Confidence(
            score=ratio,
            basis=EvidenceKind.DERIVED,
            calibration="normalized_token_alignment",
            sample_size=len(script_tokens) or None,
        ),
    )


def _needleman_wunsch(left: list[str], right: list[str]) -> list[tuple[int | None, int | None]]:
    rows = len(left) + 1
    columns = len(right) + 1
    scores = [[0] * columns for _ in range(rows)]
    trace = [[""] * columns for _ in range(rows)]
    for row in range(1, rows):
        scores[row][0] = -row
        trace[row][0] = "up"
    for column in range(1, columns):
        scores[0][column] = -column
        trace[0][column] = "left"
    for row in range(1, rows):
        for column in range(1, columns):
            match_score = 2 if _normalize(left[row - 1]) == _normalize(right[column - 1]) else -1
            options = [
                (scores[row - 1][column - 1] + match_score, "diag"),
                (scores[row - 1][column] - 1, "up"),
                (scores[row][column - 1] - 1, "left"),
            ]
            score, direction = max(options, key=lambda value: (value[0], -options.index(value)))
            scores[row][column] = score
            trace[row][column] = direction
    pairs: list[tuple[int | None, int | None]] = []
    row = len(left)
    column = len(right)
    while row or column:
        direction = trace[row][column]
        if direction == "diag":
            pairs.append((row - 1, column - 1))
            row -= 1
            column -= 1
        elif direction == "up":
            pairs.append((row - 1, None))
            row -= 1
        else:
            pairs.append((None, column - 1))
            column -= 1
    return list(reversed(pairs))


def _normalize(value: str) -> str:
    return value.lower().strip("'_")
