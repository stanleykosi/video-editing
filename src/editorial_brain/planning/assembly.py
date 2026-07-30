"""Assembly pass backed by global candidate-sequence search."""

from editorial_brain.core.models import (
    CandidateAssembly,
    EditorialBrief,
    SelectCandidate,
    Shot,
    StoryMap,
)
from editorial_brain.policies.models import EditorialPolicy
from editorial_brain.search.beam import beam_search


def create_assemblies(
    story: StoryMap,
    pools: dict[str, list[SelectCandidate]],
    shots: list[Shot],
    brief: EditorialBrief,
    policy: EditorialPolicy,
    *,
    variants: int,
) -> list[CandidateAssembly]:
    return beam_search(
        story,
        pools,
        shots,
        brief,
        policy,
        variants=variants,
        seed=brief.seed,
    )
