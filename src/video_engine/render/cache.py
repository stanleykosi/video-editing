"""Content-addressed render-node cache with checksum validation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from fcntl import LOCK_EX, LOCK_UN, flock
from pathlib import Path
from typing import Any

from video_engine.render.models import RenderArtifact
from video_engine.render.nodes import (
    CaptionNode,
    DecodeNode,
    GradeNode,
    MotionGraphicNode,
    RenderNode,
)

COMPILER_FINGERPRINT = "video-engine-render-14"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset_paths(node: RenderNode) -> tuple[Path, ...]:
    values: list[str] = []
    if isinstance(node, GradeNode) and node.lut_path:
        values.append(node.lut_path)
    if isinstance(node, CaptionNode) and node.subtitle_path:
        values.append(node.subtitle_path)
    if isinstance(node, CaptionNode):
        values.extend(node.font_paths)
    if isinstance(node, MotionGraphicNode):
        values.extend(str(asset.source_path) for asset in node.assets)
    return tuple(Path(value) for value in values)


def cache_key_for_node(
    node: RenderNode,
    input_keys: tuple[str, ...],
    *,
    backend_name: str,
    backend_version: str,
    tool_fingerprint: str,
) -> str:
    node_payload = node.model_dump(mode="json")
    node_payload.pop("id", None)
    node_payload.pop("inputs", None)
    for index, layer in enumerate(node_payload.get("layers", [])):
        layer["input_id"] = f"$input:{index}"
    for index, mix_input in enumerate(node_payload.get("mix_inputs", [])):
        mix_input["input_id"] = f"$input:{index}"
    if isinstance(node, MotionGraphicNode):
        node_payload["assets"] = [
            {
                "id": asset.id,
                "media_type": asset.media_type,
                "staged_extension": Path(asset.staged_name).suffix.lower(),
            }
            for asset in node.assets
        ]
    referenced_assets: list[dict[str, str | None]] = []
    for path in _asset_paths(node):
        checksum = sha256_file(path) if path.is_file() else None
        referenced_assets.append(
            {
                "identity": checksum or str(path.resolve()),
                "sha256": checksum,
            }
        )
    for field in (
        "lut_path",
        "mask_path",
        "subtitle_path",
        "font_paths",
    ):
        node_payload.pop(field, None)
    if isinstance(node, DecodeNode):
        source = Path(node.source_uri)
        checksum = node.source_sha256
        if checksum is None and source.is_file():
            checksum = sha256_file(source)
        node_payload.pop("source_uri", None)
        node_payload.pop("snapshot_uri", None)
        node_payload["source_identity"] = checksum or str(source.resolve())
    payload = {
        "compiler": COMPILER_FINGERPRINT,
        "backend": backend_name,
        "backend_version": backend_version,
        "tool_fingerprint": tool_fingerprint,
        "node": node_payload,
        "input_keys": input_keys,
        "referenced_assets": referenced_assets,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class RenderCache:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _entry_dir(self, cache_key: str) -> Path:
        if len(cache_key) != 64 or any(
            character not in "0123456789abcdef" for character in cache_key
        ):
            raise ValueError("render cache keys must be 64 lowercase hexadecimal characters")
        return self.root / cache_key[:2] / cache_key

    @contextmanager
    def lock(self, cache_key: str) -> Iterator[None]:
        self._entry_dir(cache_key)
        lock_root = self.root / ".locks" / cache_key[:2]
        lock_root.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            lock_root / f"{cache_key}.lock",
            os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        try:
            flock(descriptor, LOCK_EX)
            yield
        finally:
            flock(descriptor, LOCK_UN)
            os.close(descriptor)

    def lookup(self, node: RenderNode, cache_key: str) -> RenderArtifact | None:
        entry = self._entry_dir(cache_key)
        metadata_path = entry / "metadata.json"
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            artifact_name = str(payload["artifact_name"])
            if Path(artifact_name).name != artifact_name:
                return None
            artifact_path = entry / artifact_name
            if artifact_path.resolve().parent != entry.resolve():
                return None
            if not artifact_path.is_file():
                return None
            expected_size = int(payload["size_bytes"])
            expected_sha = str(payload["sha256"])
            if artifact_path.stat().st_size != expected_size:
                return None
            if sha256_file(artifact_path) != expected_sha:
                return None
            return RenderArtifact(
                node_id=node.id,
                cache_key=cache_key,
                artifact_type=node.artifact_type,
                path=artifact_path,
                cached=True,
                size_bytes=expected_size,
                sha256=expected_sha,
                metadata=payload.get("metadata", {}),
            )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def publish(
        self,
        node: RenderNode,
        cache_key: str,
        source: Path,
        *,
        suffix: str,
        metadata: dict[str, Any] | None = None,
        assume_locked: bool = False,
    ) -> RenderArtifact:
        if not assume_locked:
            with self.lock(cache_key):
                return self.publish(
                    node,
                    cache_key,
                    source,
                    suffix=suffix,
                    metadata=metadata,
                    assume_locked=True,
                )
        if not source.is_file():
            raise FileNotFoundError(source)
        entry = self._entry_dir(cache_key)
        entry.parent.mkdir(parents=True, exist_ok=True)
        existing = self.lookup(node, cache_key)
        if existing is not None:
            return existing
        if entry.exists():
            shutil.rmtree(entry, ignore_errors=True)
        temporary = Path(tempfile.mkdtemp(prefix=f".{cache_key}.", dir=entry.parent))
        artifact_name = f"artifact{suffix}"
        temporary_artifact = temporary / artifact_name
        try:
            shutil.copy2(source, temporary_artifact)
            with temporary_artifact.open("rb") as handle:
                os.fsync(handle.fileno())
            checksum = sha256_file(temporary_artifact)
            size = temporary_artifact.stat().st_size
            payload = {
                "cache_key": cache_key,
                "artifact_name": artifact_name,
                "sha256": checksum,
                "size_bytes": size,
                "metadata": metadata or {},
            }
            metadata_file = temporary / "metadata.json"
            with metadata_file.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.replace(temporary, entry)
            except FileExistsError:
                shutil.rmtree(temporary, ignore_errors=True)
            directory_descriptor = os.open(entry.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
            artifact = self.lookup(node, cache_key)
            if artifact is None:
                raise OSError(f"published cache entry {entry} failed validation")
            return artifact.model_copy(update={"cached": False})
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
