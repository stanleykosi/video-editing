"""Managed temporary workspaces with deterministic cleanup behavior."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


class TemporaryWorkspace:
    def __init__(
        self,
        *,
        root: Path | None = None,
        prefix: str = "video-engine-",
        keep: bool = False,
    ) -> None:
        self.root = root
        self.prefix = prefix
        self.keep = keep
        self.path: Path | None = None

    def __enter__(self) -> Path:
        if self.root is not None:
            self.root.mkdir(parents=True, exist_ok=True)
        self.path = Path(tempfile.mkdtemp(prefix=self.prefix, dir=self.root))
        return self.path

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.path is not None and not self.keep:
            shutil.rmtree(self.path, ignore_errors=True)
