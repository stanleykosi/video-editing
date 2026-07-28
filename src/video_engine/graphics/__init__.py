"""Structured motion-graphics components and rendering service."""

from video_engine.graphics.external import (
    ExternalGraphicRequest,
    ExternalGraphicResult,
    ExternalGraphicsBackend,
)
from video_engine.graphics.registry import GraphicsRegistry, builtin_graphics_registry
from video_engine.graphics.service import GraphicsService, PreparedGraphic

__all__ = [
    "ExternalGraphicRequest",
    "ExternalGraphicResult",
    "ExternalGraphicsBackend",
    "GraphicsRegistry",
    "GraphicsService",
    "PreparedGraphic",
    "builtin_graphics_registry",
]
