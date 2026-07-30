"""Stable editorial variant construction."""

from editorial_brain.core.models import CandidateAssembly


def variant_differentiators(best: CandidateAssembly, alternative: CandidateAssembly) -> list[str]:
    differences: list[str] = []
    best_selects = [item.select_id for item in best.segments]
    alternative_selects = [item.select_id for item in alternative.segments]
    if best_selects != alternative_selects:
        differences.append("different source selects")
    if best.rhythm.overall != alternative.rhythm.overall:
        differences.append("different pacing/rhythm score")
    if best.score.continuity != alternative.score.continuity:
        differences.append("different continuity tradeoff")
    return differences or ["score tie resolved deterministically"]
