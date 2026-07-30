"""Stable Editorial Brain errors."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class EditorialErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    INVALID_EVIDENCE = "invalid_evidence"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_FAILED = "provider_failed"
    CACHE_CORRUPT = "cache_corrupt"
    ANALYSIS_FAILED = "analysis_failed"
    NO_VALID_CANDIDATE = "no_valid_candidate"
    PLAN_INVALID = "plan_invalid"
    COMPILE_FAILED = "compile_failed"
    ENGINE_VALIDATION_FAILED = "engine_validation_failed"


class EditorialBrainError(Exception):
    def __init__(
        self,
        code: EditorialErrorCode,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context or {}

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code.value, "message": self.message, "context": self.context}
