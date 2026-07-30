"""Stable candidate-assembly ranking."""

from editorial_brain.core.models import CandidateAssembly


def rank_assemblies(values: list[CandidateAssembly]) -> list[CandidateAssembly]:
    return sorted(values, key=lambda item: (-item.score.overall, item.id))
