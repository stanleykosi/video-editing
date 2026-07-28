"""Durable atomic render-attempt checkpoints backed by cache evidence."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from fcntl import LOCK_EX, LOCK_UN, flock
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from video_engine.core.schema import JsonValue
from video_engine.render.backends.registry import BackendPlan
from video_engine.render.cache import COMPILER_FINGERPRINT
from video_engine.render.compiler import CompiledRender
from video_engine.render.models import NodeExecutionRecord, RenderRequest

CheckpointStatus = Literal["running", "interrupted", "failed", "succeeded"]


class CheckpointAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    status: CheckpointStatus
    started_at: datetime
    completed_at: datetime | None = None
    records: tuple[NodeExecutionRecord, ...] = ()
    failure: dict[str, JsonValue] | None = None
    owner_pid: int | None = Field(default=None, gt=0)
    owner_identity: str | None = None


class CheckpointSectionState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    section_id: str
    video_node_id: str
    audio_node_id: str
    video_status: str | None = None
    audio_status: str | None = None
    video_cache_key: str | None = None
    audio_cache_key: str | None = None


class RenderCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checkpoint_version: str = "1.2.0"
    identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    project_id: str
    project_revision: int = Field(ge=1)
    sequence_id: str
    graph_hash: str
    request_signature: dict[str, JsonValue]
    status: CheckpointStatus
    created_at: datetime
    updated_at: datetime
    attempts: tuple[CheckpointAttempt, ...]
    completed_cache_keys: dict[str, str] = Field(default_factory=dict)
    sections: tuple[CheckpointSectionState, ...] = ()
    output_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


def checkpoint_identity(
    compiled: CompiledRender,
    backend_plan: BackendPlan,
    request: RenderRequest,
    *,
    project_id: str,
    project_revision: int,
) -> tuple[str, dict[str, JsonValue]]:
    signature: dict[str, JsonValue] = {
        "project_id": project_id,
        "project_revision": project_revision,
        "compiler_fingerprint": COMPILER_FINGERPRINT,
        "graph_hash": compiled.graph.graph_hash,
        "delivery_profile": compiled.delivery_profile.model_dump(mode="json"),
        "timeline_range": compiled.timeline_range.model_dump(mode="json"),
        "sections": compiled.section_plan.model_dump(mode="json"),
        "backend": backend_plan.name,
        "backend_version": backend_plan.version,
        "tool_fingerprints": backend_plan.tool_fingerprints,
        "caption_track_ids": (
            list(request.caption_track_ids) if request.caption_track_ids is not None else None
        ),
        "caption_languages": (
            list(request.caption_languages) if request.caption_languages is not None else None
        ),
        "chapter_id": request.chapter_id,
    }
    encoded = json.dumps(signature, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest(), signature


class RenderCheckpointStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, identity: str) -> Path:
        if len(identity) != 64 or any(value not in "0123456789abcdef" for value in identity):
            raise ValueError("checkpoint identity must be a lowercase SHA-256 digest")
        return self.root / identity[:2] / f"{identity}.json"

    @contextmanager
    def _lock(self, identity: str) -> Iterator[None]:
        self.path_for(identity)
        lock_root = self.root / ".locks" / identity[:2]
        lock_root.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            lock_root / f"{identity}.lock",
            os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        try:
            flock(descriptor, LOCK_EX)
            yield
        finally:
            flock(descriptor, LOCK_UN)
            os.close(descriptor)

    def load(self, identity: str) -> RenderCheckpoint | None:
        with self._lock(identity):
            return self._load_unlocked(identity)

    def _load_unlocked(self, identity: str) -> RenderCheckpoint | None:
        path = self.path_for(identity)
        try:
            return RenderCheckpoint.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            quarantine = path.parent / (
                f"{path.stem}.corrupt-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
                f"-{uuid.uuid4().hex}.json"
            )
            with suppress(FileNotFoundError):
                os.replace(path, quarantine)
            return None

    @staticmethod
    def _process_identity(pid: int) -> str | None:
        try:
            boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
            fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
            return f"{boot_id}:{fields[19]}"
        except (OSError, IndexError):
            return None

    @staticmethod
    def _owner_is_alive(attempt: CheckpointAttempt) -> bool:
        if attempt.owner_pid is None:
            return False
        try:
            os.kill(attempt.owner_pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        if attempt.owner_identity is None:
            return True
        return RenderCheckpointStore._process_identity(attempt.owner_pid) == attempt.owner_identity

    def begin(
        self,
        *,
        identity: str,
        signature: dict[str, JsonValue],
        compiled: CompiledRender,
        project_id: str,
        project_revision: int,
        resume: bool,
    ) -> tuple[RenderCheckpoint, str]:
        with self._lock(identity):
            now = datetime.now(UTC)
            existing = self._load_unlocked(identity) if resume else None
            attempts = list(existing.attempts if existing is not None else ())
            for index, attempt in enumerate(attempts):
                if attempt.status == "running" and not self._owner_is_alive(attempt):
                    attempts[index] = attempt.model_copy(
                        update={"status": "interrupted", "completed_at": now}
                    )
            attempt_id = f"attempt-{uuid.uuid4().hex}"
            attempts.append(
                CheckpointAttempt(
                    id=attempt_id,
                    status="running",
                    started_at=now,
                    owner_pid=os.getpid(),
                    owner_identity=self._process_identity(os.getpid()),
                )
            )
            checkpoint = RenderCheckpoint(
                identity=identity,
                project_id=project_id,
                project_revision=project_revision,
                sequence_id=compiled.sequence_id,
                graph_hash=compiled.graph.graph_hash,
                request_signature=signature,
                status="running",
                created_at=existing.created_at if existing is not None else now,
                updated_at=now,
                attempts=tuple(attempts),
                completed_cache_keys=(
                    existing.completed_cache_keys if existing is not None else {}
                ),
                sections=existing.sections if existing is not None else (),
                output_sha256=None,
            )
            self._write_unlocked(checkpoint)
            return checkpoint, attempt_id

    def finish(
        self,
        checkpoint: RenderCheckpoint,
        attempt_id: str,
        compiled: CompiledRender,
        records: tuple[NodeExecutionRecord, ...],
        *,
        status: Literal["failed", "succeeded"],
        output_sha256: str | None = None,
        failure: dict[str, JsonValue] | None = None,
    ) -> RenderCheckpoint:
        with self._lock(checkpoint.identity):
            now = datetime.now(UTC)
            current = self._load_unlocked(checkpoint.identity) or checkpoint
            attempts = list(current.attempts)
            try:
                index = next(
                    index for index, attempt in enumerate(attempts) if attempt.id == attempt_id
                )
            except StopIteration:
                attempts.extend(
                    attempt for attempt in checkpoint.attempts if attempt.id == attempt_id
                )
                index = len(attempts) - 1
            attempts[index] = attempts[index].model_copy(
                update={
                    "status": status,
                    "completed_at": now,
                    "records": records,
                    "failure": failure,
                }
            )
            completed = dict(current.completed_cache_keys)
            record_map = {record.node_id: record for record in records}
            for record in records:
                if record.status in {"succeeded", "cached"} and record.cache_key:
                    completed[record.node_id] = record.cache_key
            prior_sections = {section.section_id: section for section in current.sections}
            sections: list[CheckpointSectionState] = []
            for output in compiled.section_outputs:
                video_record = record_map.get(output.video_node_id)
                audio_record = record_map.get(output.audio_node_id)
                previous = prior_sections.get(output.section.id)
                sections.append(
                    CheckpointSectionState(
                        section_id=output.section.id,
                        video_node_id=output.video_node_id,
                        audio_node_id=output.audio_node_id,
                        video_status=(
                            video_record.status
                            if video_record is not None
                            else previous.video_status if previous is not None else None
                        ),
                        audio_status=(
                            audio_record.status
                            if audio_record is not None
                            else previous.audio_status if previous is not None else None
                        ),
                        video_cache_key=(
                            video_record.cache_key
                            if video_record is not None
                            else previous.video_cache_key if previous is not None else None
                        ),
                        audio_cache_key=(
                            audio_record.cache_key
                            if audio_record is not None
                            else previous.audio_cache_key if previous is not None else None
                        ),
                    )
                )
            finished_attempt = attempts[index]
            concurrent_success = any(
                attempt.id != attempt_id
                and attempt.status == "succeeded"
                and attempt.completed_at is not None
                and attempt.completed_at >= finished_attempt.started_at
                for attempt in attempts
            )
            any_running = any(
                attempt.id != attempt_id and attempt.status == "running" for attempt in attempts
            )
            overall_status: CheckpointStatus = (
                "succeeded"
                if status == "succeeded" or concurrent_success
                else "running" if any_running else "failed"
            )
            result = current.model_copy(
                update={
                    "status": overall_status,
                    "updated_at": now,
                    "attempts": tuple(attempts),
                    "completed_cache_keys": completed,
                    "sections": tuple(sections),
                    "output_sha256": (
                        output_sha256
                        if status == "succeeded"
                        else current.output_sha256 if concurrent_success else None
                    ),
                }
            )
            self._write_unlocked(result)
            return result

    def write(self, checkpoint: RenderCheckpoint) -> Path:
        with self._lock(checkpoint.identity):
            return self._write_unlocked(checkpoint)

    def _write_unlocked(self, checkpoint: RenderCheckpoint) -> Path:
        path = self.path_for(checkpoint.identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(checkpoint.model_dump_json(indent=2))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return path
