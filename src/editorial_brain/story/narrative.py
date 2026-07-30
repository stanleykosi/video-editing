"""Narrative function assignment from source evidence."""

from editorial_brain.core.models import NarrativeFunction, TranscriptPhrase


def narrative_function(phrase: TranscriptPhrase, *, position: int, total: int) -> NarrativeFunction:
    if phrase.kind == "question":
        return NarrativeFunction.QUESTION
    if phrase.kind == "claim":
        return NarrativeFunction.EVIDENCE
    if phrase.kind == "punchline":
        return NarrativeFunction.PAYOFF
    if phrase.kind == "topic_change":
        return NarrativeFunction.TRANSITION
    if position == 0:
        return NarrativeFunction.HOOK
    if position == total - 1:
        return NarrativeFunction.RESOLUTION
    return NarrativeFunction.CONTEXT
