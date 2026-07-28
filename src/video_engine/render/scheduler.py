"""Dependency-aware parallel render-node scheduler."""

from __future__ import annotations

import hashlib
import re
import time
from collections import defaultdict, deque
from collections.abc import Mapping
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict

from video_engine.errors import EngineError, ErrorCode
from video_engine.render.backends.base import RenderBackend
from video_engine.render.cache import RenderCache, cache_key_for_node, sha256_file
from video_engine.render.graph import RenderGraph
from video_engine.render.models import NodeExecutionRecord, RenderArtifact
from video_engine.render.nodes import RenderNode


class SchedulerResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifacts: dict[str, RenderArtifact]
    records: tuple[NodeExecutionRecord, ...]


class _NodeOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact: RenderArtifact
    record: NodeExecutionRecord


class RenderScheduler:
    def __init__(
        self,
        backend: RenderBackend | Mapping[str, RenderBackend],
        cache: RenderCache,
        *,
        max_workers: int,
        use_cache: bool = True,
        publish_cache: bool | None = None,
        resume_cache_keys: Mapping[str, str] | None = None,
    ) -> None:
        self._default_backend = backend if isinstance(backend, RenderBackend) else None
        self._backends_by_node = (
            {} if self._default_backend else dict(cast(Mapping[str, RenderBackend], backend))
        )
        self.cache = cache
        self.max_workers = max_workers
        self.use_cache = use_cache
        self.publish_cache = use_cache if publish_cache is None else publish_cache
        self.resume_cache_keys = dict(resume_cache_keys or {})

    def execute(
        self,
        graph: RenderGraph,
        work_dir: Path,
        *,
        targets: tuple[str, ...] | None = None,
    ) -> SchedulerResult:
        work_dir.mkdir(parents=True, exist_ok=True)
        closure = graph.ancestor_closure(targets)
        nodes = graph.node_map()
        position = {node.id: index for index, node in enumerate(graph.nodes)}
        remaining = {
            node_id: sum(1 for input_id in nodes[node_id].inputs if input_id in closure)
            for node_id in closure
        }
        dependents: dict[str, list[str]] = defaultdict(list)
        for node_id in closure:
            for input_id in nodes[node_id].inputs:
                if input_id in closure:
                    dependents[input_id].append(node_id)
        ready = deque(
            sorted(
                (node_id for node_id, count in remaining.items() if count == 0),
                key=lambda node_id: position[node_id],
            )
        )
        artifacts: dict[str, RenderArtifact] = {}
        records: dict[str, NodeExecutionRecord] = {}
        failed_or_skipped: set[str] = set()
        futures: dict[Future[_NodeOutcome], str] = {}

        def finish_dependency(node_id: str) -> None:
            queue = deque([node_id])
            while queue:
                completed = queue.popleft()
                for dependent in sorted(
                    dependents[completed], key=lambda node_id: position[node_id]
                ):
                    remaining[dependent] -= 1
                    if remaining[dependent] != 0:
                        continue
                    if any(input_id in failed_or_skipped for input_id in nodes[dependent].inputs):
                        failed_or_skipped.add(dependent)
                        records[dependent] = self._skipped_record(
                            nodes[dependent], self._backend_for(nodes[dependent])
                        )
                        queue.append(dependent)
                    else:
                        ready.append(dependent)

        with ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="render") as pool:
            while ready or futures:
                while ready and len(futures) < self.max_workers:
                    node_id = ready.popleft()
                    node = nodes[node_id]
                    input_artifacts = tuple(artifacts[input_id] for input_id in node.inputs)
                    future = pool.submit(
                        self._execute_node,
                        node,
                        input_artifacts,
                        work_dir / self._work_directory_name(node_id),
                    )
                    futures[future] = node_id
                if not futures:
                    continue
                done, _ = wait(tuple(futures), return_when=FIRST_COMPLETED)
                for future in done:
                    node_id = futures.pop(future)
                    try:
                        outcome = future.result()
                    except Exception as exc:
                        failed_or_skipped.add(node_id)
                        records[node_id] = self._failed_record(
                            nodes[node_id], exc, self._backend_for(nodes[node_id])
                        )
                    else:
                        artifacts[node_id] = outcome.artifact
                        records[node_id] = outcome.record
                    finish_dependency(node_id)

        requested = targets or tuple(graph.outputs.values())
        missing = [node_id for node_id in requested if node_id not in artifacts]
        ordered_records = tuple(
            records[node_id] for node_id in graph.topological_order(tuple(requested))
        )
        if missing:
            failures = [
                record.model_dump(mode="json")
                for record in ordered_records
                if record.status in {"failed", "skipped"}
            ]
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "render graph execution failed",
                context={
                    "missing_targets": missing,
                    "failures": failures,
                    "records": [record.model_dump(mode="json") for record in ordered_records],
                },
            )
        return SchedulerResult(artifacts=artifacts, records=ordered_records)

    def _execute_node(
        self,
        node: RenderNode,
        inputs: tuple[RenderArtifact, ...],
        work_dir: Path,
    ) -> _NodeOutcome:
        started_at = datetime.now(UTC)
        started = time.monotonic()
        backend = self._backend_for(node)
        cache_key = cache_key_for_node(
            node,
            tuple(item.cache_key for item in inputs),
            backend_name=backend.name,
            backend_version=backend.version,
            tool_fingerprint=backend.tool_fingerprint,
        )
        if node.cacheable and (self.use_cache or self.publish_cache):
            with self.cache.lock(cache_key):
                resume_match = self.resume_cache_keys.get(node.id) == cache_key
                cached = (
                    self.cache.lookup(node, cache_key) if self.use_cache or resume_match else None
                )
                if cached is not None:
                    return _NodeOutcome(
                        artifact=cached,
                        record=NodeExecutionRecord(
                            node_id=node.id,
                            node_type=node.node_type,
                            backend=backend.name,
                            backend_version=backend.version,
                            cache_key=cache_key,
                            status="cached",
                            cached=True,
                            started_at=started_at,
                            duration_seconds=time.monotonic() - started,
                            artifact_path=cached.path,
                            artifact_metadata=cached.metadata,
                        ),
                    )
                return self._execute_backend(
                    node,
                    inputs,
                    work_dir,
                    cache_key,
                    started_at,
                    started,
                    backend,
                    publish=self.publish_cache,
                )
        return self._execute_backend(
            node,
            inputs,
            work_dir,
            cache_key,
            started_at,
            started,
            backend,
            publish=False,
        )

    def _execute_backend(
        self,
        node: RenderNode,
        inputs: tuple[RenderArtifact, ...],
        work_dir: Path,
        cache_key: str,
        started_at: datetime,
        started: float,
        backend: RenderBackend,
        *,
        publish: bool,
    ) -> _NodeOutcome:
        work_dir.mkdir(parents=True, exist_ok=True)
        suffix = backend.output_suffix(node)
        if re.fullmatch(r"\.[A-Za-z0-9]{1,12}", suffix) is None:
            raise EngineError(
                ErrorCode.STORAGE,
                "render backend returned an unsafe artifact suffix",
                context={"node_id": node.id, "suffix": suffix},
            )
        output_path = work_dir / f"output{suffix}"
        execution = backend.execute(node, inputs, output_path, work_dir)
        if not execution.path.is_file():
            raise FileNotFoundError(execution.path)
        if publish:
            artifact = self.cache.publish(
                node,
                cache_key,
                execution.path,
                suffix=suffix,
                metadata=execution.metadata,
                assume_locked=True,
            )
        else:
            artifact = RenderArtifact(
                node_id=node.id,
                cache_key=cache_key,
                artifact_type=node.artifact_type,
                path=execution.path,
                cached=False,
                size_bytes=execution.path.stat().st_size,
                sha256=sha256_file(execution.path),
                metadata=execution.metadata,
            )
        return _NodeOutcome(
            artifact=artifact,
            record=NodeExecutionRecord(
                node_id=node.id,
                node_type=node.node_type,
                backend=backend.name,
                backend_version=backend.version,
                cache_key=cache_key,
                status="succeeded",
                cached=False,
                started_at=started_at,
                duration_seconds=time.monotonic() - started,
                artifact_path=artifact.path,
                artifact_metadata=artifact.metadata,
            ),
        )

    def _backend_for(self, node: RenderNode) -> RenderBackend:
        if self._default_backend is not None:
            return self._default_backend
        try:
            return self._backends_by_node[node.id]
        except KeyError as exc:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "render plan has no backend for node",
                context={"node_id": node.id, "node_type": node.node_type.value},
            ) from exc

    @staticmethod
    def _work_directory_name(node_id: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", node_id).strip(".-")[:40] or "node"
        digest = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:16]
        return f"{slug}-{digest}"

    @staticmethod
    def _failed_record(
        node: RenderNode, exc: Exception, backend: RenderBackend
    ) -> NodeExecutionRecord:
        context = exc.to_dict()["error"] if isinstance(exc, EngineError) else {"message": str(exc)}
        return NodeExecutionRecord(
            node_id=node.id,
            node_type=node.node_type,
            backend=backend.name,
            backend_version=backend.version,
            cache_key="",
            status="failed",
            cached=False,
            started_at=datetime.now(UTC),
            duration_seconds=0,
            error=context,
        )

    @staticmethod
    def _skipped_record(node: RenderNode, backend: RenderBackend) -> NodeExecutionRecord:
        return NodeExecutionRecord(
            node_id=node.id,
            node_type=node.node_type,
            backend=backend.name,
            backend_version=backend.version,
            cache_key="",
            status="skipped",
            cached=False,
            started_at=datetime.now(UTC),
            duration_seconds=0,
            error={"message": "dependency failed"},
        )
