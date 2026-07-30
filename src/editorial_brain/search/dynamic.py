"""Deterministic duration-constrained dynamic programming."""

from __future__ import annotations

from editorial_brain.core.models import SelectCandidate


def duration_knapsack(
    candidates: list[SelectCandidate], target_milliseconds: int
) -> list[SelectCandidate]:
    if target_milliseconds <= 0:
        raise ValueError("target duration must be positive")
    states: dict[int, tuple[float, tuple[SelectCandidate, ...]]] = {0: (0, ())}
    for candidate in sorted(candidates, key=lambda item: item.id):
        milliseconds = max(1, round(float(candidate.inner_usable_range.duration.fraction) * 1000))
        additions: dict[int, tuple[float, tuple[SelectCandidate, ...]]] = {}
        for duration, (score, selected) in states.items():
            new_duration = duration + milliseconds
            if new_duration > target_milliseconds * 2:
                continue
            choice = (score + candidate.score.overall, (*selected, candidate))
            current = states.get(new_duration) or additions.get(new_duration)
            if current is None or _choice_rank(choice) < _choice_rank(current):
                additions[new_duration] = choice
        states.update(additions)
    _, best = min(
        states.items(),
        key=lambda item: (
            abs(item[0] - target_milliseconds),
            -item[1][0],
            tuple(candidate.id for candidate in item[1][1]),
        ),
    )
    return list(best[1])


def _choice_rank(
    choice: tuple[float, tuple[SelectCandidate, ...]],
) -> tuple[float, tuple[str, ...]]:
    return (-choice[0], tuple(item.id for item in choice[1]))
