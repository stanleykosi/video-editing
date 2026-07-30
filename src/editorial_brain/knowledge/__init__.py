"""Canonical editorial knowledge and per-video taste synthesis."""

from editorial_brain.knowledge.base import load_or_build_base, write_canonical_base
from editorial_brain.knowledge.compiler import apply_directives
from editorial_brain.knowledge.consolidator import consolidate_catalog
from editorial_brain.knowledge.loader import load_catalog
from editorial_brain.knowledge.models import (
    ConsolidatedKnowledgeBase,
    KnowledgeCatalog,
    KnowledgeItem,
    KnowledgeKind,
    TasteProfile,
)
from editorial_brain.knowledge.provider import RepositoryKnowledgeDirectiveProvider
from editorial_brain.knowledge.taste import (
    compile_taste_directives,
    synthesize_taste_profile,
)

__all__ = [
    "ConsolidatedKnowledgeBase",
    "KnowledgeCatalog",
    "KnowledgeItem",
    "KnowledgeKind",
    "RepositoryKnowledgeDirectiveProvider",
    "TasteProfile",
    "apply_directives",
    "compile_taste_directives",
    "consolidate_catalog",
    "load_catalog",
    "load_or_build_base",
    "synthesize_taste_profile",
    "write_canonical_base",
]
