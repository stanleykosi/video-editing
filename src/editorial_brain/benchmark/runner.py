"""Deterministic end-to-end editorial benchmark runner."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

from editorial_brain.api.brain import EditorialBrain
from editorial_brain.api.results import (
    BenchmarkMetric,
    BenchmarkResult,
    BenchmarkScenarioResult,
)
from editorial_brain.benchmark.fixtures import synthetic_fixture, synthetic_reference_profile
from editorial_brain.benchmark.metrics import (
    audio_picture_alignment,
    continuity_violations,
    cuts_inside_words,
    duplicate_source_usage,
    duration_error,
    expected_candidate_rank,
    expected_cut_window_accuracy,
    invalid_source_ranges,
    missing_required_beats,
    must_exclude_violations,
    must_include_coverage,
    patch_validation,
    reaction_preservation,
    repetition_score,
    visual_requirement_match,
)
from editorial_brain.benchmark.report import markdown_report
from editorial_brain.benchmark.scenarios import SCENARIOS, GoldenScenario
from editorial_brain.core.hashing import fingerprint
from editorial_brain.core.models import EditorialPlan, MediaUnderstandingIndex, ReferenceEditProfile
from editorial_brain.knowledge.provider import RepositoryKnowledgeDirectiveProvider
from editorial_brain.storage.artifacts import ArtifactStore
from video_engine.api import RenderRequest, VideoEngine


def run_benchmarks(project_root: Path) -> BenchmarkResult:
    """Exercise every golden scenario through planning and engine compilation."""
    results = [_run_scenario(project_root, scenario) for scenario in SCENARIOS]
    digest = fingerprint([item.model_dump(mode="json") for item in results])
    interim = BenchmarkResult(
        scenarios=results,
        passed=all(item.passed for item in results),
        deterministic_fingerprint=digest,
    )
    store = ArtifactStore(project_root)
    report_path = store.write_text("benchmarks", "latest", markdown_report(interim))
    result = interim.model_copy(update={"report_path": str(report_path)})
    store.write_model("benchmarks", "latest", result)
    return result


def _run_scenario(project_root: Path, scenario: GoldenScenario) -> BenchmarkScenarioResult:
    started = time.monotonic()
    root = project_root / ".editorial-brain" / "benchmarks" / "fixtures" / scenario.id
    project, brief, index, expected_shots = synthetic_fixture(root, scenario)
    knowledge_provider = (
        RepositoryKnowledgeDirectiveProvider(root, knowledge_root=project_root / "knowledge")
        if (project_root / "knowledge").is_dir()
        else None
    )
    brain = EditorialBrain(root, directive_provider=knowledge_provider)
    reference = synthetic_reference_profile(scenario)
    plans = brain.plan(
        project=project, brief=brief, analysis=index, variants=3, reference=reference
    )
    repeated = brain.plan(
        project=project, brief=brief, analysis=index, variants=3, reference=reference
    )
    plan = plans.best
    compilation = brain.compile(project=project, plan=plan)
    patch = compilation.patch
    assert patch is not None
    graph_compiles = False
    try:
        VideoEngine(root).renderer(compilation.validated_project).compile(
            RenderRequest(output_path=root / "benchmark-preview.mp4")
        )
        graph_compiles = True
    except Exception:
        graph_compiles = False

    selected_shots = {
        decision.selected_id.rsplit(":", 1)[-1]
        for decision in plan.decisions
        if decision.kind == "select" and decision.selected_id is not None
    }
    select_result = brain.generate_selects(
        project=project,
        brief=brief,
        analysis=index,
    )
    expected_recall = (
        len(selected_shots & expected_shots) / len(expected_shots) if expected_shots else 1
    )
    candidate_rank = min(
        (expected_candidate_rank(select_result.candidates, shot_id) for shot_id in expected_shots),
        default=1,
    )
    selected_cuts = [cut for cut in plan.cut_candidates if cut.id in plan.assembly.cut_ids]
    points = {point.id: point for point in plan.cut_points}
    chosen_cut_times = [
        points[cut.out_point_id].time for cut in selected_cuts if cut.out_point_id is not None
    ]
    cut_accuracy = (
        min(
            expected_cut_window_accuracy(float(item.fraction), 3.5, 1.0)
            for item in chosen_cut_times
        )
        if chosen_cut_times
        else 1.0
    )
    jl_expected = scenario.id in {"interview", "podcast_clip", "multicam_conversation"}
    jl_present = any(
        segment.audio_relationship.value
        in {"j_cut", "l_cut", "reaction_continuing_dialogue", "audio_bridge"}
        for segment in plan.assembly.segments
    )
    target = brief.constraints.target_duration
    knowledge_metrics = _knowledge_metrics(scenario, plan, knowledge_provider)
    metrics = [
        _metric(
            "invalid_source_ranges",
            invalid_source_ranges(plan, project),
            0,
            "technical",
            maximum=True,
        ),
        _metric("cuts_inside_words", cuts_inside_words(plan, index), 0, "technical", maximum=True),
        _metric(
            "missing_required_beats", missing_required_beats(plan), 0, "technical", maximum=True
        ),
        _metric(
            "duration_error",
            duration_error(plan, float(target.fraction) if target else None),
            0.75,
            "technical",
            maximum=True,
        ),
        _metric(
            "duplicate_source_usage", duplicate_source_usage(plan), 0, "editorial", maximum=True
        ),
        _metric("repetition_score", repetition_score(plan), 0, "editorial", maximum=True),
        _metric(
            "continuity_violations",
            continuity_violations(plan, index),
            0,
            "editorial",
            maximum=True,
        ),
        _metric("visual_requirement_match", visual_requirement_match(plan), 1, "editorial"),
        _metric("reaction_preservation", reaction_preservation(plan, index), 1, "editorial"),
        _metric("audio_picture_alignment", audio_picture_alignment(plan), 1, "editorial"),
        _metric(
            "must_include_coverage",
            must_include_coverage(plan, brief.constraints.must_include_media_ids),
            1,
            "technical",
        ),
        _metric(
            "must_exclude_violations",
            must_exclude_violations(
                plan,
                brief.constraints.must_exclude_media_ids,
                brief.constraints.must_exclude_ranges,
            ),
            0,
            "technical",
            maximum=True,
        ),
        _bool_metric("patch_validation", patch_validation(patch, project), "technical"),
        _bool_metric("engine_compile_success", graph_compiles, "technical"),
        _bool_metric(
            "deterministic_repeatability",
            plan.deterministic_fingerprint == repeated.best.deterministic_fingerprint
            and plan.model_dump(mode="json") == repeated.best.model_dump(mode="json"),
            "technical",
        ),
        _metric("expected_select_top_k_recall", expected_recall, 1, "editorial"),
        _metric("expected_cut_window_accuracy", cut_accuracy, 0.5, "editorial"),
        _metric("expected_candidate_rank", candidate_rank, 0.25, "editorial"),
        _bool_metric("expected_j_l_cut_decision", not jl_expected or jl_present, "editorial"),
        _metric(
            "expected_reaction_hold",
            reaction_preservation(plan, index),
            1,
            "editorial",
        ),
        *[
            _bool_metric(f"behavior:{name}", passed, "editorial")
            for name, passed in _behavior_checks(scenario, plan, index, reference).items()
        ],
        *knowledge_metrics,
        BenchmarkMetric(
            name="human_editorial_quality",
            value=0,
            passed=None,
            category="subjective",
        ),
    ]
    return BenchmarkScenarioResult(
        scenario_id=scenario.id,
        metrics=metrics,
        passed=all(item.passed is not False for item in metrics),
        elapsed_seconds=time.monotonic() - started,
    )


def _knowledge_metrics(
    scenario: GoldenScenario,
    plan: EditorialPlan,
    provider: RepositoryKnowledgeDirectiveProvider | None,
) -> list[BenchmarkMetric]:
    if (
        provider is None
        or provider.last_catalog is None
        or provider.last_base is None
        or provider.last_profile is None
    ):
        return []
    base = provider.last_base
    profile = provider.last_profile
    principles = {item.id: item for item in base.principles}
    selected = [principles[item.principle_id] for item in profile.selected]
    expected_categories = {
        "interview": {"dialogue_reaction", "audio_picture", "story_beat"},
        "podcast_clip": {"dialogue_reaction", "audio_picture", "story_beat"},
        "narration_animal": {"selects", "story_beat", "presentation"},
        "recap": {"selects", "story_beat", "safety_qc"},
        "product_advertisement": {"selects", "story_beat", "presentation"},
        "music_montage": {"sound_music", "rhythm_pacing", "cut_points"},
        "multicam_conversation": {"dialogue_reaction", "audio_picture"},
        "long_form_documentary": {"story_beat", "rhythm_pacing", "dialogue_reaction"},
        "intentional_long_hold": {"dialogue_reaction", "rhythm_pacing"},
        "reference_led": {"rhythm_pacing", "story_beat", "presentation"},
    }[scenario.id]
    route_match = bool({item.category for item in selected} & expected_categories)
    serialized = plan.model_dump_json().lower()
    taste_identity = (
        str(plan.extensions.get("editorial_brain:taste_profile_id", "")).startswith("taste:")
        and len(str(plan.extensions.get("editorial_brain:taste_fingerprint", ""))) == 64
        and plan.extensions.get("editorial_brain:knowledge_base_fingerprint") == base.fingerprint
    )
    return [
        _metric(
            "knowledge_catalog_items",
            float(len(provider.last_catalog.items)),
            380,
            "technical",
        ),
        _metric(
            "knowledge_consolidation_reduction",
            base.statistics.principle_reduction_ratio,
            0.7,
            "technical",
        ),
        _metric(
            "knowledge_total_construct_reduction",
            base.statistics.total_construct_reduction_ratio,
            0.45,
            "technical",
        ),
        _bool_metric("taste_profile_relevance", route_match, "editorial"),
        _bool_metric(
            "source_neutral_taste_identity",
            taste_identity
            and "relative_path" not in serialized
            and "source_ids" not in serialized
            and "youtube" not in serialized,
            "technical",
        ),
    ]


def _behavior_checks(
    scenario: GoldenScenario,
    plan: EditorialPlan,
    index: MediaUnderstandingIndex,
    reference: ReferenceEditProfile | None,
) -> dict[str, bool]:
    shots = {
        segment.select_id: next(
            (shot for shot in index.shots if shot.id in segment.select_id), None
        )
        for segment in plan.assembly.segments
    }
    relations = {segment.audio_relationship.value for segment in plan.assembly.segments}
    roles = {segment.role for segment in plan.assembly.segments}
    no_repetition = repetition_score(plan) == 0
    ordered = all(
        left.timeline_range.end <= right.timeline_range.start
        for left, right in zip(plan.assembly.segments, plan.assembly.segments[1:], strict=False)
    )
    checks = {
        "dead_space_tightened": not any(
            not pause.protected
            and any(
                segment.media_id == pause.media_id
                and segment.source_range.overlaps(pause.source_range)
                for segment in plan.assembly.segments
            )
            for pause in index.pauses
        ),
        "reaction_preserved": reaction_preservation(plan, index) == 1,
        "no_cut_inside_word": cuts_inside_words(plan, index) == 0,
        "natural_cadence": audio_picture_alignment(plan) == 1,
        "coherent_context": missing_required_beats(plan) == 0,
        "dialogue_cover": "reaction" in roles or "cutaway" in roles,
        "motivated_j_l_cut": bool(relations & {"j_cut", "l_cut", "reaction_continuing_dialogue"}),
        "named_subject_match": visual_requirement_match(plan) == 1,
        "minimum_reveal_hold": all(
            segment.timeline_range.duration >= requirement.minimum_hold
            for segment in plan.assembly.segments
            for beat in plan.story.beats
            if beat.id == segment.beat_id
            for requirement in beat.visual_requirements
        ),
        "no_repetition": no_repetition,
        "event_scene_match": visual_requirement_match(plan) == 1,
        "story_order": ordered,
        "selective_fragments": any(
            shot is not None and segment.source_range.duration < shot.source_range.duration
            for segment in plan.assembly.segments
            for shot in [shots[segment.select_id]]
        ),
        "benefit_proof": "proof" in roles,
        "detail_closeup": any(
            shot is not None and shot.camera.shot_scale in {"detail", "close"}
            for shot in shots.values()
        ),
        "product_visibility": any(
            decision.kind == "select" and decision.confidence.score >= 0.5
            for decision in plan.decisions
        ),
        "musical_structure": "music_led" in relations,
        "non_mechanical_beats": len(plan.assembly.cut_ids) < len(index.music_events),
        "visual_progression": len({segment.select_id for segment in plan.assembly.segments})
        == len(plan.assembly.segments),
        "measured_sync": bool(index.synchronizations),
        "speaker_reaction_choice": "reaction" in roles,
        "non_mechanical_switching": no_repetition,
        "beat_structure": missing_required_beats(plan) == 0,
        "long_range_continuity": continuity_violations(plan, index) == 0,
        "slower_sections": any(
            float(segment.timeline_range.duration.fraction) >= 3
            for segment in plan.assembly.segments
        ),
        "do_not_cut": not plan.assembly.cut_ids,
        "protected_hold": any(segment.protected for segment in plan.assembly.segments),
        "no_fast_bias": any(
            float(segment.timeline_range.duration.fraction) >= 4
            for segment in plan.assembly.segments
        ),
        "measured_reference_grammar": reference is not None,
        "pacing_prior": plan.reference_profile_id is not None,
        "no_sequence_copy": bool(
            reference
            and all(
                segment.media_sha256 != reference.source_sha256
                for segment in plan.assembly.segments
            )
        ),
    }
    return {name: checks.get(name, False) for name in scenario.expected_behaviors}


def _metric(
    name: str,
    value: float,
    threshold: float,
    category: Literal["technical", "editorial", "subjective"],
    *,
    maximum: bool = False,
) -> BenchmarkMetric:
    passed = value <= threshold if maximum else value >= threshold
    return BenchmarkMetric(
        name=name,
        value=value,
        passed=passed,
        category=category,
    )


def _bool_metric(
    name: str,
    value: bool,
    category: Literal["technical", "editorial", "subjective"],
) -> BenchmarkMetric:
    return _metric(name, float(value), 1, category)
