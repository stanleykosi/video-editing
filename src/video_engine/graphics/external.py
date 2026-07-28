"""Optional external graphics backend contracts for trusted tool integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from video_engine.core.schema import JsonValue
from video_engine.core.time import FrameRate, TimeRange


class ExternalGraphicRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    backend: Literal["blender", "manim"]
    component_id: str = Field(min_length=1)
    source_path: Path
    output_path: Path
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_rate: FrameRate
    timeline_range: TimeRange
    properties: dict[str, JsonValue] = Field(default_factory=dict)
    transparent: bool = True


class ExternalGraphicResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output_path: Path
    backend: Literal["blender", "manim"]
    tool_fingerprint: str
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class ExternalGraphicsBackend(ABC):
    """Optional backend interface; implementations are registered explicitly."""

    name: Literal["blender", "manim"]

    @property
    @abstractmethod
    def tool_fingerprint(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def render(self, request: ExternalGraphicRequest) -> ExternalGraphicResult:
        raise NotImplementedError
