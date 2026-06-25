"""Route repo knowledge into a focused from-scratch project plan.

The knowledge base is intentionally broad: skills, extracted lessons, technique
cards, presets, style packs, and QC checklists. This helper scans those layers
and writes a project-local knowledge plan so sub-agents know what to read before
writing scripts, visuals, timelines, captions, sound, and QC.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCAN_ROOTS = (
    "content_creation",
    "sources",
    "extracted_lessons",
    "style_packs",
    "skills",
    "technique_cards",
    "presets",
    "qc_checklists",
)

UNIVERSAL_CONTENT = (
    "content_creation/knowledge_router.md",
    "content_creation/faceless_video_workflow.md",
    "content_creation/scriptwriter.md",
    "content_creation/visual_planner.md",
    "content_creation/asset_planner.md",
    "content_creation/voiceover_planner.md",
    "content_creation/subagent_modules.md",
)

CORE_SKILLS = (
    "skills/editing_taste_story_pacing.md",
    "skills/short_form_retention.md",
    "skills/kinetic_captions.md",
    "skills/video_typography.md",
    "skills/sound_design.md",
    "skills/beat_sync.md",
    "skills/motion_graphics.md",
    "skills/color_grading.md",
    "skills/editor_qc.md",
)

ALWAYS_SOURCE_DOCS = (
    "sources/asset_resource_platforms.md",
)

RESEARCH_TERMS = {
    "fact",
    "facts",
    "research",
    "source",
    "sources",
    "documentary",
    "history",
    "business",
    "data",
    "stat",
    "stats",
    "study",
    "news",
    "science",
    "football",
    "sports",
}

YOUTUBE_STORY_TERMS = {
    "youtube",
    "story",
    "storytelling",
    "documentary",
    "viral",
    "retention",
    "business",
    "history",
}

DOMAIN_TERMS: dict[str, tuple[str, ...]] = {
    "documentary": (
        "documentary",
        "vox",
        "archive",
        "archival",
        "evidence",
        "document",
        "source",
        "map",
        "chart",
        "paper",
        "history",
    ),
    "sports": (
        "football",
        "soccer",
        "sports",
        "match",
        "player",
        "tactical",
        "pitch",
        "team",
        "club",
        "analysis",
    ),
    "business": (
        "business",
        "company",
        "founder",
        "startup",
        "market",
        "money",
        "brand",
        "history",
        "case",
    ),
    "retention": (
        "viral",
        "short",
        "shorts",
        "reel",
        "reels",
        "tiktok",
        "hook",
        "retention",
        "intro",
        "payoff",
    ),
    "captions": (
        "caption",
        "captions",
        "subtitle",
        "subtitles",
        "kinetic",
        "text",
        "typography",
        "font",
        "word",
    ),
    "sound": (
        "sound",
        "sfx",
        "music",
        "audio",
        "voiceover",
        "duck",
        "foley",
        "mix",
    ),
    "motion": (
        "motion",
        "animation",
        "keyframe",
        "keyframes",
        "remotion",
        "capcut",
        "zoom",
        "transition",
        "overlay",
        "mask",
        "glow",
    ),
    "color": (
        "color",
        "grade",
        "grading",
        "look",
        "palette",
        "contrast",
    ),
    "assets": (
        "asset",
        "assets",
        "stock",
        "footage",
        "image",
        "generated",
        "map",
        "chart",
        "manifest",
    ),
}

STOP_WORDS = {
    "about",
    "after",
    "again",
    "agent",
    "also",
    "and",
    "are",
    "because",
    "before",
    "build",
    "can",
    "create",
    "does",
    "edit",
    "editing",
    "for",
    "from",
    "has",
    "have",
    "how",
    "into",
    "its",
    "make",
    "not",
    "only",
    "project",
    "repo",
    "scratch",
    "that",
    "the",
    "this",
    "use",
    "used",
    "using",
    "video",
    "want",
    "what",
    "when",
    "with",
    "workflow",
    "your",
}


@dataclass
class KnowledgeItem:
    path: str
    kind: str
    category: str
    title: str
    score: int = 0
    matched_terms: list[str] = field(default_factory=list)
    reason: str = ""
    required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    _search_text: str = field(default="", repr=False)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_root_from_helper() -> Path:
    return Path(__file__).resolve().parents[3]


def safe_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path, limit: int | None = None) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if limit is not None and len(text) > limit:
        return text[:limit]
    return text


def title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def title_from_stem(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def flatten_json_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, list):
        for item in value:
            strings.extend(flatten_json_strings(item))
    elif isinstance(value, dict):
        for key, item in value.items():
            strings.append(str(key))
            strings.extend(flatten_json_strings(item))
    return strings


def item_kind_and_category(rel: str, data: dict[str, Any] | None) -> tuple[str, str]:
    parts = rel.split("/")
    top = parts[0]
    if top == "content_creation":
        return "content_creation", parts[1] if len(parts) > 2 else "workflow"
    if top == "sources":
        return "source_doc", "source"
    if top == "extracted_lessons":
        return "extracted_lesson", "lesson"
    if top == "style_packs":
        suffix = Path(rel).suffix.lower()
        return "style_pack", "json" if suffix == ".json" else "style_reference"
    if top == "skills":
        return "skill", "skill"
    if top == "technique_cards":
        category = str((data or {}).get("category") or Path(rel).stem.split("_", 1)[0])
        return "technique_card", category
    if top == "presets":
        return "preset", parts[1] if len(parts) > 1 else "preset"
    if top == "qc_checklists":
        return "qc_checklist", "qc"
    return "other", top


def load_item(path: Path, root: Path) -> KnowledgeItem:
    rel = safe_rel(path, root)
    text = read_text(path, limit=20000)
    data: dict[str, Any] | None = None
    if path.suffix.lower() == ".json":
        try:
            parsed = json.loads(text)
            data = parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError as exc:
            data = {"json_error": str(exc)}

    kind, category = item_kind_and_category(rel, data)
    title = title_from_stem(path)
    metadata: dict[str, Any] = {}

    if data:
        title = str(data.get("name") or data.get("id") or title)
        for key in ("id", "version", "category", "source_tutorial", "additional_sources", "knowledge_files"):
            if key in data:
                metadata[key] = data[key]
        search_bits = [rel, title, category, *flatten_json_strings(data)]
    else:
        title = title_from_markdown(text, title)
        search_bits = [rel, title, category, text]

    return KnowledgeItem(
        path=rel,
        kind=kind,
        category=category,
        title=title,
        metadata=metadata,
        _search_text=" ".join(str(bit) for bit in search_bits if bit),
    )


def scan_knowledge(root: Path) -> list[KnowledgeItem]:
    items: list[KnowledgeItem] = []
    for folder in SCAN_ROOTS:
        base = root / folder
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if any(part.startswith(".") for part in path.relative_to(base).parts):
                continue
            if path.suffix.lower() not in {".md", ".json", ".txt"}:
                continue
            items.append(load_item(path, root))
    return items


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if len(token) > 2 and token not in STOP_WORDS]


def infer_domains(query_text: str) -> list[str]:
    lowered = query_text.lower()
    domains: list[str] = []
    for domain, terms in DOMAIN_TERMS.items():
        if any(term in lowered for term in terms):
            domains.append(domain)
    return domains


def style_pack_data(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists() or path.suffix.lower() != ".json":
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def resolve_style_pack(root: Path, requested: str, video_type: str, brief: str) -> Path | None:
    style_dir = root / "style_packs"
    candidates = sorted(style_dir.glob("*.json")) if style_dir.exists() else []

    def matches(path: Path, needle: str) -> bool:
        if not needle:
            return False
        lowered = needle.lower().replace(" ", "_")
        data = style_pack_data(path)
        values = {
            path.stem.lower(),
            str(data.get("id", "")).lower(),
            str(data.get("name", "")).lower().replace(" ", "_"),
        }
        return lowered in values

    for value in (requested, video_type):
        if not value:
            continue
        direct = Path(value)
        if not direct.is_absolute():
            direct = root / direct
        if direct.exists():
            return direct
        for candidate in candidates:
            if matches(candidate, value):
                return candidate

    lowered = f"{brief} {video_type}".lower()
    heuristic_order = [
        ("football_analysis_short", ("football", "soccer", "match", "tactical", "sports")),
        ("business_history_short", ("business", "company", "founder", "startup", "market", "history")),
        ("documentary_explainer", ("documentary", "archive", "evidence", "historical", "history")),
        ("viral_storytelling_short", ("viral", "story", "storytelling", "hook", "retention")),
        ("faceless_educational_short", ("education", "educational", "explainer", "how", "topic")),
    ]
    for style_id, terms in heuristic_order:
        if any(term in lowered for term in terms):
            for candidate in candidates:
                if matches(candidate, style_id):
                    return candidate

    for candidate in candidates:
        if matches(candidate, "faceless_educational_short"):
            return candidate
    return candidates[0] if candidates else None


def project_brief(project_dir: Path) -> str:
    pieces: list[str] = []
    for name in ("project.md", "script.md", "visual_plan.md", "asset_list.md"):
        path = project_dir / name
        if path.exists():
            pieces.append(read_text(path, limit=8000))
    return "\n\n".join(pieces)


def score_item(item: KnowledgeItem, query_tokens: set[str], domains: list[str]) -> KnowledgeItem:
    search = item._search_text.lower()
    path_title = f"{item.path} {item.title} {item.category}".lower()
    search_tokens = set(tokenize(search))
    path_tokens = set(tokenize(path_title))
    matched = sorted(token for token in query_tokens if token in search_tokens or token in path_tokens)
    score = 0
    for token in matched:
        if token in path_tokens:
            score += 5
        if token in search_tokens:
            score += 1

    for domain in domains:
        terms = DOMAIN_TERMS[domain]
        if any(term in search for term in terms):
            score += 8
        if any(term in path_title for term in terms):
            score += 6

    if item.kind == "style_pack":
        score += 2
    if item.kind == "skill":
        score += 2
    if item.kind == "qc_checklist":
        score += 2
    if item.kind == "technique_card" and item.path.endswith("_template.json"):
        score = 0

    item.score = score
    item.matched_terms = matched[:16]
    if matched:
        item.reason = f"matched: {', '.join(matched[:8])}"
    elif domains and score > 0:
        item.reason = f"domain match: {', '.join(domains[:4])}"
    return item


def entry(item: KnowledgeItem) -> dict[str, Any]:
    data = asdict(item)
    data.pop("_search_text", None)
    return data


def select_required(items_by_path: dict[str, KnowledgeItem], rel: str, reason: str, selected: dict[str, KnowledgeItem]) -> None:
    item = items_by_path.get(rel)
    if not item:
        return
    item.required = True
    item.reason = reason
    item.score = max(item.score, 1000)
    selected[item.path] = item


def select_top(
    items: list[KnowledgeItem],
    kind: str,
    limit: int,
    selected: dict[str, KnowledgeItem],
    minimum_score: int = 1,
) -> list[KnowledgeItem]:
    candidates = [
        item
        for item in items
        if item.kind == kind
        and item.path not in selected
        and item.score >= minimum_score
        and not item.path.endswith("_template.json")
    ]
    candidates.sort(key=lambda item: (-item.score, item.path))
    picked = candidates[:limit]
    for item in picked:
        selected[item.path] = item
    return picked


def selected_by_kind(selected: dict[str, KnowledgeItem], kind: str) -> list[KnowledgeItem]:
    items = [item for item in selected.values() if item.kind == kind]
    return sorted(items, key=lambda item: (not item.required, -item.score, item.path))


def build_plan(
    root: Path,
    project_dir: Path,
    brief: str,
    video_type: str,
    style_pack_arg: str,
    max_skills: int,
    max_techniques: int,
    max_presets: int,
    max_qc: int,
    max_lessons: int,
    max_sources: int,
) -> dict[str, Any]:
    items = scan_knowledge(root)
    items_by_path = {item.path: item for item in items}
    style_path = resolve_style_pack(root, style_pack_arg, video_type, brief)
    style_rel = safe_rel(style_path, root) if style_path else ""
    style_data = style_pack_data(style_path)
    style_text = " ".join(flatten_json_strings(style_data))
    query_text = " ".join(
        bit
        for bit in (
            brief,
            video_type,
            style_rel,
            str(style_data.get("id", "")),
            str(style_data.get("name", "")),
            style_text,
            "faceless script visual asset voiceover captions motion sound qc render",
        )
        if bit
    )
    query_tokens = set(tokenize(query_text))
    domains = infer_domains(query_text)

    for item in items:
        score_item(item, query_tokens, domains)

    selected: dict[str, KnowledgeItem] = {}
    for rel in UNIVERSAL_CONTENT:
        select_required(items_by_path, rel, "universal from-scratch workflow layer", selected)
    for rel in ALWAYS_SOURCE_DOCS:
        select_required(items_by_path, rel, "asset/resource rights guidance is required before sourcing", selected)
    if style_rel:
        select_required(items_by_path, style_rel, "selected or inferred style pack", selected)

    style_knowledge_files = style_data.get("knowledge_files", [])
    if isinstance(style_knowledge_files, list):
        for rel_value in style_knowledge_files:
            rel = str(rel_value).strip()
            select_required(items_by_path, rel, "required by selected style pack", selected)

    for rel in CORE_SKILLS:
        select_required(items_by_path, rel, "core from-scratch editing skill", selected)

    brief_tokens = set(tokenize(query_text))
    if brief_tokens & RESEARCH_TERMS:
        select_required(
            items_by_path,
            "content_creation/research_to_script.md",
            "factual or research-led topic detected",
            selected,
        )
    if brief_tokens & YOUTUBE_STORY_TERMS:
        select_required(
            items_by_path,
            "content_creation/youtube_storytelling_workflow.md",
            "story-led or retention-led format detected",
            selected,
        )

    select_top(items, "skill", max_skills, selected)
    select_top(items, "technique_card", max_techniques, selected)
    select_top(items, "preset", max_presets, selected)
    select_top(items, "qc_checklist", max_qc, selected)
    select_top(items, "extracted_lesson", max_lessons, selected)
    select_top(items, "source_doc", max_sources, selected)

    inventory_counts = Counter(item.kind for item in items)
    selected_counts = Counter(item.kind for item in selected.values())
    inventory = [entry(item) for item in sorted(items, key=lambda value: value.path)]

    return {
        "created_at": utc_now(),
        "repo_root": str(root),
        "project_dir": str(project_dir),
        "brief": brief,
        "video_type": video_type,
        "style_pack": {
            "path": style_rel,
            "id": style_data.get("id", ""),
            "name": style_data.get("name", ""),
        },
        "domains_detected": domains,
        "inventory_counts": dict(sorted(inventory_counts.items())),
        "selected_counts": dict(sorted(selected_counts.items())),
        "selected": {
            "content_creation": [entry(item) for item in selected_by_kind(selected, "content_creation")],
            "source_docs": [entry(item) for item in selected_by_kind(selected, "source_doc")],
            "style_packs": [entry(item) for item in selected_by_kind(selected, "style_pack")],
            "skills": [entry(item) for item in selected_by_kind(selected, "skill")],
            "extracted_lessons": [entry(item) for item in selected_by_kind(selected, "extracted_lesson")],
            "technique_cards": [entry(item) for item in selected_by_kind(selected, "technique_card")],
            "presets": [entry(item) for item in selected_by_kind(selected, "preset")],
            "qc_checklists": [entry(item) for item in selected_by_kind(selected, "qc_checklist")],
        },
        "inventory": inventory,
        "usage_rule": (
            "Sub-agents should read knowledge_plan.md first, load only the selected files "
            "needed for their module, and cite the influencing files in project artifacts."
        ),
    }


def markdown_list(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- None selected"]
    lines: list[str] = []
    for item in items:
        reason = item.get("reason") or "selected by score"
        score = item.get("score", 0)
        required = " required" if item.get("required") else ""
        lines.append(f"- `{item['path']}` - {item['title']} ({reason}; score {score}{required})")
    return lines


def write_markdown(path: Path, plan: dict[str, Any]) -> None:
    selected = plan["selected"]
    lines = [
        "# Knowledge Plan",
        "",
        f"- Created at: {plan['created_at']}",
        f"- Project: `{plan['project_dir']}`",
        f"- Video type: `{plan['video_type'] or 'unspecified'}`",
        f"- Style pack: `{plan['style_pack'].get('path') or 'unspecified'}`",
        f"- Detected domains: {', '.join(plan['domains_detected']) or 'none'}",
        "",
        "## Brief",
        "",
        plan["brief"].strip() or "No brief found yet.",
        "",
        "## Inventory Scanned",
        "",
    ]
    for kind, count in plan["inventory_counts"].items():
        selected_count = plan["selected_counts"].get(kind, 0)
        lines.append(f"- {kind}: {count} scanned, {selected_count} selected")

    section_order = [
        ("Content Creation Docs", "content_creation"),
        ("Source Docs", "source_docs"),
        ("Style Packs", "style_packs"),
        ("Skills", "skills"),
        ("Extracted Lessons", "extracted_lessons"),
        ("Technique Cards", "technique_cards"),
        ("Presets", "presets"),
        ("QC Checklists", "qc_checklists"),
    ]
    for title, key in section_order:
        lines.extend(["", f"## {title}", ""])
        lines.extend(markdown_list(selected[key]))

    lines.extend(
        [
            "",
            "## How Sub-Agents Should Use This",
            "",
            "- Script and research agents read the content creation docs, style pack, core story/retention skills, and any selected extracted lessons.",
            "- Visual, asset, caption, sound, and motion agents read their matching skills, technique cards, and presets before writing project artifacts.",
            "- Timeline and renderer agents use the selected technique cards and presets as implementation hints, not as mandatory decoration.",
            "- QC agents combine `qc_check.py` with the selected QC checklists and relevant card-level `qc` rules.",
            "- Raw transcripts are not part of this route; only distilled lessons and structured knowledge should shape final project files.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a project-specific video editing knowledge plan.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--brief", default="")
    parser.add_argument("--video-type", default="")
    parser.add_argument("--style-pack", default="")
    parser.add_argument("--repo-root", type=Path, default=repo_root_from_helper())
    parser.add_argument("--max-skills", type=int, default=16)
    parser.add_argument("--max-techniques", type=int, default=24)
    parser.add_argument("--max-presets", type=int, default=18)
    parser.add_argument("--max-qc", type=int, default=12)
    parser.add_argument("--max-lessons", type=int, default=8)
    parser.add_argument("--max-sources", type=int, default=4)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    project_dir = args.project_dir.resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    brief = args.brief.strip() or project_brief(project_dir)
    output = args.output or project_dir / "knowledge_plan.md"
    json_output = args.json_output or project_dir / "knowledge_plan.json"

    plan = build_plan(
        root=root,
        project_dir=project_dir,
        brief=brief,
        video_type=args.video_type,
        style_pack_arg=args.style_pack,
        max_skills=args.max_skills,
        max_techniques=args.max_techniques,
        max_presets=args.max_presets,
        max_qc=args.max_qc,
        max_lessons=args.max_lessons,
        max_sources=args.max_sources,
    )
    write_markdown(output, plan)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "knowledge_plan": str(output),
                "json": str(json_output),
                "inventory_counts": plan["inventory_counts"],
                "selected_counts": plan["selected_counts"],
                "style_pack": plan["style_pack"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
