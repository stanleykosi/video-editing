"""Versioned artifacts and explicit diffs for the ten editorial passes."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from editorial_brain.core.hashing import fingerprint
from editorial_brain.core.models import VersionedModel

PassName = Literal[
    "understanding",
    "selects",
    "assembly",
    "story_refinement",
    "fine_cut",
    "audio_picture",
    "broll_cutaways",
    "rhythm",
    "presentation_intent",
    "compile",
]


class EditorialPassArtifact(VersionedModel):
    run_id: str
    pass_number: int = Field(ge=1, le=10)
    name: PassName
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    changed_paths: list[str] = Field(default_factory=list)
    summary: str


def make_pass_artifact(
    run_id: str,
    pass_number: int,
    name: PassName,
    before: object,
    after: object,
    summary: str,
) -> EditorialPassArtifact:
    before_payload = _payload(before)
    after_payload = _payload(after)
    return EditorialPassArtifact(
        run_id=run_id,
        pass_number=pass_number,
        name=name,
        input_fingerprint=fingerprint(before_payload),
        output_fingerprint=fingerprint(after_payload),
        changed_paths=_diff(before_payload, after_payload),
        summary=summary,
    )


def _payload(value: object) -> object:
    dump = getattr(value, "model_dump", None)
    return dump(mode="json") if callable(dump) else value


def _diff(left: object, right: object, prefix: str = "$") -> list[str]:
    if type(left) is not type(right):
        return [prefix]
    if isinstance(left, dict) and isinstance(right, dict):
        paths: list[str] = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                paths.append(f"{prefix}.{key}")
            else:
                paths.extend(_diff(left[key], right[key], f"{prefix}.{key}"))
        return paths
    if isinstance(left, list) and isinstance(right, list):
        paths = []
        for index in range(max(len(left), len(right))):
            if index >= len(left) or index >= len(right):
                paths.append(f"{prefix}[{index}]")
            else:
                paths.extend(_diff(left[index], right[index], f"{prefix}[{index}]"))
        return paths
    return [] if left == right else [prefix]
