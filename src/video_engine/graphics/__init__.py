"""Structured motion-graphics components and rendering service."""

from video_engine.graphics.external import (
    ExternalGraphicRequest,
    ExternalGraphicResult,
    ExternalGraphicsBackend,
)
from video_engine.graphics.registry import GraphicsRegistry, builtin_graphics_registry

__all__ = [
    "ExternalGraphicRequest",
    "ExternalGraphicResult",
    "ExternalGraphicsBackend",
    "GraphicsRegistry",
    "builtin_graphics_registry",
]
