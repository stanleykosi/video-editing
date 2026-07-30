"""Evidence lookup and integrity helpers."""

from __future__ import annotations

from editorial_brain.core.models import EvidenceBundle, EvidenceKind, EvidenceRef


def evidence_by_id(bundle: EvidenceBundle) -> dict[str, EvidenceRef]:
    return {item.id: item for item in bundle.refs}


def require_evidence_kind(ref: EvidenceRef, allowed: set[EvidenceKind]) -> None:
    if ref.kind not in allowed:
        raise ValueError(f"evidence {ref.id!r} has disallowed kind {ref.kind.value!r}")


def merge_evidence(*bundles: EvidenceBundle) -> EvidenceBundle:
    merged: dict[str, EvidenceRef] = {}
    for bundle in bundles:
        for ref in bundle.refs:
            existing = merged.get(ref.id)
            if existing is not None and existing != ref:
                raise ValueError(f"conflicting evidence id {ref.id!r}")
            merged[ref.id] = ref
    return EvidenceBundle(refs=[merged[key] for key in sorted(merged)])
