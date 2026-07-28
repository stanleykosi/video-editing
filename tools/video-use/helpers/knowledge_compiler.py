"""Compile routed editing knowledge into renderable creative directives.

The knowledge router answers "what should the agents read?"  This compiler
answers "what must the timeline and renderer actually do with that knowledge?"
It intentionally produces concrete layer contracts for captions, motion, sound,
color, transitions, and QC so from-scratch videos cannot collapse into stitched
clips plus plain subtitles.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]

CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "retention": ("retention", "hook", "intro", "story", "pacing", "viral"),
    "captions": ("caption", "captions", "subtitle", "subtitles", "typography", "text"),
    "motion": ("motion", "keyframe", "zoom", "pan", "transition", "mask", "glow", "animation", "remotion", "capcut"),
    "sound": ("sound", "sfx", "audio", "music", "whoosh", "duck", "foley", "mix"),
    "color": ("color", "grade", "grading", "contrast", "palette", "lumetri"),
    "assets": ("asset", "stock", "footage", "image", "manifest", "generated"),
    "qc": ("qc", "checklist", "quality", "readability", "publish"),
}

FALLBACK_TECHNIQUES: dict[str, list[str]] = {
    "retention": [
        "knowledge/techniques/retention/retention_first_three_second_dynamic_zoom_hook_001.json",
        "knowledge/techniques/retention/retention_shortform_claim_hook_001.json",
        "knowledge/techniques/story_pacing/build_peak_release_duration_arc.json",
    ],
    "captions": [
        "knowledge/techniques/captions/captions_two_word_social_subtitles_001.json",
        "knowledge/techniques/typography/typography_programmatic_text_mask_highlight_glow_001.json",
        "knowledge/techniques/typography/typography_sentence_structure_line_breaks_001.json",
    ],
    "motion": [
        "knowledge/techniques/motion/motion_show_dont_tell_visual_stack_001.json",
        "knowledge/techniques/motion/motion_overlay_readability_focus_stack_001.json",
        "knowledge/techniques/motion/motion_keyframe_focus_zoom_hold_001.json",
    ],
    "sound": [
        "knowledge/techniques/sound_design/sound_infographic_motion_sfx_sync_001.json",
        "knowledge/techniques/sound_design/sound_music_ducking_volume_keyframes_001.json",
        "knowledge/techniques/sound_design/sound_isolated_sfx_design_pass_001.json",
    ],
    "color": [
        "knowledge/techniques/color/davinci_color_management_primary_look_001.json",
        "knowledge/techniques/color/color_keyframed_saturation_shift_001.json",
        "knowledge/techniques/color/color_filter_strength_music_reveal_001.json",
    ],
    "qc": [
        "knowledge/techniques/qc/qc_publish_threshold_creative_iteration_001.json",
    ],
}

FALLBACK_PRESETS: dict[str, list[str]] = {
    "captions": [
        "knowledge/presets/captions/two_word_social_subtitles.md",
        "knowledge/presets/captions/shorts_readable_contrast.md",
        "knowledge/presets/captions/typographic_hierarchy_caption_system.md",
    ],
    "motion": [
        "knowledge/presets/motion/first_three_second_dynamic_zoom_hook.md",
        "knowledge/presets/motion/remotion_text_mask_highlight_glow.md",
        "knowledge/presets/motion/overlay_readability_focus_stack.md",
    ],
    "sound": [
        "knowledge/presets/sound/infographic_motion_sfx_sync.md",
        "knowledge/presets/sound/music_ducking_volume_keyframes.md",
        "knowledge/presets/sound/reverse_hit_whoosh_motion_sync.md",
    ],
    "color": [
        "knowledge/presets/color/subtle_lumetri_adjustment_layer.md",
        "knowledge/presets/color/typography_contrast_palette.md",
    ],
    "transitions": [
        "knowledge/presets/transitions/short_form_micro_black_drop.md",
        "knowledge/presets/transitions/davinci_white_flash.md",
    ],
}

RENDERABLE_EFFECT_OPTIONS: list[dict[str, Any]] = [
    {
        "effect_id": "capcut_highlight_wipe",
        "layer_type": "emphasis_text",
        "source_paths": [
            "knowledge/techniques/typography/typography_capcut_color_change_highlight_wipe_001.json",
            "knowledge/techniques/typography/typography_programmatic_text_mask_highlight_glow_001.json",
            "knowledge/presets/motion/capcut_color_change_highlight_wipe.md",
            "knowledge/presets/motion/remotion_text_mask_highlight_glow.md",
        ],
        "use_when": ["claim", "keyword", "payoff", "premium title", "short quote"],
        "avoid_when": ["long subtitle", "busy proof frame", "text-heavy scene"],
        "sound_cue": "highlight_shimmer",
    },
    {
        "effect_id": "capcut_staggered_blur_glitch_reveal",
        "layer_type": "emphasis_text",
        "source_paths": [
            "knowledge/techniques/typography/typography_capcut_staggered_blur_glitch_reveal_001.json",
            "knowledge/techniques/typography/typography_remotion_seeded_scramble_glitch_001.json",
            "knowledge/presets/motion/capcut_staggered_blur_glitch_reveal.md",
            "knowledge/presets/motion/remotion_seeded_glitch_scramble_text.md",
        ],
        "use_when": ["hook", "first beat", "surprise claim", "fast social title"],
        "avoid_when": ["serious body explanation", "dense sentence", "accessibility caption"],
        "sound_cue": "glitch_tick",
    },
    {
        "effect_id": "capcut_axis_stretch_word",
        "layer_type": "word_emphasis",
        "source_paths": [
            "knowledge/techniques/typography/typography_capcut_axis_stretch_emphasis_001.json",
            "knowledge/presets/motion/capcut_axis_stretch_word.md",
        ],
        "use_when": ["single impact word", "hook word", "payoff word"],
        "avoid_when": ["long phrase", "brand font must stay undistorted"],
        "sound_cue": "tiny_pop",
    },
    {
        "effect_id": "capcut_font_shift_loop",
        "layer_type": "word_emphasis",
        "source_paths": [
            "knowledge/techniques/typography/typography_capcut_font_shift_loop_001.json",
            "knowledge/presets/motion/capcut_font_shift_loop.md",
        ],
        "use_when": ["unstable idea", "myth vs truth", "style beat", "social hook"],
        "avoid_when": ["serious factual proof", "continuous captions"],
        "sound_cue": "font_tick",
    },
    {
        "effect_id": "player3_smooth_caption_compound",
        "layer_type": "caption_kinetic",
        "source_paths": [
            "knowledge/techniques/captions/captions_capcut_player3_smooth_caption_compounds_001.json",
            "knowledge/presets/captions/capcut_player3_smooth_captions.md",
        ],
        "use_when": ["caption support", "premium social caption", "clean phrase group"],
        "avoid_when": ["text-heavy scene", "proof/UI/faces in lower safe region"],
        "sound_cue": "",
    },
    {
        "effect_id": "capcut_adaptive_texture_caption",
        "layer_type": "caption_kinetic",
        "source_paths": [
            "knowledge/techniques/captions/captions_capcut_adaptive_texture_animation_001.json",
            "knowledge/presets/captions/capcut_adaptive_texture_captions.md",
        ],
        "use_when": ["stock footage background", "simple social caption pass"],
        "avoid_when": ["busy background", "accessibility-critical line"],
        "sound_cue": "",
    },
    {
        "effect_id": "capcut_apple_slide_up_text",
        "layer_type": "emphasis_text",
        "source_paths": [
            "knowledge/techniques/typography/typography_capcut_apple_slide_up_text_001.json",
            "knowledge/presets/motion/capcut_apple_slide_up_text.md",
        ],
        "use_when": ["calm premium explainer", "body section label", "takeaway"],
        "avoid_when": ["chaotic/high-energy beat"],
        "sound_cue": "soft_slide",
    },
    {
        "effect_id": "capcut_perspective_freeze_text",
        "layer_type": "emphasis_text",
        "source_paths": [
            "knowledge/techniques/typography/typography_capcut_perspective_freeze_text_001.json",
            "knowledge/presets/motion/capcut_perspective_freeze_text.md",
        ],
        "use_when": ["scene-attached word", "diagram label", "environment text"],
        "avoid_when": ["flat subtitle", "tiny unreadable text"],
        "sound_cue": "soft_hit",
    },
    {
        "effect_id": "capcut_graph_zoom_stack",
        "layer_type": "camera_motion",
        "source_paths": [
            "knowledge/techniques/motion/motion_capcut_graph_zoom_stack_001.json",
            "knowledge/techniques/motion/motion_keyframe_focus_zoom_hold_001.json",
            "knowledge/presets/motion/capcut_graph_zoom_stack.md",
            "knowledge/presets/motion/focus_zoom_hold_keyframes.md",
        ],
        "use_when": ["hook jolt", "focus target", "payoff reveal"],
        "avoid_when": ["proof would crop", "caption would become unreadable"],
        "sound_cue": "short_whoosh",
    },
    {
        "effect_id": "infographic_sfx_sync",
        "layer_type": "sound_cue",
        "source_paths": [
            "knowledge/techniques/sound_design/sound_infographic_motion_sfx_sync_001.json",
            "knowledge/techniques/sound_design/sound_sfx_variation_exaggeration_001.json",
            "knowledge/presets/sound/infographic_motion_sfx_sync.md",
            "knowledge/presets/sound/reverse_hit_whoosh_motion_sync.md",
        ],
        "use_when": ["arrow", "chart", "highlight", "diagram", "text reveal"],
        "avoid_when": ["no visible event", "speech would be masked"],
        "sound_cue": "event_matched_sfx",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_selected(plan: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    selected = plan.get("selected", {})
    if isinstance(selected, dict):
        for kind, values in selected.items():
            for value in values or []:
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("kind", kind)
                    items.append(item)
    return items


def score_category(path: str, title: str, category: str) -> str:
    haystack = f"{path} {title} {category}".lower()
    best = "assets"
    best_score = -1
    for name, terms in CATEGORY_TERMS.items():
        score = sum(1 for term in terms if term in haystack)
        if score > best_score:
            best = name
            best_score = score
    if "/transitions/" in haystack or "transition" in haystack:
        return "transitions"
    return best


def selected_paths_by_category(items: list[dict[str, Any]], kind_filter: str | None = None) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for item in sorted(items, key=lambda x: int(x.get("score", 0)), reverse=True):
        path = str(item.get("path", ""))
        if not path:
            continue
        kind = str(item.get("kind", ""))
        if kind_filter and kind != kind_filter:
            continue
        category = score_category(path, str(item.get("title", "")), str(item.get("category", "")))
        if path not in grouped[category]:
            grouped[category].append(path)
    return grouped


def ensure_fallbacks(grouped: dict[str, list[str]], fallbacks: dict[str, list[str]], limit: int) -> dict[str, list[str]]:
    result = {key: list(value[:limit]) for key, value in grouped.items()}
    for category, paths in fallbacks.items():
        bucket = result.setdefault(category, [])
        for path in paths:
            if path not in bucket and (REPO_ROOT / path).exists():
                bucket.append(path)
        result[category] = bucket[:limit]
    return result


def discover_repo_files(directory: str, suffix: str) -> list[str]:
    root = REPO_ROOT / directory
    if not root.exists():
        return []
    return sorted(rel(path) for path in root.rglob(f"*{suffix}") if path.is_file())


def group_discovered_paths(paths: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        category = score_category(path, "", "")
        grouped[category].append(path)
    return grouped


def expand_with_repo_options(
    grouped: dict[str, list[str]],
    directory: str,
    suffix: str,
    per_category_limit: int = 200,
) -> dict[str, list[str]]:
    """Keep selected/fallback paths first, then preserve all repo options."""
    result = {category: list(paths) for category, paths in grouped.items()}
    discovered = group_discovered_paths(discover_repo_files(directory, suffix))
    for category, paths in discovered.items():
        bucket = result.setdefault(category, [])
        for path in paths:
            if path not in bucket:
                bucket.append(path)
        result[category] = bucket[:per_category_limit]
    return result


def build_option_bank(
    technique_groups: dict[str, list[str]],
    preset_groups: dict[str, list[str]],
) -> dict[str, Any]:
    option_techniques = expand_with_repo_options(
        technique_groups, "knowledge/techniques", ".json"
    )
    option_presets = expand_with_repo_options(preset_groups, "knowledge/presets", ".md")
    return {
        "selection_policy": {
            "compiler_role": "surface options and constraints, not force one global style",
            "strict_about": [
                "no basic stitched clips",
                "asset rights",
                "phone readability",
                "caption/proof/faces/UI safety",
                "speech-dominant audio mix",
            ],
            "flexible_about": [
                "which caption style to use per beat",
                "which CapCut-style typography effect to use",
                "whether to suppress captions over designed text",
                "SFX density and tone",
                "camera motion intensity",
                "visual support type",
            ],
            "per_beat_rule": "Timeline builder chooses from the option bank based on beat purpose, visual job, tone, and QC risk.",
            "do_not": [
                "collapse the whole video into one caption preset",
                "apply every technique at once",
                "ignore an option because it is not the first selected card",
                "treat optional effects as mandatory decoration",
            ],
        },
        "technique_options_by_category": option_techniques,
        "preset_options_by_category": option_presets,
        "renderable_effect_options": RENDERABLE_EFFECT_OPTIONS,
    }


def read_card_summary(path: str) -> dict[str, Any]:
    full = REPO_ROOT / path
    if not full.exists() or full.suffix.lower() != ".json":
        return {"path": path}
    try:
        card = load_json(full)
    except Exception:
        return {"path": path}
    return {
        "id": card.get("id") or full.stem,
        "name": card.get("name") or full.stem.replace("_", " ").title(),
        "path": path,
        "category": card.get("category", ""),
        "implementation": card.get("implementation", {}),
        "qc": card.get("qc", [])[:8],
    }


def style_from_pack(plan: dict[str, Any]) -> dict[str, Any]:
    style_path = plan.get("style_pack", {}).get("path") if isinstance(plan.get("style_pack"), dict) else ""
    style: dict[str, Any] = {}
    if style_path and (REPO_ROOT / style_path).exists():
        try:
            style = load_json(REPO_ROOT / style_path)
        except Exception:
            style = {}
    visual_language = style.get("visual_language", {})
    voiceover = style.get("voiceover", {})
    return {
        "style_pack": style.get("id") or plan.get("video_type") or "",
        "name": style.get("name") or "Knowledge-Driven Edit",
        "resolution": style.get("default_platform", {}).get("resolution", "1080x1920"),
        "fps": int(style.get("default_platform", {}).get("fps", 30)),
        "accent_color": "#38bdf8",
        "secondary_accent": "#facc15",
        "danger_accent": "#fb7185",
        "background_tint": "#08111f",
        "font_family": "DejaVu Sans",
        "caption_position": "lower_safe",
        "visual_language": visual_language,
        "voiceover": voiceover,
    }


def build_directive(plan: dict[str, Any]) -> dict[str, Any]:
    items = flatten_selected(plan)
    technique_groups = ensure_fallbacks(
        selected_paths_by_category(items, "technique_card"),
        FALLBACK_TECHNIQUES,
        limit=24,
    )
    preset_groups = ensure_fallbacks(
        selected_paths_by_category(items, "preset"),
        FALLBACK_PRESETS,
        limit=24,
    )
    option_bank = build_option_bank(technique_groups, preset_groups)

    selected_skills = [item["path"] for item in items if item.get("kind") == "skill" and item.get("path")]
    selected_qc = [item["path"] for item in items if item.get("kind") == "qc_checklist" and item.get("path")]

    style = style_from_pack(plan)
    caption_cards = [read_card_summary(path) for path in technique_groups.get("captions", [])]
    motion_cards = [read_card_summary(path) for path in technique_groups.get("motion", [])]
    sound_cards = [read_card_summary(path) for path in technique_groups.get("sound", [])]
    color_cards = [read_card_summary(path) for path in technique_groups.get("color", [])]

    return {
        "schema_version": 1,
        "created_at": utc_now(),
        "brief": plan.get("brief", ""),
        "video_type": plan.get("video_type", ""),
        "project_contract": {
            "no_basic_outputs": True,
            "knowledge_must_compile_to_layers": True,
            "creative_option_mode": "open_option_bank",
            "strictness": "strict quality floor, flexible creative technique selection",
            "minimum_layers_per_beat": 6,
            "required_layer_types": [
                "camera_motion",
                "caption_kinetic",
                "emphasis_text",
                "visual_motion_overlay",
                "color_grade",
                "sound_cue",
            ],
            "required_role_groups": {
                "visual_motion": ["camera_motion", "visual_motion_overlay", "compositing_effect", "motion_graphic"],
                "text_hierarchy": ["caption_kinetic", "emphasis_text", "word_emphasis", "designed_scene_text"],
                "audio_sync": ["sound_cue", "music_cue", "sfx_event"],
                "finish": ["color_grade", "transition", "qc_rule"],
            },
            "layer_substitution_policy": "Required layer types are the default contract; a richer equivalent layer may satisfy the role when it records its substitution reason and QC risk.",
            "required_global_artifacts": [
                "knowledge_plan.json",
                "creative_directive.json",
                "edit_decision_list.json",
                "captions/captions.json",
                "asset_manifest.json",
                "preview.mp4",
                "final.mp4",
                "qc_report.md",
            ],
        },
        "style": style,
        "caption_system": {
            "style_id": "adaptive_capcut_kinetic_caption_stack",
            "style_options": [
                "player3_smooth_caption_compound",
                "capcut_adaptive_texture_caption",
                "two_word_pop_highlight_glow",
                "organic_low_focus_subtitles",
                "premiere_one_word_pop_fade",
            ],
            "chunk_words": 2,
            "max_duration_seconds": 1.45,
            "font_size": 64,
            "line_height": 1.08,
            "safe_region": "bottom 18-30 percent; never cover faces, proof, UI, charts, or key action",
            "layout_policy": "Use semantic phrase chunks, avoid dangling prepositions/articles, fit every caption/emphasis layer inside an 82 percent width safe box, and suppress or reposition captions when scene text already carries the same meaning.",
            "animation": {
                "in": "scale_88_to_108_to_100",
                "hold": "steady_read",
                "out": "opacity_fade_6_frames",
                "emphasis": "accent_fill_plus_short_glow_sweep",
            },
            "effect_selection_rule": "Choose caption style per beat; suppress ordinary captions when designed text carries the same phrase.",
            "source_cards": caption_cards,
            "source_presets": preset_groups.get("captions", []),
        },
        "motion_system": {
            "camera_moves": [
                "first_three_second_dynamic_zoom_hook",
                "slow_push_in",
                "parallax_pan_left",
                "focus_zoom_hold",
                "settle_zoom_out",
            ],
            "overlay_moves": [
                "callout_label_pop",
                "arrow_trace",
                "corner_pulse",
                "outline_trace",
                "mask_highlight_wipe",
                "final_zoom_settle",
                "capcut_staggered_blur_glitch_reveal",
                "capcut_axis_stretch_word",
                "capcut_font_shift_loop",
                "capcut_apple_slide_up_text",
                "capcut_perspective_freeze_text",
                "capcut_graph_zoom_stack",
            ],
            "transition_policy": "Choose motivated transitions from the option bank; do not force a transition if it would harm factual clarity.",
            "source_cards": motion_cards,
            "source_presets": preset_groups.get("motion", []),
        },
        "sound_system": {
            "cue_policy": "Frame-lock subtle SFX to visual reveals and caption emphasis; keep speech dominant.",
            "ducking": "All SFX/music stay under narration; no hit should mask a word.",
            "cue_families": [
                "soft_hit",
                "short_whoosh",
                "diagram_tick",
                "highlight_shimmer",
                "glitch_tick",
                "font_tick",
                "tiny_pop",
                "reverse_hit",
                "final_resolve",
            ],
            "effect_to_sfx_map": {
                option["effect_id"]: option.get("sound_cue", "")
                for option in RENDERABLE_EFFECT_OPTIONS
                if option.get("sound_cue")
            },
            "source_cards": sound_cards,
            "source_presets": preset_groups.get("sound", []),
        },
        "color_system": {
            "look": "clean educational contrast with subtle cool tint, accent highlights, and restrained vignette",
            "filters": {
                "contrast": 1.06,
                "saturation": 1.08,
                "brightness": 0.01,
                "vignette": "subtle",
            },
            "source_cards": color_cards,
            "source_presets": preset_groups.get("color", []),
        },
        "transition_system": {
            "default": "micro_black_drop_or_soft_wipe",
            "max_duration_seconds": 0.22,
            "source_presets": preset_groups.get("transitions", []),
        },
        "knowledge_coverage": {
            "domains_detected": plan.get("domains_detected", []),
            "inventory_counts": plan.get("inventory_counts", {}),
            "selected_counts": plan.get("selected_counts", {}),
            "selected_skills": selected_skills,
            "selected_qc_checklists": selected_qc,
            "technique_paths_by_category": technique_groups,
            "preset_paths_by_category": preset_groups,
        },
        "option_bank": option_bank,
        "qc_gates": [
            "Each beat has camera, caption, emphasis, overlay, color, and sound layer instructions.",
            "Captions use rich JSON style metadata, not only SRT.",
            "Every selected technique either appears in a layer/source list or is recorded as not applicable.",
            "Renderer applies caption/effect overlay after base visual composition.",
            "Phone-size readability and visual collisions are checked before final.",
        ],
    }


def write_markdown(path: Path, directive: dict[str, Any]) -> None:
    contract = directive["project_contract"]
    lines = [
        "# Creative Directive",
        "",
        f"- Created at: {directive['created_at']}",
        f"- Brief: {directive.get('brief', '')}",
        f"- Style pack: `{directive['style'].get('style_pack', '')}`",
        f"- No basic outputs: `{contract['no_basic_outputs']}`",
        f"- Minimum layers per beat: `{contract['minimum_layers_per_beat']}`",
        "",
        "## Required Layer Types",
        "",
    ]
    lines.extend(f"- `{item}`" for item in contract["required_layer_types"])
    lines.extend(["", "## Caption System", ""])
    lines.append(f"- Style: `{directive['caption_system']['style_id']}`")
    lines.append(f"- Chunk words: `{directive['caption_system']['chunk_words']}`")
    lines.append(f"- Animation: `{directive['caption_system']['animation']['in']}` with `{directive['caption_system']['animation']['emphasis']}`")
    lines.extend(["", "## Motion System", ""])
    lines.extend(f"- {item}" for item in directive["motion_system"]["camera_moves"])
    lines.extend(["", "## Selected Technique Coverage", ""])
    for category, paths in directive["knowledge_coverage"]["technique_paths_by_category"].items():
        if not paths:
            continue
        lines.append(f"### {category.title()}")
        lines.extend(f"- `{item}`" for item in paths)
        lines.append("")
    lines.extend(["## QC Gates", ""])
    lines.extend(f"- {item}" for item in directive["qc_gates"])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile knowledge_plan.json into renderable creative directives.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--knowledge-plan", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    plan_path = args.knowledge_plan or project_dir / "knowledge_plan.json"
    output = args.output or project_dir / "creative_directive.json"
    markdown_output = args.markdown_output or project_dir / "creative_directive.md"
    if not plan_path.exists():
        raise SystemExit(f"knowledge plan not found: {plan_path}")

    directive = build_directive(load_json(plan_path))
    output.write_text(json.dumps(directive, indent=2) + "\n", encoding="utf-8")
    write_markdown(markdown_output, directive)
    print(json.dumps({"output": str(output), "markdown": str(markdown_output)}, indent=2))


if __name__ == "__main__":
    main()
