"""Typed engine failures with stable machine-readable codes."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    CONFIGURATION = "configuration_error"
    DEPENDENCY_MISSING = "dependency_missing"
    EXTERNAL_TOOL = "external_tool_error"
    INVALID_PROJECT = "invalid_project"
    INVALID_TIMELINE = "invalid_timeline"
    INVALID_OPERATION = "invalid_operation"
    MEDIA_NOT_FOUND = "media_not_found"
    MEDIA_INVALID = "media_invalid"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    RENDER_FAILED = "render_failed"
    QC_FAILED = "qc_failed"
    STORAGE = "storage_error"
    MIGRATION = "migration_error"


class EngineError(Exception):
    """Base error carrying a stable code and JSON-compatible context."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "context": self.context,
            }
        }


class ConfigurationError(EngineError):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.CONFIGURATION, message, context=context)


class DependencyError(EngineError):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.DEPENDENCY_MISSING, message, context=context)


class ExternalToolError(EngineError):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.EXTERNAL_TOOL, message, context=context)


class InvalidProjectError(EngineError):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.INVALID_PROJECT, message, context=context)


class InvalidTimelineError(EngineError):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.INVALID_TIMELINE, message, context=context)


class StorageError(EngineError):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.STORAGE, message, context=context)
