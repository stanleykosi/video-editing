"""Build a knowledge-driven from-scratch `edit_decision_list.json`.

The output timeline is not allowed to be a thin list of clips. It compiles the
project creative directive into renderable layer instructions: camera motion,
kinetic captions, emphasis text, visual overlays, color, sound, transitions,
and QC gates for every beat.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from asset_manifest import load_manifest, utc_now


def parse_timecode(value: str) -> float:
    value = value.strip()
    if not value:
        return 0.0
    parts = value.split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def parse_range(value: str, fallback_start: float, fallback_duration: float = 3.0) -> tuple[float, float]:
    match = re.search(r"([0-9:.]+)\s*[-–]\s*([0-9:.]+)", value)
    if not match:
        return fallback_start, fallback_start + fallback_duration
    return parse_timecode(match.group(1)), parse_timecode(match.group(2))


def markdown_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not (line.startswith("|") and line.endswith("|")):
            headers = None
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        lowered = [c.lower() for c in cells]
        if any("beat" in c for c in lowered):
            headers = lowered
            continue
        if headers:
            rows.append({headers[idx]: cells[idx] if idx < len(cells) else "" for idx in range(len(headers))})
    return rows


def load_style_pack(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_directive(project_dir: Path, path: Path | None = None) -> dict[str, Any]:
    directive_path = path or project_dir / "creative_directive.json"
    if not directive_path.exists():
        return {}
    return json.loads(directive_path.read_text(encoding="utf-8"))


def assets_by_id(project_dir: Path) -> dict[str, dict[str, Any]]:
    manifest = load_manifest(project_dir)
    result: dict[str, dict[str, Any]] = {}
    for asset in manifest.get("assets", []):
        for key in ("manifest_id", "asset_id"):
            value = asset.get(key)
            if value:
                result[str(value)] = asset
    return result


def clean_markdown_path(value: str) -> str:
    return value.strip().strip("`").strip()


def markdown_table_rows_any(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not (line.startswith("|") and line.endswith("|")):
            headers = None
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        if headers is None:
            headers = [c.lower() for c in cells]
            continue
        rows.append({headers[idx]: cells[idx] if idx < len(cells) else "" for idx in range(len(headers))})
    return rows


def asset_aliases(project_dir: Path) -> dict[str, str]:
    path = project_dir / "asset_list.md"
    if not path.exists():
        return {}
    rows = markdown_table_rows_any(path.read_text(encoding="utf-8"))
    aliases: dict[str, str] = {}
    for row in rows:
        asset_id = row.get("asset id") or row.get("id")
        local_path = row.get("local path") or row.get("path")
        if not asset_id or not local_path:
            continue
        cleaned = clean_markdown_path(local_path)
        if cleaned and cleaned.lower() not in {"pending", "n/a", "none"}:
            aliases[asset_id.strip()] = cleaned
    return aliases


def first_asset_id(value: str) -> str:
    match = re.search(r"\b[A-Z]\d{2,}\b|\basset_[a-f0-9]{8,}\b|[\w.-]+\.(?:mp4|mov|png|jpg|jpeg|webm|mp3|wav)", value)
    return match.group(0) if match else ""


def emphasis_terms(text: str, purpose: str = "", visual: dict[str, str] | None = None) -> list[str]:
    visual = visual or {}
    quoted = re.findall(r'"([^"]+)"|`([^`]+)`', " ".join([text, purpose, *visual.values()]))
    terms = [next(part for part in group if part).strip() for group in quoted if any(group)]
    candidates = [
        "pressure",
        "stress magnets",
        "sharp corners",
        "spreads",
        "force",
        "avoid hard corners",
        "pressure shield",
        "not style",
        "payoff",
        "hook",
    ]
    lowered = text.lower()
    for candidate in candidates:
        if candidate in lowered and candidate not in [term.lower() for term in terms]:
            terms.append(candidate)
    if not terms:
        words = [w.strip(".,:;!?()[]").lower() for w in text.split()]
        stop = {"the", "and", "are", "for", "one", "that", "this", "with", "your", "from", "into", "there", "every"}
        terms = [w for w in words if len(w) > 5 and w not in stop][:2]
    return terms[:4]


def pick(values: list[str], idx: int, fallback: str) -> str:
    if not values:
        return fallback
    return values[idx % len(values)]


def technique_refs(directive: dict[str, Any], category: str, limit: int = 3) -> list[str]:
    coverage = directive.get("knowledge_coverage", {})
    grouped = coverage.get("technique_paths_by_category", {})
    values = grouped.get(category, []) if isinstance(grouped, dict) else []
    return list(values[:limit])


def preset_refs(directive: dict[str, Any], category: str, limit: int = 2) -> list[str]:
    coverage = directive.get("knowledge_coverage", {})
    grouped = coverage.get("preset_paths_by_category", {})
    values = grouped.get(category, []) if isinstance(grouped, dict) else []
    return list(values[:limit])


def visual_overlay_kind(visual_text: str, beat_id: str) -> str:
    lowered = visual_text.lower()
    if any(word in lowered for word in ("stress", "corner", "crack", "square")):
        return "corner_pulse"
    if any(word in lowered for word in ("force", "arrow", "distribution", "pressure")):
        return "arrow_trace"
    if any(word in lowered for word in ("modern", "window", "rounded", "outline")):
        return "outline_trace"
    if beat_id.endswith("01"):
        return "hook_label_pop"
    if any(word in lowered for word in ("final", "payoff", "takeaway")):
        return "final_zoom_settle"
    return "callout_label_pop"


def text_heavy_scene(visual: dict[str, str]) -> bool:
    context = " ".join(
        visual.get(key, "")
        for key in ("primary visual", "secondary overlays", "motion treatment", "text/captions")
    ).lower()
    text_heavy_phrases = (
        "final graphic card",
        "end card",
        "title card",
        "big final phrase",
        "quote card",
        "text card",
        "chapter card",
        "full-screen text",
    )
    return any(phrase in context for phrase in text_heavy_phrases)


def renderable_option(directive: dict[str, Any], effect_id: str) -> dict[str, Any]:
    for option in directive.get("option_bank", {}).get("renderable_effect_options", []):
        if option.get("effect_id") == effect_id:
            return option
    return {"effect_id": effect_id, "source_paths": []}


def option_sources(directive: dict[str, Any], effect_id: str) -> list[str]:
    option = renderable_option(directive, effect_id)
    return [path for path in option.get("source_paths", []) if path.endswith(".json")]


def choose_typography_effect(
    beat_id: str,
    idx: int,
    script_text: str,
    visual: dict[str, str],
    suppress_duplicate_emphasis: bool,
) -> str:
    context = " ".join([beat_id, script_text, *visual.values()]).lower()
    if suppress_duplicate_emphasis:
        return "suppressed_scene_text"
    if idx == 0 or "hook" in context:
        return "capcut_staggered_blur_glitch_reveal"
    if any(word in context for word in ("stress", "crack", "sharp", "corner")):
        return "capcut_axis_stretch_word"
    if any(word in context for word in ("pressure", "force", "spreads", "highlight")):
        return "capcut_highlight_wipe"
    if any(word in context for word in ("not style", "style", "myth", "truth")):
        return "capcut_font_shift_loop"
    if any(word in context for word in ("takeaway", "final", "payoff")):
        return "capcut_apple_slide_up_text"
    return "capcut_highlight_wipe"


def choose_caption_effect(visual: dict[str, str], suppress_duplicate_emphasis: bool) -> str:
    context = " ".join(visual.values()).lower()
    if suppress_duplicate_emphasis:
        return "caption_suppressed_or_low_focus"
    if any(word in context for word in ("stock", "footage", "cabin", "window", "flight")):
        return "player3_smooth_caption_compound"
    return "capcut_adaptive_texture_caption"


def choose_camera_effect(idx: int, script_text: str, visual: dict[str, str], motion_system: dict[str, Any]) -> str:
    context = " ".join([script_text, *visual.values()]).lower()
    if idx == 0 or "hook" in context:
        return "capcut_graph_zoom_stack"
    if any(word in context for word in ("proof", "detail", "focus", "stress", "corner")):
        return "focus_zoom_hold"
    return pick(motion_system.get("camera_moves", []), idx, "slow_push_in")


def sound_events(
    start: float,
    end: float,
    typography_effect: str,
    overlay_kind: str,
    idx: int,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if idx:
        events.append({"time": start, "kind": "short_whoosh", "description": "beat transition starts"})
    if typography_effect == "capcut_staggered_blur_glitch_reveal":
        events.append({"time": start + 0.08, "kind": "glitch_tick", "description": "first word stagger/glitch reveal"})
        events.append({"time": start + 0.28, "kind": "font_tick", "description": "final word reveal resolves"})
    elif typography_effect == "capcut_axis_stretch_word":
        events.append({"time": start + 0.18, "kind": "tiny_pop", "description": "axis stretch reaches peak"})
    elif typography_effect == "capcut_highlight_wipe":
        events.append({"time": start + 0.2, "kind": "highlight_shimmer", "description": "highlight wipe enters keyword"})
    elif typography_effect == "capcut_font_shift_loop":
        events.append({"time": start + 0.12, "kind": "font_tick", "description": "font shift loop starts"})
    if overlay_kind in {"corner_pulse", "arrow_trace", "outline_trace"}:
        events.append({"time": min(end - 0.2, start + 0.55), "kind": "diagram_tick", "description": f"{overlay_kind} locks to diagram"})
    return events


def build_layers(
    beat_id: str,
    idx: int,
    start: float,
    end: float,
    script_text: str,
    visual: dict[str, str],
    directive: dict[str, Any],
) -> list[dict[str, Any]]:
    duration = max(0.2, end - start)
    caption_system = directive.get("caption_system", {})
    motion_system = directive.get("motion_system", {})
    sound_system = directive.get("sound_system", {})
    color_system = directive.get("color_system", {})
    transition_system = directive.get("transition_system", {})
    style = directive.get("style", {})
    terms = emphasis_terms(script_text, visual.get("text/captions", ""), visual)
    camera_move = choose_camera_effect(idx, script_text, visual, motion_system)
    overlay_kind = visual_overlay_kind(visual.get("secondary overlays", "") + " " + visual.get("motion treatment", "") + " " + visual.get("primary visual", ""), beat_id)
    suppress_duplicate_emphasis = text_heavy_scene(visual)
    typography_effect = choose_typography_effect(beat_id, idx, script_text, visual, suppress_duplicate_emphasis)
    caption_effect = choose_caption_effect(visual, suppress_duplicate_emphasis)
    accent = style.get("accent_color", "#38bdf8")
    secondary = style.get("secondary_accent", "#facc15")
    typography_sources = option_sources(directive, typography_effect)
    caption_sources = option_sources(directive, caption_effect)
    camera_sources = option_sources(directive, camera_move)
    sfx_events = sound_events(start, end, typography_effect, overlay_kind, idx)

    layers: list[dict[str, Any]] = [
        {
            "type": "camera_motion",
            "effect": camera_move,
            "start": start,
            "end": end,
            "keyframes": [
                {"time": start, "scale": 1.0, "x": 0, "y": 0},
                {"time": end, "scale": 1.055 if idx == 0 else 1.035, "x": (-10 if idx % 2 else 10), "y": -8},
            ],
            "source_techniques": technique_refs(directive, "motion") + camera_sources,
        },
        {
            "type": "caption_kinetic",
            "style_id": caption_system.get("style_id", "two_word_pop_highlight_glow"),
            "effect": caption_effect,
            "start": start,
            "end": end,
            "chunk_words": int(caption_system.get("chunk_words", 2)),
            "max_duration_seconds": float(caption_system.get("max_duration_seconds", 1.45)),
            "safe_region": caption_system.get("safe_region", "lower_safe"),
            "animation": caption_system.get("animation", {}),
            "emphasis_terms": terms,
            "source_techniques": technique_refs(directive, "captions") + caption_sources,
            "source_presets": preset_refs(directive, "captions"),
        },
        {
            "type": "emphasis_text",
            "effect": typography_effect,
            "text": terms[0].upper() if terms else "",
            "start": start + min(0.35, duration * 0.15),
            "end": min(end, start + max(1.15, duration * 0.55)),
            "position": "upper_or_center_safe",
            "accent_color": secondary if idx % 2 else accent,
            "suppressed": suppress_duplicate_emphasis,
            "suppression_reason": "scene text already carries the emphasis phrase" if suppress_duplicate_emphasis else "",
            "source_techniques": technique_refs(directive, "captions") + technique_refs(directive, "motion", 1) + typography_sources,
        },
        {
            "type": "visual_motion_overlay",
            "effect": overlay_kind,
            "label": terms[0] if terms else visual.get("primary visual", ""),
            "start": start + 0.1,
            "end": end - 0.1,
            "accent_color": accent,
            "source_techniques": technique_refs(directive, "motion"),
        },
        {
            "type": "color_grade",
            "effect": color_system.get("look", "clean educational contrast"),
            "start": start,
            "end": end,
            "filters": color_system.get("filters", {}),
            "source_techniques": technique_refs(directive, "color"),
            "source_presets": preset_refs(directive, "color"),
        },
        {
            "type": "sound_cue",
            "effect": pick(sound_system.get("cue_families", []), idx, "short_whoosh"),
            "start": start + (0.05 if idx else 0.0),
            "end": min(end, start + 0.45),
            "level": "low_under_voice",
            "events": sfx_events,
            "source_techniques": technique_refs(directive, "sound"),
            "source_presets": preset_refs(directive, "sound"),
        },
        {
            "type": "transition",
            "effect": transition_system.get("default", "micro_black_drop_or_soft_wipe"),
            "start": start,
            "end": min(end, start + float(transition_system.get("max_duration_seconds", 0.22))),
            "skip_if_first_beat": idx == 0,
            "source_presets": preset_refs(directive, "transitions"),
        },
    ]
    return layers


def build_timeline(
    project_dir: Path,
    script_rows: list[dict[str, str]],
    visual_rows: list[dict[str, str]],
    style: dict[str, Any],
    directive: dict[str, Any] | None = None,
) -> dict[str, Any]:
    directive = directive or {}
    visual_by_beat = {
        (row.get("beat id") or row.get("beat") or f"B{idx:02d}"): row
        for idx, row in enumerate(visual_rows, start=1)
    }
    asset_lookup = assets_by_id(project_dir)
    alias_lookup = asset_aliases(project_dir)
    default_platform = style.get("default_platform", {})
    width, height = 1080, 1920
    if isinstance(default_platform.get("resolution"), str) and "x" in default_platform["resolution"]:
        width_s, height_s = default_platform["resolution"].split("x", 1)
        width, height = int(width_s), int(height_s)

    beats: list[dict[str, Any]] = []
    cursor = 0.0
    for idx, row in enumerate(script_rows, start=1):
        beat_id = row.get("beat id") or row.get("beat") or f"B{idx:02d}"
        start, end = parse_range(row.get("time target", ""), cursor, 3.0)
        cursor = end
        visual = visual_by_beat.get(beat_id, {})
        asset_hint = first_asset_id(visual.get("assets", "") or row.get("source/claim notes", ""))
        asset = asset_lookup.get(asset_hint, {})
        local_path = asset.get("local_path") if asset else alias_lookup.get(asset_hint, "")
        if not local_path and "." in asset_hint:
            local_path = asset_hint
        script_text = row.get("voiceover") or row.get("script") or row.get("line") or ""
        layers = build_layers(beat_id, idx - 1, start, end, script_text, visual, directive)
        techniques_applied = sorted(
            {
                ref
                for layer in layers
                for ref in (layer.get("source_techniques", []) or [])
                if ref
            }
        )
        beats.append(
            {
                "beat_id": beat_id,
                "start": start,
                "end": end,
                "script_text": script_text,
                "purpose": row.get("purpose", ""),
                "visual_job": visual.get("primary visual") or visual.get("visual") or row.get("purpose", ""),
                "primary_asset_id": asset_hint,
                "primary_asset_path": local_path,
                "layers": layers,
                "techniques_applied": techniques_applied,
                "caption": {
                    "text": script_text,
                    "style": directive.get("caption_system", {}).get("style_id", visual.get("text/captions", "")),
                    "safe_region": directive.get("caption_system", {}).get("safe_region", "center-lower, avoid faces/proof/UI"),
                    "emphasis_terms": emphasis_terms(script_text, row.get("purpose", ""), visual),
                },
                "sound": {
                    "music_cue": visual.get("sound", ""),
                    "sfx": [layer for layer in layers if layer.get("type") == "sound_cue"],
                },
                "qc": ([visual.get("qc risk", "")] if visual.get("qc risk") else []) + directive.get("qc_gates", [])[:3],
            }
        )

    return {
        "schema_version": 1,
        "created_at": utc_now(),
        "project": {
            "title": project_dir.name,
            "mode": "create_from_scratch",
            "style_pack": style.get("id", ""),
            "creative_directive": "creative_directive.json" if directive else "",
            "knowledge_contract": directive.get("project_contract", {}),
            "resolution": {"width": width, "height": height},
            "fps": int(default_platform.get("fps", 30)),
            "target_duration_seconds": float(cursor),
            "audio_sample_rate": 48000,
        },
        "tracks": {
            "voiceover": [{"asset_id": "voiceover", "path": "assets/audio/voiceover.mp3"}],
            "music": [],
            "sfx": [],
            "background_video": [],
            "broll": [],
            "images": [],
            "motion_graphics": [{"source": "compiled_layers", "directive": "creative_directive.json"}] if directive else [],
            "captions": [{"path": "captions/master.srt"}],
            "overlays": [{"path": "captions/captions.json", "rendered_last": True}],
        },
        "beats": beats,
        "render": {
            "preview_path": "preview.mp4",
            "final_path": "final.mp4",
            "subtitles_last": True,
            "asset_manifest": "asset_manifest.json",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build edit_decision_list.json for a from-scratch video.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--script", type=Path)
    parser.add_argument("--visual-plan", type=Path)
    parser.add_argument("--style-pack", type=Path)
    parser.add_argument("--creative-directive", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    script = args.script or project_dir / "script.md"
    visual_plan = args.visual_plan or project_dir / "visual_plan.md"
    output = args.output or project_dir / "edit_decision_list.json"
    if not script.exists():
        raise SystemExit(f"script not found: {script}")
    if not visual_plan.exists():
        raise SystemExit(f"visual plan not found: {visual_plan}")

    style = load_style_pack(args.style_pack)
    directive = load_directive(project_dir, args.creative_directive)
    timeline = build_timeline(
        project_dir,
        markdown_rows(script.read_text(encoding="utf-8")),
        markdown_rows(visual_plan.read_text(encoding="utf-8")),
        style,
        directive,
    )
    output.write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "beats": len(timeline["beats"])}, indent=2))


if __name__ == "__main__":
    main()
