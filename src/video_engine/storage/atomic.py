"""Small atomic persistence primitives for engine reports and interchange files."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from video_engine.errors import StorageError


def atomic_write_text(path: Path, content: str) -> Path:
    destination = path.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise StorageError(
            "failed to write text atomically",
            context={"path": str(destination), "detail": str(exc)},
        ) from exc
    return destination
