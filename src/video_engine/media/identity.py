"""Persistent source-byte identity verification without redundant full reads."""

from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from fcntl import LOCK_EX, LOCK_UN, flock
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from video_engine.errors import EngineError, ErrorCode
from video_engine.storage.atomic import atomic_write_text


class SourceIdentityRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    size_bytes: int = Field(ge=0)
    modified_ns: int = Field(ge=0)
    changed_ns: int = Field(ge=0)
    device: int = Field(ge=0)
    inode: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SourceIdentityData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    records: list[SourceIdentityRecord] = Field(default_factory=list)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SourceIdentityStore:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.path.with_suffix(self.path.suffix + ".lock"),
            os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        try:
            flock(descriptor, LOCK_EX)
            yield
        finally:
            flock(descriptor, LOCK_UN)
            os.close(descriptor)

    def _load(self) -> SourceIdentityData:
        try:
            return SourceIdentityData.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            return SourceIdentityData()

    @staticmethod
    def _matches(record: SourceIdentityRecord, path: Path) -> bool:
        stat = path.stat()
        return (
            record.path == path
            and record.size_bytes == stat.st_size
            and record.modified_ns == stat.st_mtime_ns
            and record.changed_ns == stat.st_ctime_ns
            and record.device == stat.st_dev
            and record.inode == stat.st_ino
        )

    def verify(self, path: Path) -> tuple[str, bool]:
        """Return `(sha256, cache_hit)` after verifying current file identity."""

        source = path.resolve()
        with self._lock():
            data = self._load()
            existing = next((record for record in data.records if record.path == source), None)
            if existing is not None and self._matches(existing, source):
                return existing.sha256, True
            stat = source.stat()
            digest = _sha256_file(source)
            record = SourceIdentityRecord(
                path=source,
                size_bytes=stat.st_size,
                modified_ns=stat.st_mtime_ns,
                changed_ns=stat.st_ctime_ns,
                device=stat.st_dev,
                inode=stat.st_ino,
                sha256=digest,
            )
            data.records = [item for item in data.records if item.path != source]
            data.records.append(record)
            atomic_write_text(self.path, data.model_dump_json(indent=2) + "\n")
            return digest, False

    @contextmanager
    def _destination_lock(self, destination: Path) -> Iterator[None]:
        lock_root = destination.parent / ".locks"
        lock_root.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            lock_root / f"{destination.name}.lock",
            os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        try:
            flock(descriptor, LOCK_EX)
            yield
        finally:
            flock(descriptor, LOCK_UN)
            os.close(descriptor)

    def materialize_verified(
        self,
        source: Path,
        destination: Path,
        *,
        expected_sha256: str,
    ) -> Path:
        """Publish an immutable byte snapshot only when its digest is exact."""

        source = source.resolve()
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._destination_lock(destination):
            if destination.is_file():
                actual, _ = self.verify(destination)
                if actual == expected_sha256:
                    return destination
                quarantine = destination.with_name(
                    f".{destination.name}.corrupt-{uuid.uuid4().hex}"
                )
                os.replace(destination, quarantine)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=".partial",
                dir=destination.parent,
            )
            temporary = Path(temporary_name)
            digest = hashlib.sha256()
            try:
                with (
                    source.open("rb") as source_handle,
                    os.fdopen(descriptor, "wb") as destination_handle,
                ):
                    for chunk in iter(lambda: source_handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                        destination_handle.write(chunk)
                    destination_handle.flush()
                    os.fsync(destination_handle.fileno())
                actual = digest.hexdigest()
                if actual != expected_sha256:
                    raise EngineError(
                        ErrorCode.MEDIA_INVALID,
                        "source changed while creating a verified snapshot",
                        context={
                            "source": str(source),
                            "expected": expected_sha256,
                            "actual": actual,
                        },
                    )
                os.chmod(temporary, 0o444)
                os.replace(temporary, destination)
                directory = os.open(destination.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
                verified, _ = self.verify(destination)
                if verified != expected_sha256:
                    raise EngineError(
                        ErrorCode.MEDIA_INVALID,
                        "published source snapshot failed identity validation",
                        context={"path": str(destination)},
                    )
                return destination
            finally:
                temporary.unlink(missing_ok=True)
