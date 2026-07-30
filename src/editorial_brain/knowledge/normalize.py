"""Source-neutral normalization and deterministic semantic similarity."""

from __future__ import annotations

import math
import re

TOKEN = re.compile(r"[a-z0-9][a-z0-9'-]+")
URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
PATH = re.compile(r"(?:knowledge|research|transcripts|source_notes)/\S+", re.IGNORECASE)
MARKUP = re.compile(r"[`*_#>|]+")

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "then",
    "this",
    "to",
    "use",
    "when",
    "with",
}

ALIASES = {
    "audience": "viewer",
    "viewers": "viewer",
    "footage": "shot",
    "shots": "shot",
    "clips": "shot",
    "voice-over": "narration",
    "voiceover": "narration",
    "dialog": "dialogue",
    "subtitles": "caption",
    "captions": "caption",
    "cutaway": "broll",
    "cutaways": "broll",
    "b-roll": "broll",
    "sound-effects": "sfx",
    "transitions": "transition",
    "reactions": "reaction",
    "pauses": "pause",
    "beats": "beat",
}


def sanitize_statement(value: str) -> str:
    """Remove ingestion provenance and markup while preserving editorial meaning."""
    value = URL.sub("", value)
    value = PATH.sub("", value)
    value = MARKUP.sub("", value)
    value = re.sub(r"\s+", " ", value).strip(" -:;,.")
    return value[:600]


def semantic_tokens(value: str) -> tuple[str, ...]:
    values: list[str] = []
    for raw in TOKEN.findall(sanitize_statement(value).lower()):
        token = ALIASES.get(raw, raw)
        token = _stem(token)
        if token not in STOP_WORDS and len(token) > 1:
            values.append(token)
    return tuple(sorted(set(values)))


def similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    a, b = set(left), set(right)
    if not a or not b:
        return 0
    overlap = len(a & b)
    jaccard = overlap / len(a | b)
    containment = overlap / min(len(a), len(b))
    length_ratio = min(len(a), len(b)) / max(len(a), len(b))
    return max(jaccard, containment * math.sqrt(length_ratio))


def _stem(token: str) -> str:
    if len(token) > 6 and token.endswith("ingly"):
        return token[:-5]
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 5 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token
