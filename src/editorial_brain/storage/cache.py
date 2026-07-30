"""Validated content-addressed semantic and analysis cache."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from editorial_brain.core.hashing import canonical_payload, fingerprint
from editorial_brain.storage.locks import file_lock

NAMESPACE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
ModelT = TypeVar("ModelT", bound=BaseModel)


class CacheIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    namespace: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")
    source_hashes: dict[str, str]
    analysis_version: str
    provider: str
    model: str
    provider_fingerprint: str
    prompt_fingerprint: str
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_source_hashes(self) -> CacheIdentity:
        for media_id, digest in self.source_hashes.items():
            if (
                not media_id
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise ValueError(f"invalid cache source identity for {media_id!r}")
        return self

    @property
    def key(self) -> str:
        return fingerprint(self)


class CacheEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    identity: CacheIdentity
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload: Any
    created_at: datetime


class BrainCache:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.quarantine = self.root / "quarantine"

    def load(self, identity: CacheIdentity, model_type: type[ModelT]) -> ModelT | None:
        path = self._path(identity)
        if not path.exists():
            return None
        with file_lock(path.with_suffix(".lock")):
            try:
                envelope = CacheEnvelope.model_validate_json(path.read_text(encoding="utf-8"))
                if envelope.identity != identity:
                    raise ValueError("cache identity mismatch")
                if fingerprint(envelope.payload) != envelope.payload_sha256:
                    raise ValueError("cache payload checksum mismatch")
                return model_type.model_validate(envelope.payload)
            except (OSError, ValueError, json.JSONDecodeError):
                self._quarantine(path)
                return None

    def store(self, identity: CacheIdentity, value: BaseModel) -> Path:
        path = self._path(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(path.with_suffix(".lock")):
            payload = value.model_dump(mode="json", exclude_none=True)
            envelope = CacheEnvelope(
                identity=identity,
                payload_sha256=fingerprint(payload),
                payload=payload,
                created_at=datetime.now(UTC),
            )
            _atomic_write(path, canonical_payload(envelope))
        return path

    def _path(self, identity: CacheIdentity) -> Path:
        if not NAMESPACE_PATTERN.fullmatch(identity.namespace):
            raise ValueError("unsafe cache namespace")
        return self.root / identity.namespace / identity.key[:2] / f"{identity.key}.json"

    def _quarantine(self, path: Path) -> None:
        if not path.exists():
            return
        self.quarantine.mkdir(parents=True, exist_ok=True)
        destination = self.quarantine / f"{path.stem}-{datetime.now(UTC).timestamp():.0f}.invalid"
        os.replace(path, destination)


def _atomic_write(path: Path, payload: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()
