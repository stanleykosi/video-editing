"""Tracking backend registry and deterministic manual backend."""

from __future__ import annotations

from abc import ABC, abstractmethod

from video_engine.errors import EngineError, ErrorCode
from video_engine.visual.models import TrackingRequest, TrackingResult


class TrackingBackend(ABC):
    name: str
    version: str

    @abstractmethod
    def track(self, request: TrackingRequest) -> TrackingResult:
        raise NotImplementedError


class ManualTrackingBackend(TrackingBackend):
    name = "manual"
    version = "1.0.0"

    def track(self, request: TrackingRequest) -> TrackingResult:
        observations = tuple(
            sorted(request.manual_observations, key=lambda item: (item.time, item.subject_id))
        )
        if not observations:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "manual tracking requires at least one observation",
                context={"request_id": request.id},
            )
        unknown_subjects = (
            sorted({item.subject_id for item in observations} - set(request.subject_ids))
            if request.subject_ids
            else []
        )
        if unknown_subjects:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "manual observations reference unrequested subjects",
                context={"request_id": request.id, "subject_ids": unknown_subjects},
            )
        return TrackingResult(
            id=f"tracking-{request.id}",
            request_id=request.id,
            media_reference_id=request.media_reference_id,
            backend=self.name,
            backend_version=self.version,
            source_range=request.source_range,
            observations=observations,
        )


class TrackingBackendRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, TrackingBackend] = {}

    def register(self, backend: TrackingBackend) -> None:
        if backend.name in self._backends:
            raise ValueError(f"tracking backend {backend.name!r} is already registered")
        self._backends[backend.name] = backend

    def get(self, name: str) -> TrackingBackend:
        try:
            return self._backends[name]
        except KeyError as exc:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "tracking backend is unavailable",
                context={"backend": name, "available": sorted(self._backends)},
            ) from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._backends))


def builtin_tracking_registry() -> TrackingBackendRegistry:
    registry = TrackingBackendRegistry()
    registry.register(ManualTrackingBackend())
    return registry
