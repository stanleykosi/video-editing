"""Load and validate the checked canonical source-neutral taste base."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from editorial_brain.knowledge.consolidator import consolidate_catalog
from editorial_brain.knowledge.models import ConsolidatedKnowledgeBase, KnowledgeCatalog

CANONICAL_RELATIVE_PATH = Path("editorial_base/v1/index.json")


def load_or_build_base(
    knowledge_root: Path, catalog: KnowledgeCatalog
) -> ConsolidatedKnowledgeBase:
    path = knowledge_root / CANONICAL_RELATIVE_PATH
    if path.is_file():
        try:
            base = _load_checked_base(str(path), path.stat().st_mtime_ns, catalog.fingerprint)
            if base is not None:
                return base
        except (OSError, ValueError):
            pass
    return consolidate_catalog(catalog)


@lru_cache(maxsize=8)
def _load_checked_base(
    path: str, modified_ns: int, input_fingerprint: str
) -> ConsolidatedKnowledgeBase | None:
    del modified_ns
    base = ConsolidatedKnowledgeBase.model_validate_json(Path(path).read_text(encoding="utf-8"))
    return base if base.input_fingerprint == input_fingerprint else None


def write_canonical_base(knowledge_root: Path, base: ConsolidatedKnowledgeBase) -> Path:
    path = knowledge_root / CANONICAL_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(base.model_dump_json(), encoding="utf-8")
    temporary.replace(path)
    return path
