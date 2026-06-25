"""Create a knowledge-driven sound design plan from a from-scratch timeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from asset_manifest import utc_now


def cue_family(beat: dict[str, Any], index: int) -> list[dict[str, Any]]:
    compiled = [layer for layer in beat.get("layers", []) if layer.get("type") == "sound_cue"]
    if compiled:
        result = []
        for layer in compiled:
            events = layer.get("events") or [
                {
                    "time": float(layer.get("start", beat.get("start", 0))),
                    "kind": layer.get("effect", "accent"),
                    "description": "compiled timeline sound cue; frame-lock to matching visual/caption reveal",
                }
            ]
            for event in events:
                result.append(
                    {
                        "time": float(event.get("time", layer.get("start", beat.get("start", 0)))),
                        "type": event.get("kind", layer.get("effect", "accent")),
                        "description": event.get("description", "compiled timeline sound cue"),
                        "level": event.get("level", layer.get("level", "low_under_voice")),
                        "source_techniques": layer.get("source_techniques", []),
                        "source_presets": layer.get("source_presets", []),
                    }
                )
        return result
    start = float(beat.get("start", 0))
    end = float(beat.get("end", start + 3))
    job = str(beat.get("visual_job", "")).lower()
    cues: list[dict[str, Any]] = []
    if index == 0:
        cues.append({"time": start, "type": "impact", "description": "small hook hit on first visual reveal", "level": "low"})
    elif any(word in job for word in ["transition", "turn", "reveal", "map", "chart", "zoom"]):
        cues.append({"time": start, "type": "whoosh", "description": "short transition accent, frame-aligned", "level": "very low"})
    if any(word in job for word in ["chart", "data", "number"]):
        cues.append({"time": max(start, end - 0.35), "type": "tick", "description": "quiet data lock-in tick", "level": "very low"})
    if any(word in job for word in ["document", "archive", "paper"]):
        cues.append({"time": start + 0.08, "type": "texture", "description": "subtle paper/document movement", "level": "low"})
    return cues


def build_plan(timeline: dict[str, Any]) -> dict[str, Any]:
    beats = timeline.get("beats", [])
    duration = max((float(b.get("end", 0)) for b in beats), default=0.0)
    sfx = []
    for idx, beat in enumerate(beats):
        for cue in cue_family(beat, idx):
            cue["beat_id"] = beat.get("beat_id", f"B{idx+1:02d}")
            sfx.append(cue)
    source_techniques = sorted({ref for cue in sfx for ref in cue.get("source_techniques", [])})
    source_presets = sorted({ref for cue in sfx for ref in cue.get("source_presets", [])})
    return {
        "created_at": utc_now(),
        "music": {
            "role": "support voiceover without masking speech",
            "start": 0,
            "end": duration,
            "ducking": "duck before every voiceover phrase; keep narration dominant",
            "license_status": "pending",
        },
        "sfx": sfx,
        "source_techniques": source_techniques,
        "source_presets": source_presets,
        "mix_rules": [
            "voiceover remains dominant at all times",
            "SFX peaks do not overpower narration",
            "music is temp-only until license/platform status is recorded",
            "silence beats are allowed when they improve comprehension or tension",
        ],
    }


def write_markdown(path: Path, plan: dict[str, Any]) -> None:
    lines = [
        "# Sound Design Plan",
        "",
        f"- Created at: {plan['created_at']}",
        f"- Music role: {plan['music']['role']}",
        f"- Ducking: {plan['music']['ducking']}",
        "",
        "## SFX Cues",
        "",
        "| Beat ID | Time | Type | Description | Level |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for cue in plan["sfx"]:
        lines.append(f"| {cue['beat_id']} | {cue['time']:.2f} | {cue['type']} | {cue['description']} | {cue['level']} |")
    lines.extend(["", "## Knowledge Sources", ""])
    for source in plan.get("source_techniques", []):
        lines.append(f"- `{source}`")
    for source in plan.get("source_presets", []):
        lines.append(f"- `{source}`")
    lines.extend(["", "## Mix Rules", ""])
    lines.extend(f"- {rule}" for rule in plan["mix_rules"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a sound_design_plan from edit_decision_list.json.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    timeline_path = args.timeline or project_dir / "edit_decision_list.json"
    output = args.output or project_dir / "sound_design_plan.md"
    json_output = args.json_output or project_dir / "sound_design_plan.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    plan = build_plan(timeline)
    write_markdown(output, plan)
    json_output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "json": str(json_output), "sfx": len(plan["sfx"])}, indent=2))


if __name__ == "__main__":
    main()
