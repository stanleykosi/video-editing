"""Stable high-level Editorial Brain facade."""

from __future__ import annotations

import re
import time
from pathlib import Path

from pydantic import Field

from editorial_brain.analysis.media import MediaAnalysisPipeline
from editorial_brain.api.exceptions import EditorialBrainError, EditorialErrorCode
from editorial_brain.api.results import (
    AnalysisResult,
    BenchmarkResult,
    CompilationResult,
    ExplanationResult,
    KnowledgeResult,
    PlanSet,
    ReferenceAnalysisResult,
    SelectsResult,
    StoryResult,
)
from editorial_brain.compile.patch import compile_patch
from editorial_brain.compile.validation import apply_and_validate, validate_plan_sources
from editorial_brain.core.hashing import fingerprint
from editorial_brain.core.models import (
    BrainModel,
    CandidateAssembly,
    Confidence,
    CutCandidate,
    CutPointCandidate,
    DecisionTrace,
    EditorialBrief,
    EditorialDecision,
    EditorialPlan,
    EditorialVariant,
    EvidenceKind,
    MediaUnderstandingIndex,
    ReferenceEditProfile,
    ReviewFlag,
    ReviewMode,
    SelectCandidate,
)
from editorial_brain.core.validation import validate_plan_against_index
from editorial_brain.cuts.candidates import generate_cut_points
from editorial_brain.knowledge.compiler import apply_directives
from editorial_brain.knowledge.models import ConsolidatedKnowledgeBase
from editorial_brain.knowledge.provider import RepositoryKnowledgeDirectiveProvider
from editorial_brain.observability.costs import aggregate_usage
from editorial_brain.observability.trace import RunTrace
from editorial_brain.planning.assembly import create_assemblies
from editorial_brain.planning.audio_picture import plan_audio_picture
from editorial_brain.planning.cut_planning import score_assembly_cuts
from editorial_brain.planning.fine_cut import refine_assembly
from editorial_brain.planning.multicam import apply_multicam_preferences
from editorial_brain.planning.narration import reveal_timing_violations
from editorial_brain.planning.passes import make_pass_artifact
from editorial_brain.planning.picture import assign_motivated_transitions, assign_picture_roles
from editorial_brain.planning.variants import variant_differentiators
from editorial_brain.policies.models import EditorialDirectiveProvider, EditorialPolicy
from editorial_brain.policies.reference import apply_reference_priors
from editorial_brain.policies.registry import PolicyRegistry
from editorial_brain.providers.base import SemanticProvider, TranscriptionProvider, VisionProvider
from editorial_brain.reference.analyzer import ReferenceAnalyzer
from editorial_brain.rhythm.pacing import samples_from_segments, score_rhythm
from editorial_brain.selects.generator import generate_selects
from editorial_brain.storage.artifacts import ArtifactStore
from editorial_brain.storage.cache import BrainCache, CacheIdentity
from editorial_brain.story.beats import build_story_map
from editorial_brain.story.structure import refine_story_map
from editorial_brain.understanding.shot_semantics import enrich_shot_semantics
from editorial_brain.understanding.speech_semantics import enrich_speech_semantics
from video_engine.api import Project, TimeRange, VideoEngine


class EditorialBrain:
    """Evidence-first editorial analysis, planning, search, and compilation."""

    def __init__(
        self,
        project_root: Path | str,
        *,
        transcription_provider: TranscriptionProvider | None = None,
        vision_provider: VisionProvider | None = None,
        semantic_provider: SemanticProvider | None = None,
        directive_provider: EditorialDirectiveProvider | None = None,
        policies: PolicyRegistry | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.artifacts = ArtifactStore(self.project_root)
        self.cache = BrainCache(self.artifacts.root / "cache")
        self.transcription_provider = transcription_provider
        self.vision_provider = vision_provider
        self.semantic_provider = semantic_provider
        self.directive_provider = directive_provider or RepositoryKnowledgeDirectiveProvider(
            self.project_root
        )
        self.policies = policies or PolicyRegistry()

    @classmethod
    def from_environment(
        cls, project_root: Path | str, *, env_file: Path | None = None
    ) -> EditorialBrain:
        """Build production providers, preferring API credentials then a local agent."""
        import os

        from dotenv import dotenv_values

        from editorial_brain.providers.codex_agent import CodexAgentProvider
        from editorial_brain.providers.deepgram import DeepgramTranscriptionProvider
        from editorial_brain.providers.openai_provider import OpenAIProvider

        root = Path(project_root).resolve()
        resolved_env_file = (env_file or root / ".env").resolve()
        openai = OpenAIProvider(env_file=resolved_env_file)
        semantic: SemanticProvider
        vision: VisionProvider
        if openai.credential_configured:
            semantic = openai
            vision = openai
        else:
            configured_model = os.environ.get("EDITORIAL_BRAIN_CODEX_MODEL")
            if resolved_env_file.is_file() and configured_model is None:
                value = dotenv_values(resolved_env_file).get("EDITORIAL_BRAIN_CODEX_MODEL")
                configured_model = value if isinstance(value, str) and value else None
            agent = CodexAgentProvider(root, model=configured_model)
            semantic = agent
            vision = agent
        return cls(
            root,
            transcription_provider=DeepgramTranscriptionProvider(env_file=resolved_env_file),
            semantic_provider=semantic,
            vision_provider=vision,
        )

    def analyze(self, *, project: Project, brief: EditorialBrief) -> AnalysisResult:
        """Build or reuse the complete evidence-backed source index."""
        started = time.monotonic()
        identity = self._analysis_identity(project, brief)
        cached = self.cache.load(identity, MediaUnderstandingIndex)
        if cached is not None:
            path = self.artifacts.write_model("analysis", _name(cached.project_id), cached)
            self._write_run_trace(
                RunTrace(
                    run_id=f"analyze-{identity.key[:20]}",
                    stage="analysis",
                    elapsed_seconds=time.monotonic() - started,
                    cache_hit=True,
                    counters={"cache_hits": 1, "cache_misses": 0},
                    provider_usage=aggregate_usage(cached.provider_evidence),
                )
            )
            return AnalysisResult(index=cached, artifact_path=str(path), cache_hit=True)
        try:
            index = MediaAnalysisPipeline(
                self.artifacts.root,
                transcription_provider=self.transcription_provider,
            ).analyze(project)
            if self.vision_provider is not None:
                index = enrich_shot_semantics(
                    index,
                    self.vision_provider,
                    instruction=(
                        "Describe only observable subjects, actions, proof, reactions, camera "
                        "grammar, and cutaway value. Encode subjects as subject:<generic label> "
                        "and actions as action:<observable action>. Do not infer identity or "
                        f"sensitive attributes. Editorial objective: {brief.objective}"
                    ),
                )
            if self.semantic_provider is not None:
                index = enrich_speech_semantics(index, self.semantic_provider)
        except Exception as exc:
            raise EditorialBrainError(
                EditorialErrorCode.ANALYSIS_FAILED,
                "media-understanding pipeline failed",
                context={"detail": str(exc)},
            ) from exc
        index = index.model_copy(
            update={
                "extensions": {
                    **index.extensions,
                    "editorial_brain:elapsed_seconds": time.monotonic() - started,
                }
            }
        )
        self.cache.store(identity, index)
        path = self.artifacts.write_model("analysis", _name(index.project_id), index)
        unavailable = index.extensions.get("editorial_brain:provider_unavailable", [])
        self._write_run_trace(
            RunTrace(
                run_id=f"analyze-{identity.key[:20]}",
                stage="analysis",
                elapsed_seconds=time.monotonic() - started,
                cache_hit=False,
                counters={
                    "cache_hits": 0,
                    "cache_misses": 1,
                    "shots": len(index.shots),
                    "transcript_words": sum(
                        len(transcript.words) for transcript in index.transcripts
                    ),
                    "provider_requests": sum(
                        item.usage.requests for item in index.provider_evidence
                    ),
                },
                provider_usage=aggregate_usage(index.provider_evidence),
                provider_failures=(
                    [str(item) for item in unavailable] if isinstance(unavailable, list) else []
                ),
            )
        )
        return AnalysisResult(index=index, artifact_path=str(path))

    def analyze_reference(self, source: Path | str) -> ReferenceAnalysisResult:
        profile = ReferenceAnalyzer(self.project_root).analyze(Path(source))
        path = self.artifacts.write_model("reference", _name(profile.id), profile)
        return ReferenceAnalysisResult(profile=profile, artifact_path=str(path))

    def knowledge(
        self, brief: EditorialBrief, *, reference: ReferenceEditProfile | None = None
    ) -> KnowledgeResult:
        """Route and compile repository knowledge for an editorial brief."""
        if isinstance(self.directive_provider, RepositoryKnowledgeDirectiveProvider):
            directives = self.directive_provider.directives_for(brief, reference=reference)
        else:
            directives = self.directive_provider.directives(brief)
        if isinstance(self.directive_provider, RepositoryKnowledgeDirectiveProvider):
            return KnowledgeResult(
                consolidated_base=self.directive_provider.last_base,
                taste_profile=self.directive_provider.last_profile,
                directives=directives,
            )
        return KnowledgeResult(directives=directives)

    def consolidate_knowledge(self) -> ConsolidatedKnowledgeBase:
        """Build and persist the strict source-neutral canonical taste base."""
        if not isinstance(self.directive_provider, RepositoryKnowledgeDirectiveProvider):
            raise ValueError("the configured directive provider has no repository knowledge base")
        base = self.directive_provider.consolidated_base()
        self.artifacts.write_model("knowledge", "consolidated-base", base)
        return base

    def build_story(
        self,
        *,
        project: Project,
        brief: EditorialBrief,
        analysis: AnalysisResult | MediaUnderstandingIndex,
    ) -> StoryResult:
        del project
        index = analysis.index if isinstance(analysis, AnalysisResult) else analysis
        story = build_story_map(brief, index)
        path = self.artifacts.write_model("story", _name(brief.id), story)
        return StoryResult(story=story, artifact_path=str(path))

    def generate_selects(
        self,
        *,
        project: Project,
        brief: EditorialBrief,
        analysis: AnalysisResult | MediaUnderstandingIndex,
    ) -> SelectsResult:
        story = self.build_story(project=project, brief=brief, analysis=analysis).story
        index = analysis.index if isinstance(analysis, AnalysisResult) else analysis
        policy = self._policy(brief, index=index)
        pools = generate_selects(
            story,
            index,
            policy,
            top_k=brief.constraints.top_k_selects,
        )
        pools = apply_multicam_preferences(story, pools, index)
        flat = [candidate for beat in story.beats for candidate in pools[beat.id]]
        path = self.artifacts.write_model(
            "selects", _name(brief.id), _SelectsArtifact(candidates=flat, pools=pools)
        )
        return SelectsResult(
            candidates=flat,
            by_beat={key: [item.id for item in values] for key, values in pools.items()},
            artifact_path=str(path),
        )

    def generate_variants(
        self,
        *,
        project: Project,
        brief: EditorialBrief,
        analysis: AnalysisResult | MediaUnderstandingIndex,
        variants: int = 3,
        reference: ReferenceAnalysisResult | ReferenceEditProfile | None = None,
    ) -> PlanSet:
        return self.plan(
            project=project,
            brief=brief,
            analysis=analysis,
            variants=variants,
            reference=reference,
        )

    def plan(
        self,
        *,
        project: Project,
        brief: EditorialBrief,
        analysis: AnalysisResult | MediaUnderstandingIndex,
        variants: int = 3,
        reference: ReferenceAnalysisResult | ReferenceEditProfile | None = None,
    ) -> PlanSet:
        if variants < 1 or variants > 100:
            raise ValueError("variants must be between 1 and 100")
        started = time.monotonic()
        index = analysis.index if isinstance(analysis, AnalysisResult) else analysis
        if index.project_id != project.id:
            raise ValueError("analysis targets a different project")
        reference_profile = (
            reference.profile if isinstance(reference, ReferenceAnalysisResult) else reference
        )
        policy = self._policy(brief, reference=reference_profile, index=index)
        if reference_profile is not None:
            policy = apply_reference_priors(policy, reference_profile)
        run_fingerprint = fingerprint(
            {"project": project.id, "brief": brief, "policy": policy, "seed": brief.seed}
        )
        run_id = f"run-{run_fingerprint[:20]}"
        pass_paths: list[str] = []
        pass_paths.append(
            self._pass(run_id, 1, "understanding", project, index, "built verified evidence index")
        )
        story = build_story_map(brief, index)
        pools = generate_selects(
            story,
            index,
            policy,
            top_k=brief.constraints.top_k_selects,
        )
        pools = apply_multicam_preferences(story, pools, index)
        pass_paths.append(self._pass(run_id, 2, "selects", story, pools, "preserved top-K selects"))
        assemblies = create_assemblies(
            story,
            pools,
            index.shots,
            brief,
            policy.model_copy(update={"beam_width": brief.constraints.beam_width}),
            variants=variants,
        )
        if not assemblies:
            raise EditorialBrainError(
                EditorialErrorCode.NO_VALID_CANDIDATE,
                "no assembly satisfies the mandatory beat and source constraints",
            )
        pass_paths.append(
            self._pass(run_id, 3, "assembly", pools, assemblies, "ran deterministic beam search")
        )
        refined_story = refine_story_map(story)
        if refined_story != story:
            story = refined_story
            pools = generate_selects(
                story,
                index,
                policy,
                top_k=brief.constraints.top_k_selects,
            )
            pools = apply_multicam_preferences(story, pools, index)
            assemblies = create_assemblies(
                story,
                pools,
                index.shots,
                brief,
                policy.model_copy(update={"beam_width": brief.constraints.beam_width}),
                variants=variants,
            )
            if not assemblies:
                raise EditorialBrainError(
                    EditorialErrorCode.NO_VALID_CANDIDATE,
                    "story refinement left no valid assembly",
                )
        pass_paths.append(
            self._pass(
                run_id,
                4,
                "story_refinement",
                story,
                refined_story,
                "validated order and retained non-redundant beats",
            )
        )
        points = generate_cut_points(index)
        fine = [refine_assembly(value, points, index) for value in assemblies]
        pass_paths.append(
            self._pass(run_id, 5, "fine_cut", assemblies, fine, "snapped to valid structural cuts")
        )
        av = [
            plan_audio_picture(
                value,
                index,
                narration_media_id=brief.narration_media_id,
                profile=brief.profile,
            )
            for value in fine
        ]
        pass_paths.append(
            self._pass(run_id, 6, "audio_picture", fine, av, "planned independent A/V edges")
        )
        picture = [assign_picture_roles(value, story, index, profile=brief.profile) for value in av]
        pass_paths.append(
            self._pass(
                run_id,
                7,
                "broll_cutaways",
                av,
                picture,
                "assigned only motivated supporting-picture roles",
            )
        )
        rhythmic = [_refresh_rhythm(value, policy) for value in picture]
        pass_paths.append(
            self._pass(run_id, 8, "rhythm", picture, rhythmic, "scored global pacing and holds")
        )
        presented = [assign_motivated_transitions(value, story, index) for value in rhythmic]
        pass_paths.append(
            self._pass(
                run_id,
                9,
                "presentation_intent",
                rhythmic,
                presented,
                "kept presentation restrained; no unmotivated effects",
            )
        )
        scored = [score_assembly_cuts(value, pools, points, index, policy) for value in presented]
        presented = [item[0] for item in scored]
        plans = [
            self._make_plan(
                project,
                brief,
                story,
                assembly,
                [item for item in presented if item.id != assembly.id],
                pools,
                index,
                policy,
                run_id,
                points,
                scored[position][1],
                reference_profile,
            )
            for position, assembly in enumerate(presented)
        ]
        plans = sorted(
            plans,
            key=lambda item: (-item.assembly.score.overall, item.assembly.id),
        )
        pass_paths.append(
            self._pass(run_id, 10, "compile", presented, plans, "validated compile-ready plans")
        )
        best = plans[0].assembly
        output = PlanSet(
            variants=[
                EditorialVariant(
                    id=f"variant:{plan.id}",
                    rank=rank,
                    plan=plan,
                    differentiators=(
                        [] if rank == 1 else variant_differentiators(best, plan.assembly)
                    ),
                )
                for rank, plan in enumerate(plans, 1)
            ]
        )
        self.artifacts.write_model("variants", _name(run_id), output)
        for variant in output.variants:
            self.artifacts.write_model("plans", _name(variant.plan.id), variant.plan)
        evaluated = sum(len(values) for values in pools.values())
        self._write_run_trace(
            RunTrace(
                run_id=run_id,
                stage="planning",
                elapsed_seconds=time.monotonic() - started,
                counters={
                    "candidates_evaluated": evaluated,
                    "assemblies_retained": len(output.variants),
                    "search_width": policy.beam_width,
                    "search_pruned": max(0, evaluated - policy.beam_width),
                    "cut_candidates": len(output.best.cut_candidates),
                    "review_flags": len(output.best.review_flags),
                },
                provider_usage=aggregate_usage(index.provider_evidence),
                chosen_candidate=output.best.assembly.id,
                rejected_alternatives=[item.plan.assembly.id for item in output.variants[1:]],
                details={
                    "final_score": output.best.assembly.score.overall,
                    "confidence": min(
                        (decision.confidence.score for decision in output.best.decisions),
                        default=0,
                    ),
                    "pass_artifacts": pass_paths,
                },
            )
        )
        return output

    def compile(
        self,
        *,
        project: Project,
        plan: EditorialPlan,
        mode: str = "patch",
    ) -> CompilationResult:
        started = time.monotonic()
        validate_plan_sources(project, plan)
        patch, decision_map = compile_patch(project, plan)
        validated = apply_and_validate(self.project_root, project, patch)
        compiled_decisions = [
            decision.model_copy(
                update={"engine_operation_indexes": decision_map.get(decision.id, [])},
                deep=True,
            )
            for decision in plan.decisions
        ]
        compiled_plan = plan.model_copy(
            update={
                "decisions": compiled_decisions,
                "trace": plan.trace.model_copy(update={"decisions": compiled_decisions}, deep=True),
            },
            deep=True,
        )
        if mode == "patch":
            result = CompilationResult(
                mode="patch",
                patch=patch,
                validated_project=validated,
                compiled_plan=compiled_plan,
                decision_operation_map=decision_map,
            )
        elif mode == "project":
            result = CompilationResult(
                mode="project",
                project=validated,
                validated_project=validated,
                compiled_plan=compiled_plan,
                decision_operation_map=decision_map,
            )
        else:
            raise ValueError("compile mode must be 'patch' or 'project'")
        self._write_run_trace(
            RunTrace(
                run_id=f"compile-{plan.id}",
                stage="compile",
                elapsed_seconds=time.monotonic() - started,
                counters={
                    "operations": len(patch.operations),
                    "mapped_decisions": sum(bool(value) for value in decision_map.values()),
                },
                chosen_candidate=plan.assembly.id,
                details={
                    "patch_id": patch.patch_id,
                    "validated_project_revision": validated.revision,
                },
            )
        )
        return result

    def explain(self, plan: EditorialPlan) -> ExplanationResult:
        return ExplanationResult(
            plan_id=plan.id,
            summary=(
                f"{len(plan.assembly.segments)} segments cover "
                f"{len(plan.assembly.covered_beat_ids)}/{len(plan.story.beats)} beats; "
                f"assembly score {plan.assembly.score.overall:.3f}."
            ),
            decisions=[decision.model_dump(mode="json") for decision in plan.decisions],
        )

    def benchmark(self) -> BenchmarkResult:
        from editorial_brain.benchmark.runner import run_benchmarks

        return run_benchmarks(self.project_root)

    def doctor(self) -> dict[str, object]:
        engine_report = VideoEngine(self.project_root).doctor()
        return {
            "editorial_brain_version": "1.0.0",
            "artifact_root": str(self.artifacts.root),
            "policies": self.policies.ids(),
            "transcription_provider": _provider_status(self.transcription_provider),
            "vision_provider": _provider_status(self.vision_provider),
            "semantic_provider": _provider_status(self.semantic_provider),
            "knowledge_provider": (
                self.directive_provider.status()
                if isinstance(self.directive_provider, RepositoryKnowledgeDirectiveProvider)
                else {"configured": self.directive_provider is not None}
            ),
            "video_engine": engine_report.model_dump(mode="json"),
        }

    def _analysis_identity(self, project: Project, brief: EditorialBrief) -> CacheIdentity:
        providers = [
            provider
            for provider in (
                self.transcription_provider,
                self.vision_provider,
                self.semantic_provider,
            )
            if provider is not None
        ]
        fingerprints = [provider.fingerprint for provider in providers]
        return CacheIdentity(
            namespace="media-understanding",
            source_hashes={media.id: media.sha256 or "" for media in project.media},
            analysis_version="media-understanding-v1",
            provider="pipeline",
            model="deterministic-plus-structured-semantics",
            provider_fingerprint=fingerprint(fingerprints),
            prompt_fingerprint=fingerprint(
                {"objective": brief.objective, "schema": "shot-speech-semantics-v1"}
            ),
            parameters={"project_settings": project.settings.model_dump(mode="json")},
        )

    def _policy(
        self,
        brief: EditorialBrief,
        *,
        reference: ReferenceEditProfile | None = None,
        index: MediaUnderstandingIndex | None = None,
    ) -> EditorialPolicy:
        policy = self.policies.get(brief.profile.value)
        if self.directive_provider is not None:
            if isinstance(self.directive_provider, RepositoryKnowledgeDirectiveProvider):
                directives = self.directive_provider.directives_for(
                    brief, reference=reference, index=index
                )
            else:
                directives = self.directive_provider.directives(brief)
            policy = apply_directives(policy, directives)
            if isinstance(self.directive_provider, RepositoryKnowledgeDirectiveProvider):
                profile = self.directive_provider.last_profile
                if profile is not None:
                    policy = policy.model_copy(
                        update={
                            "knowledge_fingerprint": profile.base_fingerprint,
                            "taste_profile_id": profile.id,
                            "taste_fingerprint": profile.fingerprint,
                            "active_principle_ids": [
                                item.principle_id for item in profile.selected
                            ],
                            "taste_axes": profile.axes,
                            "reference_profile_id": profile.reference_profile_id,
                        },
                        deep=True,
                    )
        return policy

    def _pass(
        self,
        run_id: str,
        number: int,
        name: object,
        before: object,
        after: object,
        summary: str,
    ) -> str:
        from typing import cast

        from editorial_brain.planning.passes import PassName

        artifact = make_pass_artifact(
            run_id,
            number,
            cast(PassName, name),
            before,
            after,
            summary,
        )
        path = self.artifacts.write_model(
            "traces", f"{_name(run_id)}-pass-{number:02d}-{name}", artifact
        )
        return str(path)

    def _write_run_trace(self, trace: RunTrace) -> str:
        return str(self.artifacts.write_model("traces", _name(trace.run_id), trace))

    def _make_plan(
        self,
        project: Project,
        brief: EditorialBrief,
        story: object,
        assembly: object,
        alternatives: list[object],
        pools: dict[str, list[SelectCandidate]],
        index: MediaUnderstandingIndex,
        policy: EditorialPolicy,
        run_id: str,
        cut_points: list[CutPointCandidate],
        cut_candidates: list[CutCandidate],
        reference_profile: ReferenceEditProfile | None,
    ) -> EditorialPlan:
        from editorial_brain.core.models import CandidateAssembly, StoryMap

        assert isinstance(story, StoryMap)
        assert isinstance(assembly, CandidateAssembly)
        assert all(isinstance(item, CandidateAssembly) for item in alternatives)
        decisions, flags = _decisions(
            assembly, pools, index, policy, cut_points, cut_candidates, brief, story
        )
        trace = DecisionTrace(
            run_id=run_id,
            decisions=decisions,
            stage_metrics={
                "candidates_evaluated": sum(len(values) for values in pools.values()),
                "search_width": policy.beam_width,
                "chosen_assembly": assembly.id,
                "final_score": assembly.score.overall,
                "review_flags": len(flags),
            },
        )
        plan_fingerprint = fingerprint({"assembly": assembly, "brief": brief, "policy": policy.id})
        plan_id = f"plan-{plan_fingerprint[:20]}"
        deterministic = fingerprint(
            {
                "project_id": project.id,
                "revision": project.revision,
                "media_hashes": index.media_hashes,
                "brief": brief,
                "assembly": assembly,
                "policy": policy,
                "seed": brief.seed,
            }
        )
        plan = EditorialPlan(
            id=plan_id,
            project_id=project.id,
            project_revision=project.revision,
            brief_id=brief.id,
            narration_media_id=brief.narration_media_id,
            narration_source_range=_narration_range(brief, index),
            story=story,
            assembly=assembly,
            cut_points=cut_points,
            cut_candidates=cut_candidates,
            alternatives=[item for item in alternatives if isinstance(item, CandidateAssembly)],
            decisions=decisions,
            review_flags=flags,
            trace=trace,
            policy_id=policy.id,
            reference_profile_id=reference_profile.id if reference_profile else None,
            seed=brief.seed,
            deterministic_fingerprint=deterministic,
            extensions={
                "editorial_brain:taste_profile_id": policy.taste_profile_id,
                "editorial_brain:taste_fingerprint": policy.taste_fingerprint,
                "editorial_brain:knowledge_base_fingerprint": policy.knowledge_fingerprint,
                "editorial_brain:active_principle_ids": policy.active_principle_ids,
                "editorial_brain:taste_axes": policy.taste_axes,
                "editorial_brain:knowledge_reasons": policy.knowledge_reasons,
                "editorial_brain:transition_preferences": policy.transition_preferences,
            },
        )
        report = validate_plan_against_index(plan, index)
        if not report.valid:
            raise EditorialBrainError(
                EditorialErrorCode.PLAN_INVALID,
                "editorial plan failed cross-model validation",
                context={"issues": [item.model_dump(mode="json") for item in report.issues]},
            )
        return plan


class _SelectsArtifact(BrainModel):
    candidates: list[SelectCandidate]
    pools: dict[str, list[SelectCandidate]] = Field(default_factory=dict)


def _decisions(
    assembly: object,
    pools: dict[str, list[SelectCandidate]],
    index: MediaUnderstandingIndex,
    policy: EditorialPolicy,
    cut_points: list[CutPointCandidate],
    cut_candidates: list[CutCandidate],
    brief: EditorialBrief,
    story: object,
) -> tuple[list[EditorialDecision], list[ReviewFlag]]:
    from editorial_brain.core.models import CandidateAssembly, StoryMap

    assert isinstance(assembly, CandidateAssembly)
    assert isinstance(story, StoryMap)
    decisions: list[EditorialDecision] = []
    flags: list[ReviewFlag] = []
    review_threshold = (
        policy.review_threshold
        + {
            ReviewMode.STRICT: 0.15,
            ReviewMode.BALANCED: 0.0,
            ReviewMode.AUTONOMOUS: -0.2,
        }[brief.constraints.review_mode]
    )
    review_threshold = max(0, min(1, review_threshold))
    beats = {beat.id: beat for beat in story.beats}
    if len({shot.media_id for shot in index.shots}) > 1 and not index.synchronizations:
        flags.append(
            ReviewFlag(
                id=f"flag:{assembly.id}:ambiguous-sync",
                code="ambiguous_sync",
                message="multiple camera sources exist without measured synchronization evidence",
                confidence=Confidence(
                    score=1,
                    basis=EvidenceKind.DERIVED,
                    calibration="missing_cross_source_sync_v1",
                ),
                blocking=brief.constraints.review_mode is ReviewMode.STRICT,
            )
        )
    for position, segment in enumerate(assembly.segments):
        candidates = pools[segment.beat_id]
        selected = next(item for item in candidates if item.id == segment.select_id)
        alternatives = [item for item in candidates if item.id != selected.id]
        story_beat = beats[segment.beat_id]
        decision_id = f"decision:{assembly.id}:{position:04d}"
        decisions.append(
            EditorialDecision(
                id=decision_id,
                kind="select",
                selected_id=selected.id,
                alternative_ids=[item.id for item in alternatives],
                alternative_scores={item.id: item.score.overall for item in alternatives},
                reasons=selected.reasons,
                constraints=["verified_source_range", "structural_cut_boundaries"],
                evidence=selected.evidence,
                confidence=selected.confidence,
                policy_ids=[policy.id, *policy.directive_ids],
                provider_evidence=index.provider_evidence,
            )
        )
        if selected.confidence.score < review_threshold:
            flags.append(
                ReviewFlag(
                    id=f"flag:{decision_id}:weak-match",
                    code="weak_semantic_match",
                    message="selected source is the best available but semantic confidence is weak",
                    decision_id=decision_id,
                    confidence=selected.confidence,
                    blocking=False,
                )
            )
        if alternatives and abs(selected.score.overall - alternatives[0].score.overall) <= 0.03:
            flags.append(
                ReviewFlag(
                    id=f"flag:{decision_id}:near-equal",
                    code="near_equal_candidates",
                    message="two source candidates have near-equal aggregate scores",
                    decision_id=decision_id,
                    confidence=Confidence(
                        score=0.5,
                        basis=EvidenceKind.DERIVED,
                        calibration="score_margin_le_0.03",
                    ),
                )
            )
        if selected.score.shot_quality < 0.35:
            flags.append(
                ReviewFlag(
                    id=f"flag:{decision_id}:poor-quality",
                    code="poor_source_quality",
                    message="the strongest matching source has weak measured picture quality",
                    decision_id=decision_id,
                    confidence=selected.confidence,
                )
            )
        if story_beat.visual_requirements and selected.score.semantic_relevance < 0.2:
            flags.append(
                ReviewFlag(
                    id=f"flag:{decision_id}:insufficient-broll",
                    code="insufficient_broll",
                    message=(
                        "no available supporting picture strongly matches the visual requirement"
                    ),
                    decision_id=decision_id,
                    confidence=selected.confidence,
                )
            )
        if position > 0 and (selected.handle_before.value <= 0 or selected.handle_after.value <= 0):
            flags.append(
                ReviewFlag(
                    id=f"flag:{decision_id}:handles",
                    code="insufficient_handles",
                    message="selected source has insufficient safe handles for boundary refinement",
                    decision_id=decision_id,
                    confidence=selected.confidence,
                )
            )
        if selected.score.reaction_value >= 0.6 and selected.confidence.score < 0.7:
            flags.append(
                ReviewFlag(
                    id=f"flag:{decision_id}:reaction",
                    code="uncertain_speaker_reaction",
                    message=(
                        "reaction value is useful but speaker/reaction attribution is uncertain"
                    ),
                    decision_id=decision_id,
                    confidence=selected.confidence,
                )
            )
        timing_issues = reveal_timing_violations(story_beat, segment)
        short_holds = [
            requirement.id
            for requirement in story_beat.visual_requirements
            if requirement.required and segment.timeline_range.duration < requirement.minimum_hold
        ]
        if timing_issues or short_holds:
            detail = timing_issues + [f"short_visual_hold:{item}" for item in short_holds]
            flags.append(
                ReviewFlag(
                    id=f"flag:{decision_id}:visual-proof",
                    code="missing_visual_proof",
                    message="required visual proof timing is uncertain: " + ", ".join(detail),
                    decision_id=decision_id,
                    confidence=Confidence(
                        score=max(0, selected.confidence.score - 0.2),
                        basis=EvidenceKind.DERIVED,
                        calibration="visual_requirement_timing_v1",
                    ),
                    blocking=brief.constraints.review_mode is ReviewMode.STRICT,
                )
            )
    point_by_id = {point.id: point for point in cut_points}
    cuts_by_id = {cut.id: cut for cut in cut_candidates}
    for position, cut_id in enumerate(assembly.cut_ids):
        selected_cut = cuts_by_id[cut_id]
        cut_alternatives = [
            cut
            for cut in cut_candidates
            if cut.id != cut_id
            and cut.from_select_id == selected_cut.from_select_id
            and cut.to_select_id == selected_cut.to_select_id
        ]
        top_dimensions = sorted(
            (
                (key, value)
                for key, value in selected_cut.score.model_dump().items()
                if isinstance(value, (int, float)) and key not in {"overall"}
            ),
            key=lambda item: (-item[1], item[0]),
        )[:4]
        decisions.append(
            EditorialDecision(
                id=f"decision:{assembly.id}:cut:{position:04d}",
                kind="cut",
                selected_id=cut_id,
                alternative_ids=[item.id for item in cut_alternatives],
                alternative_scores={item.id: item.score.overall for item in cut_alternatives},
                reasons=[f"{name}={value:.3f}" for name, value in top_dimensions],
                constraints=["not_inside_word", "verified_source_range", "reaction_protection"],
                evidence=selected_cut.evidence,
                confidence=selected_cut.confidence,
                policy_ids=[policy.id, *policy.directive_ids],
                provider_evidence=index.provider_evidence,
            )
        )
        if selected_cut.confidence.score < policy.review_threshold:
            flags.append(
                ReviewFlag(
                    id=f"flag:{assembly.id}:cut:{position:04d}",
                    code="uncertain_continuity",
                    message="chosen structural cut has weak supporting confidence",
                    decision_id=f"decision:{assembly.id}:cut:{position:04d}",
                    confidence=selected_cut.confidence,
                )
            )
        assert selected_cut.out_point_id is not None
        assert selected_cut.out_point_id in point_by_id
    target = brief.constraints.target_duration
    if target is not None:
        actual = assembly.segments[-1].timeline_range.end
        tolerance = max(0.25, float(target.fraction) * 0.1)
        if abs(float(actual.fraction - target.fraction)) > tolerance:
            flags.append(
                ReviewFlag(
                    id=f"flag:{assembly.id}:duration",
                    code="duration_meaning_conflict",
                    message=(
                        "the strongest meaning-preserving assembly cannot meet the requested "
                        "duration within ten percent"
                    ),
                    confidence=Confidence(
                        score=0.9,
                        basis=EvidenceKind.DERIVED,
                        calibration="duration_delta_v1",
                    ),
                    blocking=brief.constraints.review_mode is ReviewMode.STRICT,
                )
            )
    return decisions, flags


def _refresh_rhythm(assembly: object, policy: EditorialPolicy) -> CandidateAssembly:
    assert isinstance(assembly, CandidateAssembly)
    rhythm = score_rhythm(
        assembly.segments,
        samples_from_segments(assembly.segments),
        policy.pacing,
    )
    score = assembly.score.model_copy(
        update={
            "pacing": rhythm.overall,
            "overall": assembly.score.overall + (rhythm.overall - assembly.score.pacing) * 0.13,
        }
    )
    return assembly.model_copy(update={"rhythm": rhythm, "score": score}, deep=True)


def _provider_status(provider: object | None) -> dict[str, object]:
    if provider is None:
        return {"configured": False}
    status: dict[str, object] = {
        "configured": True,
        "provider": getattr(provider, "provider_name", "unknown"),
        "model": getattr(provider, "model_name", "unknown"),
        "fingerprint": getattr(provider, "fingerprint", "unknown"),
    }
    api_key_env = getattr(provider, "api_key_env", None)
    if isinstance(api_key_env, str):
        status["credential_environment"] = api_key_env
        status["credential_configured"] = bool(getattr(provider, "credential_configured", False))
        source = getattr(provider, "credential_source", None)
        if source is not None:
            status["credential_source"] = source
    agent_available = getattr(provider, "agent_available", None)
    if isinstance(agent_available, bool):
        status["runtime_available"] = agent_available
        status["executable"] = getattr(provider, "executable_path", None)
        status["selection_reason"] = "OPENAI_API_KEY absent; using authenticated agent runtime"
    return status


def _narration_range(brief: EditorialBrief, index: MediaUnderstandingIndex) -> TimeRange | None:
    if brief.narration_media_id is None:
        return None
    transcript = next(
        (
            item
            for item in index.transcripts
            if (
                item.id == brief.narration_transcript_id
                if brief.narration_transcript_id
                else item.media_id == brief.narration_media_id
            )
        ),
        None,
    )
    if transcript is None or not transcript.words:
        return None
    return TimeRange.from_start_end(
        transcript.words[0].source_range.start,
        transcript.words[-1].source_range.end,
    )


def _name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")[:120] or "artifact"
