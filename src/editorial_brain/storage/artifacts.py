"""Project-scoped Brain artifact layout and atomic publication."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from editorial_brain.core.hashing import canonical_payload
from editorial_brain.storage.cache import _atomic_write

ARTIFACT_DIRECTORIES = (
    "analysis",
    "shots",
    "frames",
    "transcripts",
    "semantics",
    "story",
    "selects",
    "candidates",
    "plans",
    "variants",
    "reference",
    "knowledge",
    "traces",
    "benchmarks",
    "cache",
)
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class ArtifactStore:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.root = self.project_root / ".editorial-brain"
        self.root.mkdir(parents=True, exist_ok=True)
        for directory in ARTIFACT_DIRECTORIES:
            (self.root / directory).mkdir(parents=True, exist_ok=True)

    def write_model(self, category: str, name: str, value: BaseModel) -> Path:
        destination = self.path(category, name, suffix=".json")
        _atomic_write(destination, canonical_payload(value))
        return destination

    def write_text(self, category: str, name: str, value: str) -> Path:
        destination = self.path(category, name, suffix=".md")
        _atomic_write(destination, value.encode("utf-8"))
        return destination

    def path(self, category: str, name: str, *, suffix: str) -> Path:
        if category not in ARTIFACT_DIRECTORIES:
            raise ValueError(f"unknown artifact category {category!r}")
        if not SAFE_NAME.fullmatch(name):
            raise ValueError("unsafe artifact name")
        if suffix not in {".json", ".md", ".png", ".jpg", ".webp"}:
            raise ValueError("unsupported artifact suffix")
        return self.root / category / f"{name}{suffix}"
