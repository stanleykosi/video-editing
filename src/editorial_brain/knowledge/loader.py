"""Safe deterministic loader for the repository's editorial knowledge layers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from editorial_brain.core.hashing import file_sha256, fingerprint
from editorial_brain.knowledge.models import KnowledgeCatalog, KnowledgeItem, KnowledgeKind

MAX_KNOWLEDGE_BYTES = 1_000_000
TOKEN = re.compile(r"[a-z0-9][a-z0-9_-]+")
LAYERS = {
    "playbooks": KnowledgeKind.PLAYBOOK,
    "research/lessons": KnowledgeKind.LESSON,
    "techniques": KnowledgeKind.TECHNIQUE,
    "presets": KnowledgeKind.PRESET,
    "styles": KnowledgeKind.STYLE,
    "quality/editorial_checklists": KnowledgeKind.QC_CHECKLIST,
}


def load_catalog(knowledge_root: Path) -> KnowledgeCatalog:
    root = knowledge_root.resolve()
    items: list[KnowledgeItem] = []
    rejected: list[str] = []
    if not root.is_dir():
        return KnowledgeCatalog(knowledge_root=str(root), fingerprint=fingerprint([]), items=[])
    for relative_layer, kind in LAYERS.items():
        layer = root / relative_layer
        if not layer.is_dir():
            continue
        for path in sorted(item for item in layer.rglob("*") if item.is_file()):
            relative = path.relative_to(root.parent).as_posix()
            if (
                path.suffix.lower() not in {".json", ".md"}
                or path.stat().st_size > MAX_KNOWLEDGE_BYTES
            ):
                rejected.append(relative)
                continue
            try:
                items.append(_load_item(root, path, kind))
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                rejected.append(relative)
    catalog_fingerprint = fingerprint([(item.relative_path, item.sha256) for item in items])
    return KnowledgeCatalog(
        knowledge_root=str(root),
        fingerprint=catalog_fingerprint,
        items=items,
        rejected_files=rejected,
    )


def _load_item(root: Path, path: Path, kind: KnowledgeKind) -> KnowledgeItem:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("knowledge file escapes the knowledge root")
    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(root.parent).as_posix()
    category = _category(root, path, kind)
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("knowledge JSON root must be an object")
        item_id = str(payload.get("id") or path.stem)
        title = str(payload.get("name") or payload.get("title") or _humanize(path.stem))
        use_when = _string_list(payload.get("use_when"))
        avoid_when = _string_list(payload.get("avoid_when"))
        rules = _rules_from_json(payload)
    else:
        item_id = path.stem
        title = _markdown_title(text, _humanize(path.stem))
        use_when, avoid_when, rules = _rules_from_markdown(text)
    searchable = " ".join([item_id, title, category, *use_when, *avoid_when, *rules])
    terms = sorted(set(TOKEN.findall(searchable.lower())))
    return KnowledgeItem(
        id=f"{kind.value}:{category}:{item_id}",
        kind=kind,
        category=category,
        title=title,
        relative_path=relative,
        sha256=file_sha256(path),
        search_terms=terms,
        use_when=use_when[:80],
        avoid_when=avoid_when[:80],
        rules=rules[:160],
    )


def _category(root: Path, path: Path, kind: KnowledgeKind) -> str:
    relative = path.relative_to(root)
    if kind in {KnowledgeKind.TECHNIQUE, KnowledgeKind.PRESET} and len(relative.parts) > 1:
        return relative.parts[1]
    if kind is KnowledgeKind.STYLE:
        return "style"
    if kind is KnowledgeKind.QC_CHECKLIST:
        return "qc"
    return kind.value


def _rules_from_json(payload: dict[str, Any]) -> list[str]:
    keys = (
        "timeline_pattern",
        "story_structure",
        "voiceover",
        "visual_language",
        "motion",
        "sound",
        "captions",
        "color",
        "common_mistakes",
        "qc",
        "editing_rules",
    )
    rules: list[str] = []
    for key in keys:
        values = _flatten_strings(payload.get(key))
        if key == "common_mistakes":
            rules.extend(f"Avoid: {value}" for value in values)
        elif key == "qc":
            rules.extend(f"Verify: {value}" for value in values)
        else:
            rules.extend(values)
    return _unique(rules)


def _rules_from_markdown(text: str) -> tuple[list[str], list[str], list[str]]:
    use_when: list[str] = []
    avoid_when: list[str] = []
    rules: list[str] = []
    section = "rules"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip().lower()
            if "use when" in heading or "when to use" in heading:
                section = "use"
            elif "avoid" in heading or "do not use" in heading:
                section = "avoid"
            else:
                section = "rules"
            continue
        if not stripped.startswith(("- ", "* ")):
            continue
        value = stripped[2:].strip()
        if len(value) < 8:
            continue
        if section == "use":
            use_when.append(value)
        elif section == "avoid":
            avoid_when.append(value)
        else:
            rules.append(value)
    return _unique(use_when), _unique(avoid_when), _unique(rules)


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if len(value.strip()) >= 8 else []
    if isinstance(value, list):
        return [item for child in value for item in _flatten_strings(child)]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _flatten_strings(child)]
    return []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def _markdown_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    return fallback


def _humanize(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))
