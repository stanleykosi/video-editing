"""Atomic canonical project persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from video_engine.core.migrations import migrate_project_payload
from video_engine.core.schema import Project
from video_engine.errors import InvalidProjectError, StorageError


class ProjectStore:
    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path

    def load(self) -> tuple[Project, list[str]]:
        try:
            payload = json.loads(self.project_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise TypeError("project root must be a JSON object")
            return migrate_project_payload(payload)
        except ValidationError as exc:
            raise InvalidProjectError(
                "project schema validation failed",
                context={"path": str(self.project_path), "errors": exc.errors()},
            ) from exc
        except (OSError, ValueError, TypeError) as exc:
            raise StorageError(
                "failed to load project",
                context={"path": str(self.project_path), "detail": str(exc)},
            ) from exc

    def save(self, project: Project) -> Path:
        destination = self.project_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = project.model_dump_json(indent=2) + "\n"
        temporary: Path | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
            )
            temporary = Path(temporary_name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except OSError as exc:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise StorageError(
                "failed to save project atomically",
                context={"path": str(destination), "detail": str(exc)},
            ) from exc
        return destination
