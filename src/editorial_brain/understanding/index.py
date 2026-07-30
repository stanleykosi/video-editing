"""Deterministic searchable source-document index."""

from __future__ import annotations

import re
from collections import defaultdict

from pydantic import Field

from editorial_brain.core.models import BrainModel, MediaUnderstandingIndex

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class SearchDocument(BrainModel):
    id: str
    kind: str
    media_id: str
    text: str
    terms: list[str]
    source_id: str


class SearchHit(BrainModel):
    document_id: str
    score: float = Field(ge=0, le=1)
    matched_terms: list[str]


class UnderstandingSearchIndex:
    def __init__(self, documents: list[SearchDocument]) -> None:
        self.documents = {document.id: document for document in documents}
        self._postings: dict[str, set[str]] = defaultdict(set)
        for document in documents:
            for term in document.terms:
                self._postings[term].add(document.id)

    @classmethod
    def build(cls, source: MediaUnderstandingIndex) -> UnderstandingSearchIndex:
        documents: list[SearchDocument] = []
        for shot in source.shots:
            text = " ".join([shot.semantics.summary, *shot.semantics.search_terms])
            documents.append(
                SearchDocument(
                    id=f"document:{shot.id}",
                    kind="shot",
                    media_id=shot.media_id,
                    text=text,
                    terms=_terms(text),
                    source_id=shot.id,
                )
            )
        for transcript in source.transcripts:
            for phrase in transcript.phrases:
                documents.append(
                    SearchDocument(
                        id=f"document:{phrase.id}",
                        kind="phrase",
                        media_id=transcript.media_id,
                        text=phrase.text,
                        terms=_terms(phrase.text),
                        source_id=phrase.id,
                    )
                )
        return cls(documents)

    def search(self, query: str, *, limit: int = 20) -> list[SearchHit]:
        if limit <= 0:
            raise ValueError("search limit must be positive")
        query_terms = set(_terms(query))
        candidate_ids = set().union(*(self._postings[term] for term in query_terms))
        hits: list[SearchHit] = []
        for document_id in candidate_ids:
            document = self.documents[document_id]
            matched = sorted(query_terms & set(document.terms))
            score = len(matched) / max(1, len(query_terms | set(document.terms)))
            hits.append(SearchHit(document_id=document_id, score=score, matched_terms=matched))
        return sorted(hits, key=lambda hit: (-hit.score, hit.document_id))[:limit]


def _terms(value: str) -> list[str]:
    return sorted(set(TOKEN_PATTERN.findall(value.lower())))
