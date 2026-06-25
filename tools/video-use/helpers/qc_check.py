"""Run project-level QC for from-scratch faceless videos.

QC is intentionally strict: a from-scratch video is not complete if it only has
clips plus plain subtitles. It must include a compiled creative directive,
renderable timeline layers, rich caption metadata, asset provenance, and valid
preview/final media.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from asset_manifest import check_manifest, utc_now


REQUIRED = [
    "knowledge_plan.json",
    "creative_directive.json",
    "script.md",
    "visual_plan.md",
    "asset_list.md",
    "edit_decision_list.json",
    "preview.mp4",
    "qc_report.md",
    "final.mp4",
]

REQUIRED_LAYER_TYPES = {
    "camera_motion",
    "caption_kinetic",
    "emphasis_text",
    "visual_motion_overlay",
    "color_grade",
    "sound_cue",
}

STOCK_MONTAGE_LAYER_TYPES = {
    "stock_asset_selection",
    "static_crop_composition",
    "caption_kinetic",
    "transition",
    "color_grade",
    "sound_cue",
    "qc_rule",
}

CAPTION_SOFT_ENDERS = {
    "a",
    "an",
    "the",
    "to",
    "for",
    "of",
    "with",
    "beside",
    "through",
    "around",
    "into",
    "your",
    "my",
    "our",
    "their",
    "his",
    "her",
    "is",
    "are",
    "not",
    "so",
}


def ffprobe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
            "-of", "json", str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr.strip()}
    data = json.loads(result.stdout or "{}")
    data["ok"] = True
    return data


def timeline_duration(project_dir: Path) -> float:
    path = project_dir / "edit_decision_list.json"
    if not path.exists():
        return 0.0
    try:
        timeline = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0.0
    beats = timeline.get("beats", [])
    return max((float(beat.get("end", 0)) for beat in beats), default=0.0)


def check_timeline(project_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    path = project_dir / "edit_decision_list.json"
    if not path.exists():
        return ["missing edit_decision_list.json"], warnings
    try:
        timeline = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"edit_decision_list.json is invalid JSON: {exc}"], warnings
    beats = timeline.get("beats", [])
    project = timeline.get("project", {})
    contract = project.get("knowledge_contract", {})
    stock_montage = bool(project.get("stock_montage_only") or project.get("render_profile") == "premium_stock_montage")
    if not project.get("creative_directive"):
        errors.append("timeline is not linked to creative_directive.json")
    if not contract.get("no_basic_outputs"):
        errors.append("timeline missing strict no_basic_outputs knowledge contract")
    if not beats:
        errors.append("timeline has no beats")
    for beat in beats:
        label = beat.get("beat_id", "unknown beat")
        if beat.get("end", 0) <= beat.get("start", 0):
            errors.append(f"{label}: end must be greater than start")
        if not beat.get("script_text"):
            warnings.append(f"{label}: missing script_text")
        if not beat.get("visual_job"):
            warnings.append(f"{label}: missing visual_job")
        if not beat.get("primary_asset_id") and not beat.get("primary_asset_path"):
            warnings.append(f"{label}: no primary asset assigned")
        layers = beat.get("layers", [])
        layer_types = {layer.get("type") for layer in layers if isinstance(layer, dict)}
        default_layer_types = STOCK_MONTAGE_LAYER_TYPES if stock_montage else REQUIRED_LAYER_TYPES
        required_layer_types = set(contract.get("required_layer_types") or default_layer_types)
        minimum_layers = int(contract.get("minimum_layers_per_beat") or (5 if stock_montage else 6))
        missing_layer_types = required_layer_types - layer_types
        role_groups = contract.get("required_role_groups", {}) if isinstance(contract, dict) else {}
        missing_roles = []
        for role, options in role_groups.items():
            option_set = set(options or [])
            if option_set and not (option_set & layer_types):
                missing_roles.append(role)
        if len(layers) < minimum_layers:
            errors.append(f"{label}: too few compiled layers ({len(layers)} found, minimum {minimum_layers})")
        if missing_roles:
            errors.append(f"{label}: missing required creative roles: {', '.join(sorted(missing_roles))}")
        elif missing_layer_types:
            warnings.append(f"{label}: substituted exact layer types: {', '.join(sorted(missing_layer_types))}")
        if missing_layer_types and not role_groups:
            errors.append(f"{label}: missing required layer types: {', '.join(sorted(missing_layer_types))}")
        if not beat.get("techniques_applied"):
            errors.append(f"{label}: no technique_cards compiled into beat")
        for layer in layers:
            if not isinstance(layer, dict):
                continue
            if layer.get("type") == "emphasis_text":
                if layer.get("suppressed"):
                    if not layer.get("suppression_reason"):
                        warnings.append(f"{label}: suppressed emphasis_text is missing suppression_reason")
                    continue
                text = str(layer.get("text", "")).strip()
                if not text:
                    warnings.append(f"{label}: emphasis_text layer has no text")
                if len(text) > 24:
                    warnings.append(f"{label}: emphasis_text may be too long for vertical safe layout")
    return errors, warnings


def check_creative_directive(project_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    path = project_dir / "creative_directive.json"
    if not path.exists():
        return ["missing creative_directive.json"], warnings
    try:
        directive = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"creative_directive.json is invalid JSON: {exc}"], warnings
    contract = directive.get("project_contract", {})
    if not contract.get("no_basic_outputs"):
        errors.append("creative directive does not enforce no_basic_outputs")
    for key in ("caption_system", "motion_system", "sound_system", "color_system", "transition_system"):
        if not directive.get(key):
            errors.append(f"creative directive missing {key}")
    caption_system = directive.get("caption_system", {})
    if not caption_system.get("layout_policy"):
        errors.append("creative directive caption_system missing layout_policy")
    coverage = directive.get("knowledge_coverage", {})
    technique_groups = coverage.get("technique_paths_by_category", {})
    for category in ("captions", "motion", "sound", "color"):
        if not technique_groups.get(category):
            errors.append(f"creative directive has no selected {category} technique cards")
    option_bank = directive.get("option_bank", {})
    if not option_bank.get("renderable_effect_options"):
        errors.append("creative directive missing renderable effect option bank")
    if not option_bank.get("selection_policy"):
        errors.append("creative directive missing flexible selection policy")
    return errors, warnings


def check_rich_captions(project_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    path = project_dir / "captions" / "captions.json"
    if not path.exists():
        return ["missing captions/captions.json"], warnings
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"captions/captions.json is invalid JSON: {exc}"], warnings
    cues = data.get("cues", [])
    if not cues:
        errors.append("captions/captions.json has no cues")
    for idx, cue in enumerate(cues, start=1):
        if not cue.get("style_id"):
            errors.append(f"caption cue {idx}: missing style_id")
        if not cue.get("animation"):
            errors.append(f"caption cue {idx}: missing animation metadata")
        if not cue.get("render_layer"):
            errors.append(f"caption cue {idx}: missing render_layer")
        if not cue.get("source_techniques"):
            warnings.append(f"caption cue {idx}: no source technique references")
        words = str(cue.get("text", "")).split()
        clean_last = words[-1].strip(".,:;!?()[]").lower() if words else ""
        if len(words) <= 2 and clean_last in CAPTION_SOFT_ENDERS:
            warnings.append(f"caption cue {idx}: phrase ends on a weak/dangling word")
        if len(str(cue.get("text", ""))) > 34:
            warnings.append(f"caption cue {idx}: caption text may exceed vertical safe width")
    return errors, warnings


def write_report(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# QC Report",
        "",
        f"- Checked at: {data['checked_at']}",
        f"- Project: `{data['project_dir']}`",
        "",
        "## Required Artifacts",
        "",
    ]
    for item, exists in data["required"].items():
        lines.append(f"- {'PASS' if exists else 'FAIL'} `{item}`")
    lines.extend(["", "## Errors", ""])
    lines.extend(f"- {item}" for item in data["errors"] or ["None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in data["warnings"] or ["None"])
    lines.extend(["", "## Media Probe", ""])
    for name, probe in data["media"].items():
        if probe.get("ok"):
            duration = probe.get("format", {}).get("duration", "unknown")
            streams = probe.get("streams", [])
            dims = next((f"{s.get('width')}x{s.get('height')}" for s in streams if s.get("codec_type") == "video"), "unknown")
            lines.append(f"- `{name}`: ok, duration {duration}, video {dims}")
        else:
            lines.append(f"- `{name}`: failed, {probe.get('error')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run from-scratch video QC checks.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--allow-missing-final", action="store_true")
    parser.add_argument("--fail-on-errors", action="store_true")
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    output = args.output or project_dir / "qc_report.md"
    json_output = args.json_output or project_dir / "qc_report.json"
    required_names = REQUIRED if not args.allow_missing_final else [x for x in REQUIRED if x != "final.mp4"]
    required = {name: (project_dir / name).exists() for name in required_names}
    errors = [f"missing required artifact: {name}" for name, exists in required.items() if not exists and name != "qc_report.md"]
    warnings: list[str] = []

    timeline_errors, timeline_warnings = check_timeline(project_dir)
    errors.extend(timeline_errors)
    warnings.extend(timeline_warnings)

    directive_errors, directive_warnings = check_creative_directive(project_dir)
    errors.extend(directive_errors)
    warnings.extend(directive_warnings)

    caption_errors, caption_warnings = check_rich_captions(project_dir)
    errors.extend(caption_errors)
    warnings.extend(caption_warnings)

    manifest_errors, manifest_warnings = check_manifest(project_dir)
    errors.extend(f"asset manifest: {item}" for item in manifest_errors)
    warnings.extend(f"asset manifest: {item}" for item in manifest_warnings)

    media = {}
    expected_duration = timeline_duration(project_dir)
    for name in ("preview.mp4", "final.mp4"):
        path = project_dir / name
        if path.exists():
            probe = ffprobe(path)
            media[name] = probe
            if not probe.get("ok"):
                errors.append(f"{name}: media probe failed: {probe.get('error', 'unknown error')}")
            elif expected_duration:
                actual = float(probe.get("format", {}).get("duration") or 0)
                if abs(actual - expected_duration) > 0.5:
                    errors.append(f"{name}: duration {actual:.2f}s does not match timeline {expected_duration:.2f}s")

    data = {
        "checked_at": utc_now(),
        "project_dir": str(project_dir),
        "required": required,
        "errors": errors,
        "warnings": warnings,
        "media": media,
    }
    write_report(output, data)
    json_output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "json": str(json_output), "errors": errors, "warnings": warnings}, indent=2))
    if args.fail_on_errors and errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
