"""Generate knowledge-driven captions from a beat-tagged script.

This helper still writes an SRT fallback, but the primary output is
`captions.json`: renderable kinetic caption cues with style IDs, emphasis terms,
animation metadata, safe-region rules, and source technique references from the
project creative directive.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from asset_manifest import utc_now


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


def srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def markdown_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_headers: list[str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not (line.startswith("|") and line.endswith("|")):
            current_headers = None
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        lowered = [c.lower() for c in cells]
        if any("beat" in c for c in lowered) and any("voiceover" in c or "script" in c for c in lowered):
            current_headers = lowered
            continue
        if current_headers:
            rows.append({current_headers[idx]: cells[idx] if idx < len(cells) else "" for idx in range(len(current_headers))})
    return rows


def parse_range(value: str, fallback_start: float, fallback_duration: float) -> tuple[float, float]:
    match = re.search(r"([0-9:.]+)\s*[-–]\s*([0-9:.]+)", value)
    if not match:
        return fallback_start, fallback_start + fallback_duration
    return parse_timecode(match.group(1)), parse_timecode(match.group(2))


def load_directive(project_dir: Path, path: Path | None = None) -> dict[str, Any]:
    directive_path = path or project_dir / "creative_directive.json"
    if not directive_path.exists():
        return {}
    return json.loads(directive_path.read_text(encoding="utf-8"))


def emphasis_terms(text: str) -> list[str]:
    lowered = text.lower()
    preferred = [
        "pressure shield",
        "stress magnets",
        "sharp corners",
        "hard corners",
        "pressure",
        "force",
        "round",
        "oval",
        "not style",
    ]
    terms = [term for term in preferred if term in lowered]
    if terms:
        return terms[:4]
    stop = {"the", "and", "are", "for", "that", "this", "with", "your", "into", "there"}
    words = [w.strip(".,:;!?()[]").lower() for w in text.split()]
    return [w for w in words if len(w) > 5 and w not in stop][:3]


SOFT_ENDERS = {
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
    "was",
    "were",
    "not",
    "so",
}


def clean_word(value: str) -> str:
    return re.sub(r"[^a-z0-9']+", "", value.lower())


def smart_chunks(words: list[str], target_size: int) -> list[list[str]]:
    """Build readable caption phrases instead of mechanical word pairs."""
    if not words:
        return []
    target_size = max(2, target_size)
    max_size = max(4, target_size + 2)
    chunks_out: list[list[str]] = []
    current: list[str] = []

    for word in words:
        current.append(word)
        clean = clean_word(word)
        sentence_end = bool(re.search(r"[.!?]$", word))
        should_close = len(current) >= target_size and clean not in SOFT_ENDERS
        must_close = len(current) >= max_size or sentence_end
        if should_close or must_close:
            chunks_out.append(current)
            current = []

    if current:
        if chunks_out and len(current) == 1 and clean_word(chunks_out[-1][-1]) in SOFT_ENDERS:
            chunks_out[-1].extend(current)
        else:
            chunks_out.append(current)

    balanced: list[list[str]] = []
    for chunk in chunks_out:
        if balanced and len(chunk) == 1:
            balanced[-1].extend(chunk)
        else:
            balanced.append(chunk)
    return balanced


def build_cues(rows: list[dict[str, str]], words_per_caption: int, max_duration: float, directive: dict[str, Any]) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    cursor = 0.0
    caption_system = directive.get("caption_system", {})
    style_id = caption_system.get("style_id", "two_word_pop_highlight_glow")
    animation = caption_system.get("animation", {})
    safe_region = caption_system.get("safe_region", "lower_safe")
    source_cards = [card.get("path") for card in caption_system.get("source_cards", []) if isinstance(card, dict) and card.get("path")]
    source_presets = caption_system.get("source_presets", [])
    for idx, row in enumerate(rows, start=1):
        beat_id = row.get("beat id") or row.get("beat") or f"B{idx:02d}"
        text = row.get("voiceover") or row.get("script") or row.get("line") or ""
        if not text:
            continue
        start, end = parse_range(row.get("time target", ""), cursor, 3.0)
        cursor = end
        word_chunks = smart_chunks(text.split(), words_per_caption)
        if not word_chunks:
            continue
        duration = max(0.5, end - start)
        cue_duration = min(max_duration, duration / len(word_chunks))
        total_cue_time = cue_duration * len(word_chunks)
        if total_cue_time > duration:
            cue_duration = duration / len(word_chunks)
        for chunk_idx, word_chunk in enumerate(word_chunks):
            cue_start = start + chunk_idx * cue_duration
            cue_end = min(end, cue_start + cue_duration)
            cue_text = " ".join(word_chunk)
            beat_terms = emphasis_terms(text)
            cues.append(
                {
                    "beat_id": beat_id,
                    "start": cue_start,
                    "end": cue_end,
                    "text": cue_text,
                    "style_id": style_id,
                    "chunk_words": len(word_chunk),
                    "safe_region": safe_region,
                    "animation": animation,
                    "emphasis_terms": [term for term in beat_terms if term in cue_text.lower()] or beat_terms[:1],
                    "render_layer": {
                        "type": "caption_kinetic",
                        "position": "lower_safe",
                        "entrance_frames": 5,
                        "exit_frames": 5,
                        "highlight_mode": "accent_fill_glow_sweep",
                    },
                    "source_techniques": source_cards,
                    "source_presets": source_presets,
                }
            )
    return cues


def write_srt(path: Path, cues: list[dict[str, Any]]) -> None:
    blocks = []
    for idx, cue in enumerate(cues, start=1):
        blocks.append(f"{idx}\n{srt_time(cue['start'])} --> {srt_time(cue['end'])}\n{cue['text']}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(blocks), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate draft SRT captions from script.md.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--script", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--creative-directive", type=Path)
    parser.add_argument("--words-per-caption", type=int, default=5)
    parser.add_argument("--max-duration", type=float, default=2.2)
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    script = args.script or project_dir / "script.md"
    output = args.output or project_dir / "captions" / "master.srt"
    json_output = args.json_output or project_dir / "captions" / "captions.json"
    if not script.exists():
        raise SystemExit(f"script not found: {script}")

    directive = load_directive(project_dir, args.creative_directive)
    caption_system = directive.get("caption_system", {})
    words_per_caption = int(caption_system.get("chunk_words", args.words_per_caption))
    max_duration = float(caption_system.get("max_duration_seconds", args.max_duration))
    rows = markdown_rows(script.read_text(encoding="utf-8"))
    cues = build_cues(rows, words_per_caption, max_duration, directive)
    write_srt(output, cues)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps({"created_at": utc_now(), "caption_system": caption_system, "cues": cues}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"srt": str(output), "json": str(json_output), "cues": len(cues)}, indent=2))


if __name__ == "__main__":
    main()
