"""Search helpers over understood media."""

from editorial_brain.understanding.index import SearchHit, UnderstandingSearchIndex


def search_sources(
    index: UnderstandingSearchIndex, query: str, *, limit: int = 20
) -> list[SearchHit]:
    return index.search(query, limit=limit)
