"""Semantic continuity from explicit search terms."""

from editorial_brain.core.models import Shot


def semantic_continuity(left: Shot, right: Shot) -> float:
    left_terms = set(left.semantics.search_terms)
    right_terms = set(right.semantics.search_terms)
    if not left_terms or not right_terms:
        return 0.5
    return len(left_terms & right_terms) / len(left_terms | right_terms)
