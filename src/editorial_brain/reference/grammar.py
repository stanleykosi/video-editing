"""Reference grammar aggregation helpers."""

from itertools import pairwise

from editorial_brain.core.models import Shot


def scale_distribution(shots: list[Shot]) -> dict[str, float]:
    if not shots:
        return {}
    counts: dict[str, int] = {}
    for shot in shots:
        counts[shot.camera.shot_scale] = counts.get(shot.camera.shot_scale, 0) + 1
    return {key: value / len(shots) for key, value in sorted(counts.items())}


def motion_frequency(shots: list[Shot]) -> float:
    if not shots:
        return 0
    return sum(shot.motion_energy >= 0.15 for shot in shots) / len(shots)


def repetition(shots: list[Shot]) -> float:
    if len(shots) < 2:
        return 0
    repeated = sum(
        left.semantics.search_terms == right.semantics.search_terms
        and left.camera.shot_scale == right.camera.shot_scale
        for left, right in pairwise(shots)
    )
    return repeated / (len(shots) - 1)
