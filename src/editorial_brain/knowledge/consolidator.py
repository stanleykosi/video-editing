"""Deterministic consolidation of tutorial-derived items into canonical taste."""

from __future__ import annotations

import math
from collections import defaultdict

from editorial_brain.core.hashing import fingerprint
from editorial_brain.knowledge.atomic import AtomicStatement, extract_atomic_statements
from editorial_brain.knowledge.models import (
    CanonicalPrinciple,
    ConsolidatedKnowledgeBase,
    ConsolidationStatistics,
    KnowledgeCatalog,
    KnowledgeConflict,
    KnowledgeItem,
    KnowledgeKind,
    PrincipleEffect,
    PrinciplePolarity,
    PrincipleScope,
    PrincipleTier,
    QualityGate,
    TechniqueRecipe,
)
from editorial_brain.knowledge.normalize import semantic_tokens, similarity

CONSOLIDATION_VERSION = "source-neutral-v1"


def consolidate_catalog(catalog: KnowledgeCatalog) -> ConsolidatedKnowledgeBase:
    atomic = extract_atomic_statements(catalog)
    principle_atomic = [statement for statement in atomic if _is_principle(statement)]
    clusters = _clusters(principle_atomic)
    principles = [
        _principle([principle_atomic[index] for index in cluster]) for cluster in clusters
    ]
    principles.sort(key=lambda item: item.id)
    conflicts, principles = _conflicts(principles)
    recipes = _recipes(catalog)
    gates = _gates(atomic)
    duplicate_clusters = sum(len(cluster) > 1 for cluster in clusters)
    statistics = ConsolidationStatistics(
        input_items=len(catalog.items),
        atomic_statements=len(atomic),
        canonical_principles=len(principles),
        technique_recipes=len(recipes),
        quality_gates=len(gates),
        duplicate_statements_removed=len(principle_atomic) - len(principles),
        duplicate_clusters=duplicate_clusters,
        conflicts_resolved=len(conflicts),
        unresolved_conflicts=0,
        principle_reduction_ratio=(1 - len(principles) / len(atomic)) if atomic else 0,
        total_construct_reduction_ratio=(
            1 - (len(principles) + len(recipes) + len(gates)) / len(atomic) if atomic else 0
        ),
    )
    payload = {
        "version": CONSOLIDATION_VERSION,
        "input_fingerprint": catalog.fingerprint,
        "principles": principles,
        "recipes": recipes,
        "gates": gates,
        "conflicts": conflicts,
        "statistics": statistics,
    }
    return ConsolidatedKnowledgeBase(
        input_fingerprint=catalog.fingerprint,
        fingerprint=fingerprint(payload),
        principles=principles,
        recipes=recipes,
        gates=gates,
        conflicts=conflicts,
        statistics=statistics,
    )


def _clusters(
    statements: list[AtomicStatement],
    *,
    known_threshold: float = 0.46,
    generic_threshold: float = 0.68,
) -> list[list[int]]:
    parent = list(range(len(statements)))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    exact: dict[tuple[object, ...], int] = {}
    postings: dict[tuple[object, ...], list[int]] = defaultdict(list)
    for index, statement in enumerate(statements):
        family = _family(statement)
        bucket = (_domain(statement), statement.scope, statement.polarity, family)
        key = (*bucket, statement.tokens)
        previous = exact.get(key)
        if previous is not None:
            union(previous, index)
        else:
            exact[key] = index
        candidates: set[int] = set()
        for token in statement.tokens:
            candidates.update(postings[(*bucket, token)])
        for other in sorted(candidates):
            other_statement = statements[other]
            shared = len(set(statement.tokens) & set(other_statement.tokens))
            minimum_tokens = min(len(statement.tokens), len(other_statement.tokens))
            overlap_ratio = 0.35 if family != "generic" else 0.5
            if shared < max(2, math.ceil(minimum_tokens * overlap_ratio)):
                continue
            threshold = known_threshold if family != "generic" else generic_threshold
            if similarity(statement.tokens, other_statement.tokens) >= threshold:
                union(other, index)
        for token in statement.tokens:
            postings[(*bucket, token)].append(index)
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(statements)):
        groups[find(index)].append(index)
    return sorted(groups.values(), key=lambda group: group[0])


def _principle(cluster: list[AtomicStatement]) -> CanonicalPrinciple:
    chosen = sorted(cluster, key=lambda item: (-_statement_quality(item.text), item.text))[0]
    contexts = sorted({term for item in cluster for term in item.context_terms})[:80]
    exclusions = sorted({term for item in cluster for term in item.exclusion_terms})[:80]
    signature = "|".join(
        (
            _domain(chosen),
            chosen.scope.value,
            chosen.polarity.value,
            " ".join(chosen.tokens),
        )
    )
    specificity = min(1, len(chosen.tokens) / 18)
    return CanonicalPrinciple(
        id=f"principle:{fingerprint(signature)[:20]}",
        statement=chosen.text,
        normalized_signature=signature,
        category=_domain(chosen),
        scope=chosen.scope,
        tier=_tier(chosen),
        polarity=chosen.polarity,
        context_terms=contexts,
        exclusion_terms=exclusions,
        prerequisite_capabilities=_prerequisites(chosen.text),
        incompatibility_groups=_incompatibilities(chosen.text),
        support_count=len(cluster),
        specificity=specificity,
        confidence=min(0.98, 0.62 + specificity * 0.25),
        effect=_effect(chosen.text, _domain(chosen), chosen.polarity),
    )


def _tier(statement: AtomicStatement) -> PrincipleTier:
    text = statement.text.lower()
    if statement.polarity is PrinciplePolarity.REQUIRE and any(
        term in text
        for term in ("inside a word", "rights", "watermark", "source range", "must not")
    ):
        return PrincipleTier.INVARIANT
    if any(term in text for term in ("meaning", "proof", "evidence", "clarity", "story")):
        return PrincipleTier.MEANING
    if statement.scope is PrincipleScope.CONTINUITY:
        return PrincipleTier.CONTINUITY
    if statement.scope in {PrincipleScope.RHYTHM, PrincipleScope.DIALOGUE}:
        return PrincipleTier.RHYTHM
    if statement.scope in {PrincipleScope.PRESENTATION, PrincipleScope.WORKFLOW}:
        return PrincipleTier.DECORATION
    return PrincipleTier.STYLE


def _effect(text: str, category: str, polarity: PrinciplePolarity) -> PrincipleEffect:
    lower = text.lower()
    sign = -1.0 if polarity is PrinciplePolarity.AVOID else 1.0
    cut: dict[str, float] = {}
    selects: dict[str, float] = {}
    axes: dict[str, float] = {}
    preferred = minimum = maximum = 1.0
    breathing = music = 0.0
    reactions = breaths = holds = None
    transitions: list[str] = []
    if any(term in lower for term in ("proof", "evidence", "show the", "readable", "clarity")):
        cut["visual_relevance"] = 0.035 * sign
        selects["evidence_value"] = 0.02 * sign
        axes["visual_proof"] = 0.7 * sign
        axes["clarity"] = 0.55 * sign
    if any(term in lower for term in ("reaction", "aftermath", "emotional", "dramatic pause")):
        cut["reaction_preservation"] = 0.05 * sign
        cut["emotional_continuity"] = 0.035 * sign
        selects["reaction_value"] = 0.02 * sign
        axes["reaction_patience"] = 0.8 * sign
        reactions = holds = polarity is not PrinciplePolarity.AVOID
    if any(term in lower for term in ("breath", "silence", "breathing room", "natural cadence")):
        cut["speech_integrity"] = 0.04 * sign
        axes["breathing_room"] = 0.7 * sign
        breathing = 0.01 * sign
        breaths = polarity is not PrinciplePolarity.AVOID
    if any(term in lower for term in ("continuity", "screen direction", "eyeline", "room tone")):
        cut["visual_continuity"] = 0.035 * sign
        cut["audio_continuity"] = 0.025 * sign
        axes["continuity_strictness"] = 0.65 * sign
    if any(term in lower for term in ("beat", "music cue", "musical phrase", "downbeat")):
        cut["rhythm"] = 0.04 * sign
        axes["musicality"] = 0.7 * sign
        music = 0.012 * sign
    if any(term in lower for term in ("novel", "variety", "repetition", "pattern break")):
        cut["visual_novelty"] = 0.03 * sign
        selects["novelty"] = 0.015 * sign
        axes["novelty"] = 0.55 * sign
    if any(term in lower for term in ("fast", "rapid", "tighten", "short-form", "high energy")):
        axes["cut_energy"] = 0.65 * sign
        axes["information_density"] = 0.45 * sign
        preferred, minimum = (0.94, 0.94) if sign > 0 else (1.06, 1.04)
    if any(term in lower for term in ("slow", "long hold", "linger", "let the moment")):
        axes["cut_energy"] = -0.7 * sign
        axes["breathing_room"] = 0.7 * sign
        preferred, maximum = (1.08, 1.15) if sign > 0 else (0.94, 0.95)
        holds = sign > 0
    if any(term in lower for term in ("caption", "graphic", "effect", "decoration")):
        if any(term in lower for term in ("restrain", "avoid", "do not", "only when")):
            axes["presentation_restraint"] = 0.6 * sign
        elif any(term in lower for term in ("kinetic", "dynamic", "animated", "bold")):
            axes["presentation_restraint"] = -0.35 * sign
    if any(term in lower for term in ("camera motion", "zoom", "pan", "push-in")):
        axes["camera_motion"] = 0.5 * sign
    if "transition" in lower:
        transitions.append(
            "prefer restrained motivated transitions"
            if any(term in lower for term in ("avoid", "restrain", "motivat", "only"))
            else "permit stylized transitions only when story or motion motivates them"
        )
    if category == "story_beat" and any(
        term in lower for term in ("story", "meaning", "context", "payoff", "clarity")
    ):
        cut["story_progression"] = 0.03 * sign
        axes.setdefault("clarity", 0.25 * sign)
    return PrincipleEffect(
        cut_adjustments=cut,
        select_adjustments=selects,
        taste_axes=axes,
        preferred_duration_multiplier=preferred,
        minimum_duration_multiplier=minimum,
        maximum_duration_multiplier=maximum,
        breathing_room_adjustment=breathing,
        music_alignment_adjustment=music,
        preserve_reactions=reactions,
        preserve_breaths=breaths,
        allow_intentional_long_holds=holds,
        transition_preferences=transitions,
    )


def _prerequisites(text: str) -> list[str]:
    lower = text.lower()
    values: list[str] = []
    mapping = {
        "beat": "has_reliable_music_beats",
        "reaction": "has_observable_reaction",
        "alternate angle": "has_synchronized_alternate_angle",
        "b-roll": "has_semantically_matching_broll",
        "speed": "supports_readable_speed_change",
        "transition handle": "has_safe_transition_handles",
        "proof": "has_visual_proof_candidate",
    }
    for term, capability in mapping.items():
        if term in lower:
            values.append(capability)
    return values


def _incompatibilities(text: str) -> list[str]:
    lower = text.lower()
    values: list[str] = []
    if "speed" in lower and any(term in lower for term in ("dialogue", "lip sync", "natural")):
        values.append("natural_dialogue_vs_speed_change")
    if "caption" in lower and any(term in lower for term in ("face", "product ui", "proof")):
        values.append("caption_vs_visual_proof_region")
    if "transition" in lower:
        values.append("transition_intensity")
    return values


def _conflicts(
    principles: list[CanonicalPrinciple],
) -> tuple[list[KnowledgeConflict], list[CanonicalPrinciple]]:
    by_axis: dict[str, dict[int, list[str]]] = defaultdict(lambda: {-1: [], 1: []})
    for principle in principles:
        for axis, value in principle.effect.taste_axes.items():
            if value:
                by_axis[axis][1 if value > 0 else -1].append(principle.id)
    conflicts: list[KnowledgeConflict] = []
    variant_ids: dict[str, str] = {}
    for axis, directions in sorted(by_axis.items()):
        if not directions[-1] or not directions[1]:
            continue
        ids = sorted(directions[-1] + directions[1])
        conflict_id = f"conflict:{fingerprint((axis, ids))[:20]}"
        conflicts.append(
            KnowledgeConflict(
                id=conflict_id,
                axis=axis,
                principle_ids=ids,
                resolution="contextual_variant",
                default_direction=0,
                reason_code="brief_and_reference_select_legal_context_variant",
            )
        )
        for principle_id in ids:
            variant_ids[principle_id] = f"variant:{axis}"
    updated = [
        principle.model_copy(update={"variant_group": variant_ids.get(principle.id)})
        for principle in principles
    ]
    return conflicts, updated


def _statement_quality(value: str) -> float:
    tokens = semantic_tokens(value)
    length_score = 1 - min(abs(len(value) - 140) / 280, 0.8)
    specificity = min(len(tokens) / 16, 1)
    generic_penalty = 0.2 if value.lower().startswith(("use this", "apply this")) else 0
    return length_score + specificity - generic_penalty


def _is_principle(statement: AtomicStatement) -> bool:
    if statement.polarity is PrinciplePolarity.VERIFY:
        return False
    if statement.scope in {PrincipleScope.QC, PrincipleScope.WORKFLOW}:
        return False
    if _family(statement) != "generic":
        return True
    return _tier(statement) in {
        PrincipleTier.INVARIANT,
        PrincipleTier.MEANING,
        PrincipleTier.CONTINUITY,
        PrincipleTier.RHYTHM,
    }


def _gates(statements: list[AtomicStatement]) -> list[QualityGate]:
    values = [
        statement
        for statement in statements
        if statement.polarity is PrinciplePolarity.VERIFY or statement.scope is PrincipleScope.QC
    ]
    clusters = _clusters(values, known_threshold=0.4, generic_threshold=0.55)
    gates: list[QualityGate] = []
    for cluster in clusters:
        members = [values[index] for index in cluster]
        chosen = sorted(members, key=lambda item: (-_statement_quality(item.text), item.text))[0]
        signature = "|".join((_domain(chosen), " ".join(chosen.tokens)))
        lower = chosen.text.lower()
        blocker = any(
            term in lower
            for term in (
                "inside a word",
                "watermark",
                "rights",
                "missing",
                "unreadable",
                "source range",
                "speech clarity",
            )
        )
        gates.append(
            QualityGate(
                id=f"gate:{fingerprint(signature)[:20]}",
                assertion=chosen.text,
                category=_domain(chosen),
                context_terms=sorted({term for member in members for term in member.context_terms})[
                    :80
                ],
                severity="blocker" if blocker else "warning",
                deterministic=any(
                    term in lower for term in ("duration", "range", "word", "hash", "resolution")
                ),
            )
        )
    return sorted({gate.id: gate for gate in gates}.values(), key=lambda item: item.id)


def _recipes(catalog: KnowledgeCatalog) -> list[TechniqueRecipe]:
    items = [
        item
        for item in catalog.items
        if item.kind
        in {
            KnowledgeKind.TECHNIQUE,
            KnowledgeKind.PRESET,
            KnowledgeKind.STYLE,
            KnowledgeKind.PLAYBOOK,
        }
        and item.rules
        and not item.id.endswith(":_template")
    ]
    groups: list[list[KnowledgeItem]] = []
    for item in sorted(items, key=lambda value: (value.title, value.id)):
        tokens = semantic_tokens(item.title)
        matched: list[KnowledgeItem] | None = None
        for group in groups:
            representative = group[0]
            representative_tokens = semantic_tokens(representative.title)
            if similarity(tokens, representative_tokens) >= 0.72:
                matched = group
                break
        if matched is None:
            groups.append([item])
        else:
            matched.append(item)
    recipes: list[TechniqueRecipe] = []
    for group in groups:
        members = list(group)
        chosen = sorted(members, key=lambda value: (len(value.title), value.title))[0]
        steps: list[str] = []
        seen: set[tuple[str, ...]] = set()
        for member in members:
            for rule in member.rules:
                if rule.startswith(("Verify:", "Avoid:")):
                    continue
                signature = semantic_tokens(rule)
                if len(signature) < 3 or signature in seen:
                    continue
                seen.add(signature)
                steps.append(rule)
        if not steps:
            continue
        title_tokens = semantic_tokens(chosen.title)
        recipe_signature = " ".join(title_tokens)
        all_text = " ".join(steps)
        recipes.append(
            TechniqueRecipe(
                id=f"recipe:{fingerprint(recipe_signature)[:20]}",
                name=chosen.title,
                category=_recipe_domain(chosen.category),
                applicability_terms=sorted(
                    {
                        term
                        for member in members
                        for value in member.use_when
                        for term in semantic_tokens(value)
                    }
                )[:100],
                exclusion_terms=sorted(
                    {
                        term
                        for member in members
                        for value in member.avoid_when
                        for term in semantic_tokens(value)
                    }
                )[:100],
                steps=steps[:20],
                prerequisite_capabilities=_prerequisites(all_text),
                incompatibility_groups=_incompatibilities(all_text),
                confidence=0.8,
            )
        )
    return sorted({item.id: item for item in recipes}.values(), key=lambda item: item.id)


def _recipe_domain(category: str) -> str:
    return {
        "captions": "typography_caption",
        "typography": "typography_caption",
        "beat_sync": "sound_music",
        "sound_design": "sound_music",
        "story_pacing": "story_beat",
        "retention": "story_beat",
        "nle_workflow": "workflow_recipe",
        "genre_workflow": "workflow_recipe",
        "qc": "safety_qc",
    }.get(category, category)


def _domain(statement: AtomicStatement) -> str:
    if statement.scope is PrincipleScope.QC:
        return "safety_qc"
    if statement.scope is PrincipleScope.DIALOGUE:
        return "dialogue_reaction"
    if statement.scope is PrincipleScope.AUDIO_PICTURE:
        return "audio_picture"
    if statement.scope is PrincipleScope.CONTINUITY:
        return "continuity"
    if statement.scope is PrincipleScope.SELECT:
        return "selects"
    if statement.scope is PrincipleScope.CUT:
        return "cut_points"
    if statement.scope is PrincipleScope.RHYTHM:
        return "rhythm_pacing"
    if statement.scope is PrincipleScope.PRESENTATION:
        return {
            "captions": "typography_caption",
            "typography": "typography_caption",
            "sound_design": "sound_music",
            "beat_sync": "sound_music",
            "color": "color",
        }.get(statement.category, "presentation")
    if statement.scope is PrincipleScope.WORKFLOW:
        return "workflow_recipe"
    return "story_beat"


def _family(statement: AtomicStatement) -> str:
    effect = _effect(statement.text, _domain(statement), statement.polarity)
    if effect.taste_axes:
        return "+".join(sorted(effect.taste_axes))
    if effect.cut_adjustments:
        return "+".join(sorted(effect.cut_adjustments))
    if effect.select_adjustments:
        return "+".join(sorted(effect.select_adjustments))
    return "generic"
