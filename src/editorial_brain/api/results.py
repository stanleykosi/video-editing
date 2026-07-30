"""Strict public facade results."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from editorial_brain.core.models import (
    BrainModel,
    CandidateAssembly,
    EditorialPlan,
    EditorialVariant,
    MediaUnderstandingIndex,
    ReferenceEditProfile,
    SelectCandidate,
    StoryMap,
)
from editorial_brain.knowledge.models import (
    ConsolidatedKnowledgeBase,
    TasteProfile,
)
from editorial_brain.policies.models import EditorialDirective
from video_engine.api import Project, TimelinePatch


class AnalysisResult(BrainModel):
    index: MediaUnderstandingIndex
    artifact_path: str
    cache_hit: bool = False


class StoryResult(BrainModel):
    story: StoryMap
    artifact_path: str | None = None


class SelectsResult(BrainModel):
    candidates: list[SelectCandidate]
    by_beat: dict[str, list[str]]
    artifact_path: str | None = None


class PlanSet(BrainModel):
    variants: list[EditorialVariant] = Field(min_length=1)

    @model_validator(mode="after")
    def ordered_ranks(self) -> PlanSet:
        expected = list(range(1, len(self.variants) + 1))
        if [variant.rank for variant in self.variants] != expected:
            raise ValueError("variants must be ordered with contiguous ranks")
        return self

    @property
    def best(self) -> EditorialPlan:
        return self.variants[0].plan


class CompilationResult(BrainModel):
    mode: Literal["project", "patch"]
    project: Project | None = None
    patch: TimelinePatch | None = None
    validated_project: Project
    compiled_plan: EditorialPlan
    decision_operation_map: dict[str, list[int]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def selected_output_exists(self) -> CompilationResult:
        if self.mode == "project" and self.project is None:
            raise ValueError("project compilation must return project")
        if self.mode == "patch" and self.patch is None:
            raise ValueError("patch compilation must return patch")
        return self


class ExplanationResult(BrainModel):
    plan_id: str
    summary: str
    decisions: list[dict[str, object]]


class ReferenceAnalysisResult(BrainModel):
    profile: ReferenceEditProfile
    artifact_path: str | None = None


class KnowledgeResult(BrainModel):
    consolidated_base: ConsolidatedKnowledgeBase | None = None
    taste_profile: TasteProfile | None = None
    directives: list[EditorialDirective] = Field(default_factory=list)


class BenchmarkMetric(BrainModel):
    name: str
    value: float
    passed: bool | None = None
    category: Literal["technical", "editorial", "subjective"]


class BenchmarkScenarioResult(BrainModel):
    scenario_id: str
    metrics: list[BenchmarkMetric]
    passed: bool
    elapsed_seconds: float = Field(ge=0)


class BenchmarkResult(BrainModel):
    scenarios: list[BenchmarkScenarioResult]
    passed: bool
    report_path: str | None = None
    deterministic_fingerprint: str


class PlanningArtifacts(BrainModel):
    assemblies: list[CandidateAssembly]
    pass_artifact_paths: list[str]


__all__ = [
    "AnalysisResult",
    "BenchmarkMetric",
    "BenchmarkResult",
    "BenchmarkScenarioResult",
    "CompilationResult",
    "ExplanationResult",
    "KnowledgeResult",
    "PlanSet",
    "PlanningArtifacts",
    "ReferenceAnalysisResult",
    "SelectsResult",
    "StoryResult",
]
