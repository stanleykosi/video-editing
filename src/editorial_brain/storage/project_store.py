"""Load/save strict Brain projects and plans."""

from __future__ import annotations

from pathlib import Path

from editorial_brain.core.models import EditorialPlan, EditorialProject
from editorial_brain.storage.cache import _atomic_write


class EditorialProjectStore:
    def save_project(self, path: Path, project: EditorialProject) -> Path:
        path = path.resolve()
        _atomic_write(path, project.model_dump_json(indent=2).encode("utf-8"))
        return path

    def load_project(self, path: Path) -> EditorialProject:
        return EditorialProject.model_validate_json(path.resolve().read_text(encoding="utf-8"))

    def save_plan(self, path: Path, plan: EditorialPlan) -> Path:
        path = path.resolve()
        _atomic_write(path, plan.model_dump_json(indent=2).encode("utf-8"))
        return path

    def load_plan(self, path: Path) -> EditorialPlan:
        return EditorialPlan.model_validate_json(path.resolve().read_text(encoding="utf-8"))
