"""Per-video taste synthesis from canonical principles and reference grammar."""

from __future__ import annotations

import math
from collections import defaultdict

from editorial_brain.core.hashing import fingerprint
from editorial_brain.core.models import (
    EditorialBrief,
    EditorialProfile,
    MediaUnderstandingIndex,
    ReferenceEditProfile,
    WorkflowModifier,
)
from editorial_brain.knowledge.models import (
    TASTE_AXES,
    CanonicalPrinciple,
    ConsolidatedKnowledgeBase,
    PrinciplePolarity,
    PrincipleTier,
    TasteProfile,
    TasteSelection,
)
from editorial_brain.knowledge.normalize import semantic_tokens
from editorial_brain.policies.models import EditorialDirective

TIER_WEIGHT = {
    PrincipleTier.INVARIANT: 5.0,
    PrincipleTier.MEANING: 4.0,
    PrincipleTier.CONTINUITY: 3.0,
    PrincipleTier.RHYTHM: 2.5,
    PrincipleTier.STYLE: 2.0,
    PrincipleTier.DECORATION: 1.0,
}


def synthesize_taste_profile(
    base: ConsolidatedKnowledgeBase,
    brief: EditorialBrief,
    *,
    reference: ReferenceEditProfile | None = None,
    index: MediaUnderstandingIndex | None = None,
) -> TasteProfile:
    terms = _brief_terms(brief)
    capabilities = _capabilities(index) if index is not None else None
    explicit = set(brief.knowledge_include)
    excluded = set(brief.knowledge_exclude)
    ranked: list[tuple[float, CanonicalPrinciple, list[str]]] = []
    rejected: dict[str, str] = {}
    for principle in base.principles:
        if principle.id in excluded or principle.category in excluded:
            rejected[principle.id] = "explicitly_excluded"
            continue
        if capabilities is not None:
            missing = sorted(set(principle.prerequisite_capabilities) - capabilities)
            if missing:
                rejected[principle.id] = "missing_capability:" + ",".join(missing)
                continue
        context = set(principle.context_terms)
        exclusions = set(principle.exclusion_terms)
        overlap = len(terms & context)
        text_overlap = len(terms & set(semantic_tokens(principle.statement)))
        exclusion_overlap = len(terms & exclusions)
        required = principle.tier is PrincipleTier.INVARIANT
        explicitly_included = (
            principle.id in explicit
            or principle.category in explicit
            or bool(explicit & set(semantic_tokens(principle.statement)))
        )
        if brief.knowledge_mode == "explicit" and not explicitly_included and not required:
            rejected[principle.id] = "not_explicitly_selected"
            continue
        category_bonus = _category_bonus(principle.category, brief)
        score = (
            TIER_WEIGHT[principle.tier]
            + principle.confidence
            + overlap * 1.2
            + text_overlap * 0.35
            + category_bonus
            + (100 if explicitly_included else 0)
            + (20 if required else 0)
            - exclusion_overlap * 2.0
        )
        if score < 3.25 and not required and not explicitly_included:
            rejected[principle.id] = "insufficient_context_match"
            continue
        reasons = [f"{principle.tier.value} editorial principle"]
        if overlap:
            reasons.append("applicability matches: " + ", ".join(sorted(terms & context)[:8]))
        if text_overlap:
            reasons.append("brief matches principle semantics")
        if category_bonus:
            reasons.append(f"{principle.category} matches the workflow")
        ranked.append((score, principle, reasons))
    ranked.sort(key=lambda item: (-item[0], item[1].id))
    selected_values = ranked[: brief.knowledge_max_items]
    selected = [
        TasteSelection(principle_id=principle.id, score=score, reasons=reasons)
        for score, principle, reasons in selected_values
    ]
    enabled_recipe_ids = _route_recipes(base, terms, capabilities, brief)
    active_gate_ids = _route_gates(base, terms)
    axes = _principle_axes(selected_values)
    reference_influence = 0.0
    reasons = [
        f"selected {len(selected)} source-neutral principles from {len(base.principles)}",
        "duplicate tutorial occurrences do not increase principle weight",
    ]
    if reference is not None:
        reference_influence = brief.reference_influence
        axes = _blend_axes(axes, _reference_axes(reference), reference_influence)
        reasons.append("bounded measurable reference grammar shaped this video's temporary style")
    resolutions = _resolve_conflicts(base, selected_values, axes)
    payload = {
        "brief": brief,
        "base": base.fingerprint,
        "selected": selected,
        "axes": axes,
        "resolutions": resolutions,
        "recipes": enabled_recipe_ids,
        "gates": active_gate_ids,
        "reference_id": reference.id if reference else None,
        "reference_influence": reference_influence,
    }
    profile_fingerprint = fingerprint(payload)
    confidence = (
        sum(principle.confidence for _, principle, _ in selected_values) / len(selected_values)
        if selected_values
        else 0
    )
    return TasteProfile(
        id=f"taste:{profile_fingerprint[:20]}",
        brief_id=brief.id,
        base_fingerprint=base.fingerprint,
        reference_profile_id=reference.id if reference else None,
        fingerprint=profile_fingerprint,
        axes=axes,
        selected=selected,
        enabled_recipe_ids=enabled_recipe_ids,
        active_gate_ids=active_gate_ids,
        rejected=rejected,
        conflict_resolutions=resolutions,
        reference_influence=reference_influence,
        confidence=confidence,
        reasons=reasons,
    )


def compile_taste_directives(
    base: ConsolidatedKnowledgeBase, profile: TasteProfile
) -> list[EditorialDirective]:
    by_id = {principle.id: principle for principle in base.principles}
    directives: list[EditorialDirective] = []
    for selected in profile.selected:
        principle = by_id[selected.principle_id]
        effect = principle.effect
        directives.append(
            EditorialDirective(
                id=principle.id,
                scoring_adjustments=effect.cut_adjustments,
                select_adjustments=effect.select_adjustments,
                hard_constraints=(
                    [principle.statement]
                    if principle.tier is PrincipleTier.INVARIANT
                    and principle.polarity is PrinciplePolarity.REQUIRE
                    else []
                ),
                soft_constraints=(
                    [] if principle.tier is PrincipleTier.INVARIANT else [principle.statement]
                ),
                technique_preferences=[principle.statement],
                transition_rules=effect.transition_preferences,
                preferred_duration_multiplier=effect.preferred_duration_multiplier,
                minimum_duration_multiplier=effect.minimum_duration_multiplier,
                maximum_duration_multiplier=effect.maximum_duration_multiplier,
                breathing_room_adjustment=effect.breathing_room_adjustment,
                music_alignment_adjustment=effect.music_alignment_adjustment,
                reasons=selected.reasons,
                confidence=principle.confidence,
            )
        )
    axes = profile.axes
    duration = _clamp(1 - axes["cut_energy"] * 0.12 + axes["breathing_room"] * 0.1, 0.7, 1.35)
    axis_cut = {
        "semantic_completeness": max(0, axes["clarity"]) * 0.08,
        "information_density": axes["information_density"] * 0.05,
        "reaction_preservation": axes["reaction_patience"] * 0.08,
        "visual_relevance": axes["visual_proof"] * 0.07,
        "visual_continuity": axes["continuity_strictness"] * 0.05,
        "rhythm": axes["musicality"] * 0.06,
        "visual_novelty": axes["novelty"] * 0.05,
        "motion_compatibility": axes["camera_motion"] * 0.035,
    }
    axis_select = {
        "semantic_relevance": max(0, axes["clarity"]) * 0.03,
        "evidence_value": axes["visual_proof"] * 0.04,
        "reaction_value": axes["reaction_patience"] * 0.035,
        "novelty": axes["novelty"] * 0.03,
    }
    directives.append(
        EditorialDirective(
            id=profile.id,
            scoring_adjustments=axis_cut,
            select_adjustments=axis_select,
            preferred_duration_multiplier=duration,
            minimum_duration_multiplier=_clamp(duration * 0.96, 0.65, 1.3),
            maximum_duration_multiplier=_clamp(duration * 1.04, 0.7, 1.5),
            breathing_room_adjustment=axes["breathing_room"] * 0.04,
            music_alignment_adjustment=axes["musicality"] * 0.04,
            allow_intentional_long_holds=axes["breathing_room"] >= -0.25,
            preserve_reactions=axes["reaction_patience"] >= -0.2,
            preserve_breaths=axes["breathing_room"] >= -0.2,
            transition_rules=[
                "prefer restrained motivated transitions"
                if axes["presentation_restraint"] >= 0
                else "permit visible transitions only when editorially motivated"
            ],
            reasons=[*profile.reasons, f"taste profile {profile.id}"],
            confidence=profile.confidence,
        )
    )
    recipes = {recipe.id: recipe for recipe in base.recipes}
    gates = {gate.id: gate for gate in base.gates}
    if profile.enabled_recipe_ids or profile.active_gate_ids:
        directives.append(
            EditorialDirective(
                id=f"{profile.id}:execution",
                hard_constraints=[
                    gates[gate_id].assertion
                    for gate_id in profile.active_gate_ids
                    if gates[gate_id].severity == "blocker"
                ],
                soft_constraints=[
                    gates[gate_id].assertion
                    for gate_id in profile.active_gate_ids
                    if gates[gate_id].severity == "warning"
                ],
                technique_preferences=[
                    recipes[recipe_id].name for recipe_id in profile.enabled_recipe_ids
                ],
                reasons=["context-selected recipes and observable quality gates"],
                confidence=profile.confidence,
            )
        )
    return directives


def _brief_terms(brief: EditorialBrief) -> set[str]:
    values = [
        brief.objective,
        brief.audience,
        brief.platform or "",
        brief.script_text or "",
        *brief.storyboard_requirements,
        *brief.style_keywords,
        brief.profile.value,
        *(modifier.value for modifier in brief.modifiers),
    ]
    return set(semantic_tokens(" ".join(values)))


def _category_bonus(category: str, brief: EditorialBrief) -> float:
    desired = {"story_beat", "safety_qc"}
    if brief.profile is EditorialProfile.DIALOGUE:
        desired |= {"dialogue_reaction", "audio_picture", "typography_caption"}
    elif brief.profile is EditorialProfile.NARRATION:
        desired |= {"selects", "presentation", "story_beat"}
    elif brief.profile is EditorialProfile.MONTAGE:
        desired |= {"sound_music", "rhythm_pacing", "presentation", "cut_points"}
    if WorkflowModifier.SHORT_FORM in brief.modifiers:
        desired |= {"typography_caption", "presentation", "sound_music"}
    if WorkflowModifier.LONG_FORM in brief.modifiers:
        desired |= {"story_beat", "dialogue_reaction", "rhythm_pacing"}
    if WorkflowModifier.RECAP in brief.modifiers:
        desired |= {"story_beat", "selects", "safety_qc"}
    if WorkflowModifier.PRODUCT_VIDEO in brief.modifiers:
        desired |= {"story_beat", "selects", "presentation", "safety_qc"}
    return 2.5 if category in desired else 0


def _capabilities(index: MediaUnderstandingIndex) -> set[str]:
    values: set[str] = set()
    if any(transcript.words for transcript in index.transcripts):
        values.add("has_dialogue")
    if index.music_events:
        values.add("has_reliable_music_beats")
    if any(shot.semantics.reaction_value > 0.25 for shot in index.shots):
        values.add("has_observable_reaction")
    if len({shot.media_id for shot in index.shots}) > 1:
        values.add("has_synchronized_alternate_angle")
    if any(shot.semantics.cutaway_value > 0.35 for shot in index.shots):
        values.add("has_semantically_matching_broll")
    if any(shot.semantics.evidence_value > 0.35 for shot in index.shots):
        values.add("has_visual_proof_candidate")
    values |= {"supports_readable_speed_change", "has_safe_transition_handles"}
    return values


def _principle_axes(
    selected: list[tuple[float, CanonicalPrinciple, list[str]]],
) -> dict[str, float]:
    sums: dict[str, float] = defaultdict(float)
    weights: dict[str, float] = defaultdict(float)
    for score, principle, _ in selected:
        weight = principle.confidence * min(2.5, 1 + math.log1p(score) / 3)
        for axis, value in principle.effect.taste_axes.items():
            sums[axis] += value * weight
            weights[axis] += weight
    return {
        axis: _clamp(sums[axis] / weights[axis] if weights[axis] else 0, -1, 1)
        for axis in TASTE_AXES
    }


def _reference_axes(profile: ReferenceEditProfile) -> dict[str, float]:
    p50 = profile.shot_duration_quantiles.get("p50")
    duration = float(p50.fraction) if p50 is not None else 3.0
    density = _clamp(
        profile.caption_density * 0.2
        + profile.graphic_density * 0.5
        + profile.sfx_event_density * 0.3,
        0,
        1,
    )
    return {
        "clarity": 0,
        "information_density": density * 2 - 0.5,
        "cut_energy": _clamp((3.0 - duration) / 2.5, -1, 1),
        "breathing_room": _clamp(profile.silence_ratio * 3 - 0.35, -1, 1),
        "reaction_patience": _clamp(profile.silence_ratio * 2 - 0.2, -1, 1),
        "visual_proof": 0,
        "continuity_strictness": 0,
        "musicality": profile.music_sync_score * 2 - 0.5,
        "novelty": _clamp((1 - profile.repetition_score) * 1.5 - 0.5, -1, 1),
        "presentation_restraint": _clamp(0.7 - density * 1.4, -1, 1),
        "camera_motion": _clamp(profile.camera_motion_frequency * 2 - 0.5, -1, 1),
    }


def _blend_axes(
    base: dict[str, float], reference: dict[str, float], influence: float
) -> dict[str, float]:
    return {
        axis: _clamp(base[axis] * (1 - influence) + reference[axis] * influence, -1, 1)
        for axis in TASTE_AXES
    }


def _resolve_conflicts(
    base: ConsolidatedKnowledgeBase,
    selected: list[tuple[float, CanonicalPrinciple, list[str]]],
    axes: dict[str, float],
) -> dict[str, str]:
    active = {principle.id for _, principle, _ in selected}
    resolutions: dict[str, str] = {}
    for conflict in base.conflicts:
        if not (active & set(conflict.principle_ids)):
            continue
        direction = axes.get(conflict.axis, conflict.default_direction)
        resolutions[conflict.id] = (
            "positive_context_variant"
            if direction > 0.1
            else "negative_context_variant"
            if direction < -0.1
            else "neutral_context_fallback"
        )
    return resolutions


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _route_recipes(
    base: ConsolidatedKnowledgeBase,
    terms: set[str],
    capabilities: set[str] | None,
    brief: EditorialBrief,
) -> list[str]:
    ranked: list[tuple[float, str]] = []
    for recipe in base.recipes:
        if capabilities is not None and not set(recipe.prerequisite_capabilities) <= capabilities:
            continue
        overlap = len(terms & set(recipe.applicability_terms))
        name_overlap = len(terms & set(semantic_tokens(recipe.name)))
        score = overlap * 1.2 + name_overlap * 0.8 + _category_bonus(recipe.category, brief)
        if score >= 2.0:
            ranked.append((score, recipe.id))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [recipe_id for _, recipe_id in ranked[:12]]


def _route_gates(base: ConsolidatedKnowledgeBase, terms: set[str]) -> list[str]:
    ranked: list[tuple[float, str]] = []
    for gate in base.gates:
        overlap = len(terms & set(gate.context_terms))
        assertion_overlap = len(terms & set(semantic_tokens(gate.assertion)))
        score = overlap + assertion_overlap * 0.5 + (4 if gate.severity == "blocker" else 0)
        if score >= 2.0:
            ranked.append((score, gate.id))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [gate_id for _, gate_id in ranked[:30]]
