"""Restrained motivated transition recommendation."""

from editorial_brain.core.models import ContinuityScore, NarrativeFunction


def transition_for_cut(
    continuity: ContinuityScore,
    *,
    next_function: NarrativeFunction,
    time_jump: bool = False,
) -> str:
    if time_jump and next_function in {NarrativeFunction.TRANSITION, NarrativeFunction.CONTEXT}:
        return "dissolve"
    if continuity.motivated_discontinuity:
        return "cut"
    return "cut"
