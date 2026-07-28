"""Canonical schema-version migration registry."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from video_engine.core.schema import CURRENT_SCHEMA_VERSION, Project
from video_engine.errors import EngineError, ErrorCode

Migration = Callable[[dict[str, Any]], dict[str, Any]]


def _integer_v1_to_semver(payload: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(payload)
    migrated["schema_version"] = "1.0.0"
    return migrated


def _v1_0_to_v1_1(payload: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(payload)
    migrated["schema_version"] = "1.1.0"
    migrated.setdefault("sequence_versions", [])
    return migrated


def _v1_1_to_v1_2(payload: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(payload)
    migrated["schema_version"] = CURRENT_SCHEMA_VERSION
    return migrated


MIGRATIONS: dict[str | int, tuple[str, Migration]] = {
    1: ("1.0.0", _integer_v1_to_semver),
    "1": ("1.0.0", _integer_v1_to_semver),
    "1.0.0": ("1.1.0", _v1_0_to_v1_1),
    "1.1.0": (CURRENT_SCHEMA_VERSION, _v1_1_to_v1_2),
}


def migrate_project_payload(payload: dict[str, Any]) -> tuple[Project, list[str]]:
    working = copy.deepcopy(payload)
    applied: list[str] = []
    version: str | int | None = working.get("schema_version")
    if version is None:
        raise EngineError(
            ErrorCode.MIGRATION,
            "canonical project payload has no schema_version",
        )
    seen: set[str | int] = set()
    while version != CURRENT_SCHEMA_VERSION:
        if version is None:
            raise EngineError(
                ErrorCode.MIGRATION,
                "schema migration produced no schema_version",
            )
        if version in seen:
            raise EngineError(
                ErrorCode.MIGRATION,
                "schema migration cycle detected",
                context={"schema_version": version},
            )
        seen.add(version)
        step = MIGRATIONS.get(version)
        if step is None:
            raise EngineError(
                ErrorCode.MIGRATION,
                "unsupported project schema version",
                context={"schema_version": version, "current": CURRENT_SCHEMA_VERSION},
            )
        target, migration = step
        working = migration(working)
        applied.append(f"{version}->{target}")
        version = working.get("schema_version")
    return Project.model_validate(working), applied
