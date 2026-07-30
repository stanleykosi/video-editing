"""Canonical Project compilation through the transactional engine surface."""

from pathlib import Path

from editorial_brain.compile.patch import compile_patch
from editorial_brain.compile.validation import apply_and_validate, validate_plan_sources
from editorial_brain.core.models import EditorialPlan
from video_engine.api import Project


def compile_project(project_root: Path, project: Project, plan: EditorialPlan) -> Project:
    validate_plan_sources(project, plan)
    patch, _ = compile_patch(project, plan)
    return apply_and_validate(project_root, project, patch)
