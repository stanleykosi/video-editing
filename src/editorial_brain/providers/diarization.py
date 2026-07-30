"""Diarization provider contracts."""

from editorial_brain.providers.base import (
    DiarizationOutput,
    DiarizationProvider,
    DiarizationRequest,
    ProviderResult,
)

__all__ = ["DiarizationOutput", "DiarizationProvider", "DiarizationRequest", "ProviderResult"]
