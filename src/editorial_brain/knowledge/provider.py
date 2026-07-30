"""Repository-backed executable editorial directive provider."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from editorial_brain.core.models import (
    BrainModel,
    EditorialBrief,
    MediaUnderstandingIndex,
    ReferenceEditProfile,
)
from editorial_brain.knowledge.base import load_or_build_base
from editorial_brain.knowledge.consolidator import consolidate_catalog
from editorial_brain.knowledge.loader import load_catalog
from editorial_brain.knowledge.models import (
    ConsolidatedKnowledgeBase,
    KnowledgeCatalog,
    TasteProfile,
)
from editorial_brain.knowledge.taste import compile_taste_directives, synthesize_taste_profile
from editorial_brain.policies.models import EditorialDirective, EditorialDirectiveProvider
from editorial_brain.storage.artifacts import ArtifactStore


class RepositoryKnowledgeDirectiveProvider(EditorialDirectiveProvider):
    """Compile the canonical knowledge tree into bounded per-brief priors."""

    def __init__(self, project_root: Path, *, knowledge_root: Path | None = None) -> None:
        self.project_root = project_root.resolve()
        self.knowledge_root = (knowledge_root or self.project_root / "knowledge").resolve()
        self.artifacts = ArtifactStore(self.project_root)
        self.last_catalog: KnowledgeCatalog | None = None
        self.last_base: ConsolidatedKnowledgeBase | None = None
        self.last_profile: TasteProfile | None = None

    def directives(self, brief: EditorialBrief) -> list[EditorialDirective]:
        return self.directives_for(brief)

    def consolidated_base(self) -> ConsolidatedKnowledgeBase:
        catalog = self.last_catalog or load_catalog(self.knowledge_root)
        self.last_catalog = catalog
        base = self.last_base or load_or_build_base(self.knowledge_root, catalog)
        self.last_base = base
        return base

    def directives_for(
        self,
        brief: EditorialBrief,
        *,
        reference: ReferenceEditProfile | None = None,
        index: MediaUnderstandingIndex | None = None,
    ) -> list[EditorialDirective]:
        base = self.consolidated_base()
        if brief.knowledge_mode == "off":
            self.last_profile = _empty_profile(base, brief)
            self.artifacts.write_model("knowledge", f"taste-{_safe(brief.id)}", self.last_profile)
            return []
        profile = synthesize_taste_profile(base, brief, reference=reference, index=index)
        self.last_profile = profile
        self.artifacts.write_model("knowledge", f"taste-{_safe(brief.id)}", profile)
        directives = compile_taste_directives(base, profile)
        self.artifacts.write_model(
            "knowledge",
            f"directives-{_safe(brief.id)}",
            _DirectiveArtifact(
                base_fingerprint=base.fingerprint,
                taste_fingerprint=profile.fingerprint,
                directives=directives,
            ),
        )
        return directives

    def status(self) -> dict[str, object]:
        catalog = self.last_catalog or load_catalog(self.knowledge_root)
        base = self.last_base or consolidate_catalog(catalog)
        return {
            "configured": self.knowledge_root.is_dir(),
            "knowledge_root": str(self.knowledge_root),
            "catalog_items": len(catalog.items),
            "rejected_files": len(catalog.rejected_files),
            "catalog_fingerprint": catalog.fingerprint,
            "canonical_principles": len(base.principles),
            "duplicate_statements_removed": base.statistics.duplicate_statements_removed,
            "resolved_conflicts": base.statistics.conflicts_resolved,
            "unresolved_conflicts": base.statistics.unresolved_conflicts,
            "base_fingerprint": base.fingerprint,
            "last_taste_profile_id": self.last_profile.id if self.last_profile else None,
            "last_taste_fingerprint": (
                self.last_profile.fingerprint if self.last_profile else None
            ),
        }


class _DirectiveArtifact(BrainModel):
    base_fingerprint: str
    taste_fingerprint: str
    directives: list[EditorialDirective] = Field(default_factory=list)


def _empty_profile(base: ConsolidatedKnowledgeBase, brief: EditorialBrief) -> TasteProfile:
    from editorial_brain.core.hashing import fingerprint

    value = fingerprint({"brief_id": brief.id, "base": base.fingerprint, "mode": "off"})
    from editorial_brain.knowledge.models import TASTE_AXES

    return TasteProfile(
        id=f"taste:{value[:20]}",
        brief_id=brief.id,
        base_fingerprint=base.fingerprint,
        fingerprint=value,
        axes={axis: 0 for axis in TASTE_AXES},
        selected=[],
        confidence=0,
        reasons=["repository taste explicitly disabled"],
    )


def _safe(value: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")[:100] or "brief"
