"""Atomic on-disk registry for content-addressed media records."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from fcntl import LOCK_EX, LOCK_UN, flock
from pathlib import Path

from video_engine.errors import StorageError
from video_engine.media.models import MediaRecord, MediaRegistryData


class MediaRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = self._load()

    def _load(self) -> MediaRegistryData:
        if not self.path.exists():
            return MediaRegistryData()
        try:
            return MediaRegistryData.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise StorageError(
                "failed to load media registry",
                context={"path": str(self.path), "detail": str(exc)},
            ) from exc

    def refresh(self) -> MediaRegistry:
        self.data = self._load()
        return self

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

    def save(self) -> None:
        with self._lock():
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(self.data.model_dump_json(indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise StorageError(
                "failed to save media registry",
                context={"path": str(self.path), "detail": str(exc)},
            ) from exc

    def get(self, media_id: str) -> MediaRecord:
        for record in self.data.records:
            if record.id == media_id:
                return record
        raise KeyError(media_id)

    def by_hash(self, sha256: str) -> MediaRecord | None:
        return next((record for record in self.data.records if record.sha256 == sha256), None)

    def upsert(self, record: MediaRecord) -> MediaRecord:
        with self._lock():
            self.data = self._load()
            for index, existing in enumerate(self.data.records):
                if existing.id != record.id:
                    continue
                source_paths = list(dict.fromkeys([*existing.source_paths, *record.source_paths]))
                derivatives = {item.key: item for item in existing.derivatives}
                derivatives.update({item.key: item for item in record.derivatives})
                record = record.model_copy(
                    update={
                        "source_paths": source_paths,
                        "derivatives": list(derivatives.values()),
                    }
                )
                self.data.records[index] = record
                break
            else:
                self.data.records.append(record)
            self._save_unlocked()
        return record
