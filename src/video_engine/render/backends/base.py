"""Backend protocol and execution context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from video_engine.core.schema import JsonValue
from video_engine.render.models import RenderArtifact
from video_engine.render.nodes import NodeKind, RenderNode


class BackendExecution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class RenderBackend(ABC):
    name: str
    version: str
    capabilities: frozenset[NodeKind]

    @property
    @abstractmethod
    def tool_fingerprint(self) -> str:
        raise NotImplementedError

    def can_execute(self, node: RenderNode) -> bool:
        return node.node_type in self.capabilities

    @abstractmethod
    def output_suffix(self, node: RenderNode) -> str:
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        node: RenderNode,
        inputs: tuple[RenderArtifact, ...],
        output_path: Path,
        work_dir: Path,
    ) -> BackendExecution:
        raise NotImplementedError
