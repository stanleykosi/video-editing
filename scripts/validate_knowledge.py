#!/usr/bin/env python3
"""Validate the canonical editorial knowledge hierarchy and its path contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
REQUIRED_DIRECTORIES = (
    "playbooks",
    "presets",
    "quality/editorial_checklists",
    "research/catalogs",
    "research/lessons",
    "styles",
    "techniques",
    "workflows/content_creation",
)
RETIRED_ROOTS = (
    "content_creation",
    "extracted_lessons",
    "presets",
    "qc_checklists",
    "skills",
    "sources",
    "style_packs",
    "technique_cards",
    "transcripts",
)
OPTIONAL_LOCAL_PREFIXES = (
    "knowledge/research/source_notes/",
    "knowledge/research/transcripts/",
)
PATH_PATTERN = re.compile(r"`(knowledge/[^`]+)`")


def strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for value_item in value for item in strings(value_item)]
    if isinstance(value, dict):
        return [item for value_item in value.values() for item in strings(value_item)]
    return []


def validate_path(value: str, failures: list[str]) -> None:
    if value.startswith(OPTIONAL_LOCAL_PREFIXES):
        return
    if any(character in value for character in "<>?"):
        return
    if "*" in value:
        if not list(ROOT.glob(value)):
            failures.append(f"knowledge glob has no matches: {value}")
        return
    if not (ROOT / value).exists():
        failures.append(f"missing knowledge path: {value}")


def main() -> int:
    failures: list[str] = []
    for relative in REQUIRED_DIRECTORIES:
        if not (KNOWLEDGE / relative).is_dir():
            failures.append(f"missing knowledge directory: knowledge/{relative}")
    for retired in RETIRED_ROOTS:
        if (ROOT / retired).exists():
            failures.append(f"retired top-level knowledge path returned: {retired}/")

    cards = sorted((KNOWLEDGE / "techniques").glob("*/*.json"))
    for card in cards:
        payload = json.loads(card.read_text(encoding="utf-8"))
        if payload.get("category") != card.parent.name:
            failures.append(f"technique category/path mismatch: {card.relative_to(ROOT)}")
        for value in strings(payload):
            if value.startswith("knowledge/"):
                validate_path(value, failures)

    markdown_roots = (ROOT / "AGENTS.md", ROOT / "README.md", KNOWLEDGE, ROOT / "docs")
    markdown_files: list[Path] = []
    for path in markdown_roots:
        markdown_files.extend(path.rglob("*.md") if path.is_dir() else [path])
    for markdown in markdown_files:
        text = markdown.read_text(encoding="utf-8")
        for value in PATH_PATTERN.findall(text):
            validate_path(value, failures)

    report = {
        "ok": not failures,
        "technique_cards": len(cards),
        "required_directories": len(REQUIRED_DIRECTORIES),
        "failures": sorted(set(failures)),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
