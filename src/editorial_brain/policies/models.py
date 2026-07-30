"""Typed algorithm policies, not editing-knowledge content."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import Field, model_validator

from editorial_brain.core.models import BrainModel, EditorialBrief
from video_engine.api import RationalTime

CUT_DIMENSIONS = (
    "semantic_completeness",
    "story_progression",
    "visual_relevance",
    "visual_continuity",
    "action_continuity",
    "screen_direction",
    "shot_scale_compatibility",
    "composition_compatibility",
    "motion_compatibility",
    "audio_continuity",
    "speech_integrity",
    "reaction_preservation",
    "emotional_continuity",
    "rhythm",
    "information_density",
    "visual_novelty",
    "shot_quality",
    "source_handle_safety",
    "style_profile_fit",
    "technical_feasibility",
)


class CutScoringPolicy(BrainModel):
    weights: dict[str, float]
    minimum_overall: float = Field(default=0.35, ge=0, le=1)
    semantic_model_weight: float = Field(default=0.2, ge=0, le=1)

    @model_validator(mode="after")
    def exact_dimensions(self) -> CutScoringPolicy:
        if set(self.weights) != set(CUT_DIMENSIONS):
            missing = sorted(set(CUT_DIMENSIONS) - set(self.weights))
            extra = sorted(set(self.weights) - set(CUT_DIMENSIONS))
            raise ValueError(f"cut weights mismatch; missing={missing}, extra={extra}")
        if any(weight < 0 for weight in self.weights.values()) or not sum(self.weights.values()):
            raise ValueError("cut weights must be nonnegative with positive total")
        return self


class SelectScoringPolicy(BrainModel):
    semantic_relevance: float = Field(default=0.25, ge=0)
    visual_clarity: float = Field(default=0.15, ge=0)
    action_completeness: float = Field(default=0.1, ge=0)
    shot_quality: float = Field(default=0.15, ge=0)
    reaction_value: float = Field(default=0.1, ge=0)
    evidence_value: float = Field(default=0.15, ge=0)
    novelty: float = Field(default=0.1, ge=0)
    repetition_penalty: float = Field(default=0.2, ge=0)


class PacingPolicy(BrainModel):
    preferred_shot_duration: RationalTime
    minimum_shot_duration: RationalTime
    maximum_shot_duration: RationalTime
    allow_intentional_long_holds: bool = True
    maximum_identical_duration_run: int = Field(default=3, ge=1)
    breathing_room_weight: float = Field(default=0.15, ge=0)
    music_alignment_weight: float = Field(default=0.1, ge=0)

    @model_validator(mode="after")
    def duration_bounds(self) -> PacingPolicy:
        if self.minimum_shot_duration.value <= 0:
            raise ValueError("minimum shot duration must be positive")
        if not (
            self.minimum_shot_duration <= self.preferred_shot_duration <= self.maximum_shot_duration
        ):
            raise ValueError("preferred shot duration must be inside pacing bounds")
        return self


class DialoguePolicy(BrainModel):
    filler_policy: Literal["conservative", "balanced", "aggressive"] = "conservative"
    minimum_dead_air: RationalTime
    preserve_breaths: bool = True
    preserve_reactions: bool = True
    room_tone_required: bool = True


class EditorialPolicy(BrainModel):
    id: str
    version: str = "1.0.0"
    cut: CutScoringPolicy
    selects: SelectScoringPolicy = Field(default_factory=SelectScoringPolicy)
    pacing: PacingPolicy
    dialogue: DialoguePolicy
    top_k: int = Field(default=5, ge=1, le=100)
    beam_width: int = Field(default=12, ge=1, le=1000)
    review_threshold: float = Field(default=0.55, ge=0, le=1)
    directive_ids: list[str] = Field(default_factory=list)
    knowledge_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    knowledge_reasons: list[str] = Field(default_factory=list)
    transition_preferences: list[str] = Field(default_factory=list)
    taste_profile_id: str | None = None
    taste_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    active_principle_ids: list[str] = Field(default_factory=list)
    taste_axes: dict[str, float] = Field(default_factory=dict)
    reference_profile_id: str | None = None


class EditorialDirective(BrainModel):
    id: str
    scoring_adjustments: dict[str, float] = Field(default_factory=dict)
    select_adjustments: dict[str, float] = Field(default_factory=dict)
    hard_constraints: list[str] = Field(default_factory=list)
    soft_constraints: list[str] = Field(default_factory=list)
    technique_preferences: list[str] = Field(default_factory=list)
    transition_rules: list[str] = Field(default_factory=list)
    pacing_rules: list[str] = Field(default_factory=list)
    preferred_duration_multiplier: float = Field(default=1, ge=0.25, le=4)
    minimum_duration_multiplier: float = Field(default=1, ge=0.25, le=4)
    maximum_duration_multiplier: float = Field(default=1, ge=0.25, le=4)
    breathing_room_adjustment: float = Field(default=0, ge=-1, le=1)
    music_alignment_adjustment: float = Field(default=0, ge=-1, le=1)
    allow_intentional_long_holds: bool | None = None
    preserve_reactions: bool | None = None
    preserve_breaths: bool | None = None
    reasons: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1, ge=0, le=1)


class EditorialDirectiveProvider(ABC):
    """Provider seam for compiled, auditable editorial knowledge directives."""

    @abstractmethod
    def directives(self, brief: EditorialBrief) -> list[EditorialDirective]:
        raise NotImplementedError


def equal_cut_weights() -> dict[str, float]:
    return {dimension: 1 for dimension in CUT_DIMENSIONS}
