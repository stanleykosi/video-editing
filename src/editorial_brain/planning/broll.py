"""Purpose-led B-roll and cutaway ranking."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from editorial_brain.core.models import BrainModel, SelectCandidate, StoryBeat

BrollPurpose = Literal[
    "visual_proof",
    "illustration",
    "context",
    "location",
    "product_detail",
    "action",
    "reaction_cover",
    "jump_cut_cover",
    "scale",
    "atmosphere",
    "comparison",
    "process",
]


class BrollPlan(BrainModel):
    beat_id: str
    select_id: str
    purpose: BrollPurpose
    phrase_relevance: float = Field(ge=0, le=1)
    timing: float = Field(ge=0, le=1)
    novelty: float = Field(ge=0, le=1)
    visual_clarity: float = Field(ge=0, le=1)
    proof_strength: float = Field(ge=0, le=1)
    overall: float = Field(ge=0, le=1)


def rank_broll(
    beat: StoryBeat,
    candidates: list[SelectCandidate],
    *,
    purpose: BrollPurpose,
) -> list[BrollPlan]:
    plans = []
    for candidate in candidates:
        relevance = candidate.score.semantic_relevance
        proof = candidate.score.evidence_value if purpose == "visual_proof" else 0.5
        overall = (
            relevance * 0.3
            + candidate.score.visual_clarity * 0.2
            + candidate.score.novelty * 0.2
            + proof * 0.2
            + candidate.score.action_completeness * 0.1
        )
        plans.append(
            BrollPlan(
                beat_id=beat.id,
                select_id=candidate.id,
                purpose=purpose,
                phrase_relevance=relevance,
                timing=1,
                novelty=candidate.score.novelty,
                visual_clarity=candidate.score.visual_clarity,
                proof_strength=proof,
                overall=overall,
            )
        )
    return sorted(plans, key=lambda item: (-item.overall, item.select_id))
