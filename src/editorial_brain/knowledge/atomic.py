"""Field-aware extraction of atomic source-neutral editorial statements."""

from __future__ import annotations

from dataclasses import dataclass

from editorial_brain.knowledge.models import (
    KnowledgeCatalog,
    PrinciplePolarity,
    PrincipleScope,
)
from editorial_brain.knowledge.normalize import sanitize_statement, semantic_tokens


@dataclass(frozen=True, slots=True)
class AtomicStatement:
    text: str
    category: str
    scope: PrincipleScope
    polarity: PrinciplePolarity
    tokens: tuple[str, ...]
    context_terms: tuple[str, ...]
    exclusion_terms: tuple[str, ...]


def extract_atomic_statements(catalog: KnowledgeCatalog) -> list[AtomicStatement]:
    statements: list[AtomicStatement] = []
    for item in catalog.items:
        contexts = semantic_tokens(" ".join(item.use_when))
        exclusions = semantic_tokens(" ".join(item.avoid_when))
        for value in item.rules:
            statement = _statement(value, item.category, contexts, exclusions)
            if statement is not None:
                statements.append(statement)
    return sorted(
        statements,
        key=lambda item: (item.category, item.scope, item.polarity, item.tokens, item.text),
    )


def _statement(
    value: str,
    category: str,
    contexts: tuple[str, ...],
    exclusions: tuple[str, ...],
) -> AtomicStatement | None:
    text = sanitize_statement(value)
    lower = text.lower()
    polarity = (
        PrinciplePolarity.VERIFY
        if text.endswith("?") or lower.startswith("verify:") or category == "qc"
        else PrinciplePolarity.AVOID
        if lower.startswith("avoid:")
        else PrinciplePolarity.REQUIRE
        if any(term in lower for term in ("must ", "never ", "required", "do not "))
        else PrinciplePolarity.PREFER
    )
    text = text.removeprefix("Verify:").removeprefix("Avoid:").strip()
    tokens = semantic_tokens(text)
    if len(text) < 8 or len(tokens) < 3:
        return None
    return AtomicStatement(
        text=text,
        category=category,
        scope=_scope(text, category),
        polarity=polarity,
        tokens=tokens,
        context_terms=contexts,
        exclusion_terms=exclusions,
    )


def _scope(text: str, category: str) -> PrincipleScope:
    lower = text.lower()
    if category == "qc" or any(term in lower for term in ("check", "verify", "review")):
        return PrincipleScope.QC
    if any(term in lower for term in ("dialogue", "spoken", "word", "breath", "filler")):
        return PrincipleScope.DIALOGUE
    if any(term in lower for term in ("j-cut", "l-cut", "audio bridge", "room tone")):
        return PrincipleScope.AUDIO_PICTURE
    if any(term in lower for term in ("continuity", "screen direction", "jump cut", "eyeline")):
        return PrincipleScope.CONTINUITY
    if any(term in lower for term in ("select", "best take", "strongest shot", "source range")):
        return PrincipleScope.SELECT
    if any(term in lower for term in ("cut", "trim", "transition", "edit point")):
        return PrincipleScope.CUT
    if any(term in lower for term in ("pace", "rhythm", "beat", "duration", "hold")):
        return PrincipleScope.RHYTHM
    if category in {"captions", "typography", "motion", "color", "compositing"}:
        return PrincipleScope.PRESENTATION
    if category in {"nle_workflow", "preset"}:
        return PrincipleScope.WORKFLOW
    return PrincipleScope.STORY
