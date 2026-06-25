"""Create stock-footage search plans from a visual plan.

The helper converts beat-level visual ideas into searchable queries and source
priority notes. It does not download assets; use `find_assets.py` after this
plan is reviewed.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from asset_manifest import utc_now


STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "with", "for",
    "show", "visual", "shot", "clip", "image", "footage", "broll", "b-roll",
    "animation", "graphic", "text", "caption", "close", "wide", "medium",
}


def markdown_tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= {"-", ":", " "} for c in cells):
                continue
            current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def rows_from_tables(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for table in markdown_tables(text):
        headers = [h.lower() for h in table[0]]
        if not any("beat" in h for h in headers):
            continue
        for cells in table[1:]:
            row = {headers[idx]: cells[idx].strip() if idx < len(cells) else "" for idx in range(len(headers))}
            rows.append(row)
    return rows


def compact_query(*parts: str) -> str:
    words: list[str] = []
    for part in parts:
        for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]+", part.lower()):
            if word not in STOPWORDS and len(word) > 2:
                words.append(word)
    deduped: list[str] = []
    for word in words:
        if word not in deduped:
            deduped.append(word)
    return " ".join(deduped[:8])


def classify_media(visual: str, assets: str) -> str:
    haystack = f"{visual} {assets}".lower()
    if any(word in haystack for word in ["chart", "graph", "data"]):
        return "chart"
    if any(word in haystack for word in ["map", "route", "country", "city"]):
        return "map"
    if any(word in haystack for word in ["document", "screenshot", "article", "archive", "photo"]):
        return "image"
    if any(word in haystack for word in ["icon", "shape", "symbol"]):
        return "icon"
    if any(word in haystack for word in ["generated", "illustration", "concept"]):
        return "generated_image"
    return "video"


def source_priority(media_type: str) -> str:
    if media_type == "video":
        return "Pexels/Pixabay first; Wikimedia/NASA/LOC/Internet Archive for factual or archival needs."
    if media_type == "image":
        return "Openverse/Wikimedia/NASA/LOC/Met/Smithsonian depending on subject and rights."
    if media_type == "icon":
        return "Iconify/Lucide first; Noun Project/Iconfinder only with API/license tracking."
    if media_type == "map":
        return "Render with render_map.py from Natural Earth/OSM-derived data with attribution."
    if media_type == "chart":
        return "Render with render_chart.py from cited CSV/API data."
    return "Generate/register with generate_asset.py; do not present as factual evidence."


def plan_from_visual_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        beat = row.get("beat id") or row.get("beat") or f"B{idx:02d}"
        voice = row.get("voiceover range") or row.get("voiceover") or row.get("line") or ""
        primary = row.get("primary visual") or row.get("visual") or row.get("visual purpose") or ""
        assets = row.get("assets") or ""
        media_type = classify_media(primary, assets)
        query = compact_query(primary, voice, assets)
        plan.append(
            {
                "beat_id": beat,
                "media_type": media_type,
                "query": query or compact_query(primary) or beat,
                "visual_need": primary,
                "source_priority": source_priority(media_type),
                "rights_status": "pending",
                "fallback": "generated placeholder or simple motion card if rights-safe footage is unavailable",
            }
        )
    return plan


def write_markdown(path: Path, plan: list[dict[str, Any]]) -> None:
    lines = [
        "# Stock Footage Plan",
        "",
        f"- Created at: {utc_now()}",
        "- Use this before `find_assets.py`; do not use watermarked previews in final.",
        "",
        "| Beat ID | Media Type | Query | Source Priority | Rights Status | Fallback |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in plan:
        lines.append(
            f"| {item['beat_id']} | {item['media_type']} | {item['query']} | "
            f"{item['source_priority']} | {item['rights_status']} | {item['fallback']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a stock-footage search plan from visual_plan.md.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--visual-plan", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    visual_plan = args.visual_plan or project_dir / "visual_plan.md"
    output = args.output or project_dir / "stock_footage_plan.md"
    json_output = args.json_output or project_dir / "stock_footage_queries.json"
    if not visual_plan.exists():
        raise SystemExit(f"visual plan not found: {visual_plan}")

    rows = rows_from_tables(visual_plan.read_text(encoding="utf-8"))
    plan = plan_from_visual_rows(rows)
    write_markdown(output, plan)
    json_output.write_text(json.dumps({"created_at": utc_now(), "items": plan}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "json": str(json_output), "items": len(plan)}, indent=2))


if __name__ == "__main__":
    main()
