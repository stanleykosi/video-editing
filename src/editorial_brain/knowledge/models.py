"""Strict models for repository knowledge and routed editorial taste."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from editorial_brain.core.models import BrainModel


class KnowledgeKind(StrEnum):
    PLAYBOOK = "playbook"
    LESSON = "lesson"
    TECHNIQUE = "technique"
    PRESET = "preset"
    STYLE = "style"
    QC_CHECKLIST = "qc_checklist"


class KnowledgeItem(BrainModel):
    id: str = Field(min_length=1)
    kind: KnowledgeKind
    category: str = Field(min_length=1)
    title: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    search_terms: list[str] = Field(default_factory=list)
    use_when: list[str] = Field(default_factory=list)
    avoid_when: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def safe_path(self) -> KnowledgeItem:
        parts = self.relative_path.replace("\\", "/").split("/")
        if self.relative_path.startswith("/") or ".." in parts:
            raise ValueError("knowledge path must remain repository-relative")
        return self


class KnowledgeCatalog(BrainModel):
    knowledge_root: str
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    items: list[KnowledgeItem]
    rejected_files: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_items(self) -> KnowledgeCatalog:
        ids = [item.id for item in self.items]
        paths = [item.relative_path for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("knowledge catalog contains duplicate IDs")
        if len(paths) != len(set(paths)):
            raise ValueError("knowledge catalog contains duplicate paths")
        return self


class PrinciplePolarity(StrEnum):
    REQUIRE = "require"
    PREFER = "prefer"
    AVOID = "avoid"
    VERIFY = "verify"


class PrincipleTier(StrEnum):
    INVARIANT = "invariant"
    MEANING = "meaning"
    CONTINUITY = "continuity"
    RHYTHM = "rhythm"
    STYLE = "style"
    DECORATION = "decoration"


class PrincipleScope(StrEnum):
    STORY = "story"
    SELECT = "select"
    CUT = "cut"
    CONTINUITY = "continuity"
    RHYTHM = "rhythm"
    AUDIO_PICTURE = "audio_picture"
    DIALOGUE = "dialogue"
    PRESENTATION = "presentation"
    QC = "qc"
    WORKFLOW = "workflow"


TASTE_AXES = (
    "clarity",
    "information_density",
    "cut_energy",
    "breathing_room",
    "reaction_patience",
    "visual_proof",
    "continuity_strictness",
    "musicality",
    "novelty",
    "presentation_restraint",
    "camera_motion",
)


class PrincipleEffect(BrainModel):
    cut_adjustments: dict[str, float] = Field(default_factory=dict)
    select_adjustments: dict[str, float] = Field(default_factory=dict)
    taste_axes: dict[str, float] = Field(default_factory=dict)
    preferred_duration_multiplier: float = Field(default=1, ge=0.25, le=4)
    minimum_duration_multiplier: float = Field(default=1, ge=0.25, le=4)
    maximum_duration_multiplier: float = Field(default=1, ge=0.25, le=4)
    breathing_room_adjustment: float = Field(default=0, ge=-1, le=1)
    music_alignment_adjustment: float = Field(default=0, ge=-1, le=1)
    preserve_reactions: bool | None = None
    preserve_breaths: bool | None = None
    allow_intentional_long_holds: bool | None = None
    transition_preferences: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def known_axes(self) -> PrincipleEffect:
        unknown = sorted(set(self.taste_axes) - set(TASTE_AXES))
        if unknown:
            raise ValueError(f"unknown taste axes: {unknown}")
        if any(not -1 <= value <= 1 for value in self.taste_axes.values()):
            raise ValueError("taste-axis effects must be between -1 and 1")
        return self


class CanonicalPrinciple(BrainModel):
    id: str = Field(pattern=r"^principle:[a-f0-9]{20}$")
    statement: str = Field(min_length=8, max_length=600)
    normalized_signature: str = Field(min_length=4)
    category: str = Field(min_length=1)
    scope: PrincipleScope
    tier: PrincipleTier
    polarity: PrinciplePolarity
    context_terms: list[str] = Field(default_factory=list)
    exclusion_terms: list[str] = Field(default_factory=list)
    prerequisite_capabilities: list[str] = Field(default_factory=list)
    incompatibility_groups: list[str] = Field(default_factory=list)
    variant_group: str | None = None
    support_count: int = Field(default=1, ge=1)
    specificity: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    effect: PrincipleEffect = Field(default_factory=PrincipleEffect)


class KnowledgeConflict(BrainModel):
    id: str = Field(pattern=r"^conflict:[a-f0-9]{20}$")
    axis: str = Field(min_length=1)
    principle_ids: list[str] = Field(min_length=2)
    resolution: Literal["contextual_variant", "precedence", "neutral_fallback"]
    default_direction: float = Field(ge=-1, le=1)
    reason_code: str = Field(min_length=1)
    unresolved: bool = False


class TechniqueRecipe(BrainModel):
    id: str = Field(pattern=r"^recipe:[a-f0-9]{20}$")
    name: str = Field(min_length=3, max_length=160)
    category: str = Field(min_length=1)
    applicability_terms: list[str] = Field(default_factory=list)
    exclusion_terms: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1, max_length=20)
    prerequisite_capabilities: list[str] = Field(default_factory=list)
    incompatibility_groups: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class QualityGate(BrainModel):
    id: str = Field(pattern=r"^gate:[a-f0-9]{20}$")
    assertion: str = Field(min_length=8, max_length=600)
    category: str = Field(min_length=1)
    context_terms: list[str] = Field(default_factory=list)
    severity: Literal["blocker", "warning"]
    deterministic: bool = False


class ConsolidationStatistics(BrainModel):
    input_items: int = Field(ge=0)
    atomic_statements: int = Field(ge=0)
    canonical_principles: int = Field(ge=0)
    technique_recipes: int = Field(ge=0)
    quality_gates: int = Field(ge=0)
    duplicate_statements_removed: int = Field(ge=0)
    duplicate_clusters: int = Field(ge=0)
    conflicts_resolved: int = Field(ge=0)
    unresolved_conflicts: int = Field(ge=0)
    principle_reduction_ratio: float = Field(ge=0, le=1)
    total_construct_reduction_ratio: float = Field(ge=0, le=1)


class ConsolidatedKnowledgeBase(BrainModel):
    version: Literal["1.0.0"] = "1.0.0"
    compiler_version: Literal["source-neutral-v1"] = "source-neutral-v1"
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    principles: list[CanonicalPrinciple]
    recipes: list[TechniqueRecipe] = Field(default_factory=list)
    gates: list[QualityGate] = Field(default_factory=list)
    conflicts: list[KnowledgeConflict] = Field(default_factory=list)
    statistics: ConsolidationStatistics

    @model_validator(mode="after")
    def valid_graph(self) -> ConsolidatedKnowledgeBase:
        ids = [principle.id for principle in self.principles]
        signatures = [principle.normalized_signature for principle in self.principles]
        if len(ids) != len(set(ids)):
            raise ValueError("consolidated base contains duplicate principle IDs")
        if len(signatures) != len(set(signatures)):
            raise ValueError("consolidated base contains duplicate semantic signatures")
        known = set(ids)
        for conflict in self.conflicts:
            if not set(conflict.principle_ids) <= known:
                raise ValueError("conflict references an unknown principle")
        if any(conflict.unresolved for conflict in self.conflicts):
            raise ValueError("consolidated base contains unresolved conflicts")
        if len({recipe.id for recipe in self.recipes}) != len(self.recipes):
            raise ValueError("consolidated base contains duplicate recipe IDs")
        if len({gate.id for gate in self.gates}) != len(self.gates):
            raise ValueError("consolidated base contains duplicate gate IDs")
        return self


class TasteSelection(BrainModel):
    principle_id: str
    score: float = Field(ge=0)
    reasons: list[str] = Field(min_length=1)


class TasteProfile(BrainModel):
    version: Literal["1.0.0"] = "1.0.0"
    id: str = Field(pattern=r"^taste:[a-f0-9]{20}$")
    brief_id: str = Field(min_length=1)
    base_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_profile_id: str | None = None
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    axes: dict[str, float]
    selected: list[TasteSelection]
    enabled_recipe_ids: list[str] = Field(default_factory=list)
    active_gate_ids: list[str] = Field(default_factory=list)
    rejected: dict[str, str] = Field(default_factory=dict)
    conflict_resolutions: dict[str, str] = Field(default_factory=dict)
    reference_influence: float = Field(default=0, ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def exact_axes(self) -> TasteProfile:
        if set(self.axes) != set(TASTE_AXES):
            raise ValueError("taste profile must contain every canonical axis exactly once")
        if any(not -1 <= value <= 1 for value in self.axes.values()):
            raise ValueError("taste profile axes must be between -1 and 1")
        return self
