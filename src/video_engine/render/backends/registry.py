"""Backend registration and graph capability resolution."""

from __future__ import annotations

from dataclasses import dataclass

from video_engine.errors import EngineError, ErrorCode
from video_engine.render.backends.base import RenderBackend
from video_engine.render.graph import RenderGraph


@dataclass(frozen=True, slots=True)
class BackendPlan:
    by_node_id: dict[str, RenderBackend]

    @property
    def backends(self) -> tuple[RenderBackend, ...]:
        return tuple(
            sorted(
                {backend.name: backend for backend in self.by_node_id.values()}.values(),
                key=lambda backend: backend.name,
            )
        )

    @property
    def name(self) -> str:
        return "+".join(backend.name for backend in self.backends)

    @property
    def version(self) -> str:
        return "+".join(f"{backend.name}:{backend.version}" for backend in self.backends)

    @property
    def tool_fingerprints(self) -> dict[str, str]:
        return {backend.name: backend.tool_fingerprint for backend in self.backends}


class BackendRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, RenderBackend] = {}

    def register(self, backend: RenderBackend, *, replace: bool = False) -> None:
        if backend.name in self._backends and not replace:
            raise EngineError(
                ErrorCode.CONFIGURATION,
                "render backend is already registered",
                context={"backend": backend.name},
            )
        self._backends[backend.name] = backend

    def get(self, name: str) -> RenderBackend:
        try:
            return self._backends[name]
        except KeyError as exc:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "render backend is not registered",
                context={"backend": name, "available": sorted(self._backends)},
            ) from exc

    def resolve(self, graph: RenderGraph, name: str) -> RenderBackend:
        backend = self.get(name)
        unsupported = [
            {"node_id": node.id, "node_type": node.node_type.value}
            for node in graph.nodes
            if not backend.can_execute(node)
        ]
        if unsupported:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "backend cannot execute every reachable render node",
                context={"backend": name, "unsupported": unsupported},
            )
        return backend

    def plan(self, graph: RenderGraph, preferred: str) -> BackendPlan:
        preferred_backend = self.get(preferred)
        candidates = [
            preferred_backend,
            *(backend for name, backend in sorted(self._backends.items()) if name != preferred),
        ]
        by_node_id: dict[str, RenderBackend] = {}
        for node in graph.nodes:
            selected = next((backend for backend in candidates if backend.can_execute(node)), None)
            if selected is None:
                raise EngineError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "no registered backend can execute a render node",
                    context={
                        "node_id": node.id,
                        "node_type": node.node_type.value,
                        "preferred": preferred,
                        "available": sorted(self._backends),
                    },
                )
            by_node_id[node.id] = selected
        return BackendPlan(by_node_id=by_node_id)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._backends))
