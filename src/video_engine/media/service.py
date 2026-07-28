"""Media import, validation, relinking, and cacheable derivative generation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from fcntl import LOCK_EX, LOCK_UN, flock
from pathlib import Path
from typing import Literal, cast

from video_engine.config import EngineConfig
from video_engine.core.schema import JsonValue, MediaReference, StreamSummary
from video_engine.core.time import RationalTime, TimeRange
from video_engine.errors import EngineError, ErrorCode
from video_engine.media.identity import SourceIdentityStore
from video_engine.media.models import (
    DerivedAsset,
    DerivedAssetKind,
    MediaRecord,
    SourceValidation,
)
from video_engine.media.probe import probe_media
from video_engine.media.registry import MediaRegistry
from video_engine.process import CommandRunner
from video_engine.storage.atomic import atomic_write_text

DERIVED_RECIPE_VERSION = 2


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MediaService:
    def __init__(
        self,
        project_root: Path,
        config: EngineConfig,
        runner: CommandRunner | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)
        self.runner = runner or CommandRunner()
        self.registry = MediaRegistry(self.project_root / ".video-engine" / "media.json")
        self.source_identities = SourceIdentityStore(
            self.project_root / ".video-engine" / "source-identities.json"
        )
        self.derived_root = self.config.cache_dir / "derived"
        self.tool_fingerprint = self._tool_fingerprint()

    def _tool_fingerprint(self) -> str:
        probes = []
        for arguments in (("-version",), ("-buildconf",), ("-filters",), ("-encoders",)):
            result = self.runner.run([self.config.ffmpeg_path, *arguments])
            probes.append({"arguments": arguments, "stdout": result.stdout})
        encoded = json.dumps(probes, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"

    def import_media(
        self,
        source: Path,
        *,
        copy_into_store: bool = False,
        deep_vfr: bool = True,
    ) -> MediaRecord:
        source = source.resolve()
        digest = sha256_file(source)
        existing = self.registry.by_hash(digest)
        if existing is not None:
            if source not in existing.source_paths:
                existing.source_paths.append(source)
            if copy_into_store:
                existing.canonical_path = self._publish_store_source(source, digest)
            elif (
                not existing.canonical_path.is_file()
                or sha256_file(existing.canonical_path) != digest
            ):
                existing.canonical_path = source
            return self.registry.upsert(existing)
        media_id = f"media-{digest[:16]}"
        canonical_path = source
        if copy_into_store:
            canonical_path = self._publish_store_source(source, digest)
        probe = probe_media(canonical_path, self.config, self.runner, deep_vfr=deep_vfr)
        record = MediaRecord(
            id=media_id,
            sha256=digest,
            source_paths=[source],
            canonical_path=canonical_path,
            size_bytes=source.stat().st_size,
            imported_at=datetime.now(UTC),
            probe=probe,
        )
        return self.registry.upsert(record)

    def _publish_store_source(self, source: Path, digest: str) -> Path:
        destination = self.project_root / "media" / "sources" / f"{digest}{source.suffix.lower()}"
        return self.source_identities.materialize_verified(
            source,
            destination,
            expected_sha256=digest,
        )

    def _verified_source(self, record: MediaRecord) -> Path:
        actual, _ = self.source_identities.verify(record.canonical_path)
        if actual != record.sha256:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "registered media source changed after import",
                context={
                    "media_id": record.id,
                    "path": str(record.canonical_path),
                    "expected": record.sha256,
                    "actual": actual,
                },
            )
        return self.source_identities.materialize_verified(
            record.canonical_path,
            self.config.cache_dir
            / "source-snapshots"
            / record.sha256[:2]
            / f"{record.sha256}{record.canonical_path.suffix.lower()}",
            expected_sha256=record.sha256,
        )

    @staticmethod
    def to_media_reference(record: MediaRecord) -> MediaReference:
        """Convert an immutable registry identity into the canonical project schema."""

        streams: list[StreamSummary] = []
        for stream in record.probe.streams:
            kind = stream.kind.value
            if kind not in {"video", "audio", "subtitle", "data"}:
                continue
            streams.append(
                StreamSummary(
                    index=stream.index,
                    codec_type=cast(
                        Literal["video", "audio", "subtitle", "data", "attachment"],
                        kind,
                    ),
                    codec_name=stream.codec_name,
                    time_base=stream.time_base,
                    frame_rate=stream.average_frame_rate,
                    sample_rate=stream.sample_rate,
                    channels=stream.channels,
                    channel_layout=stream.channel_layout,
                    width=stream.width,
                    height=stream.height,
                    pixel_format=stream.pixel_format,
                    color_primaries=stream.color_primaries,
                    color_transfer=stream.color_transfer,
                    color_space=stream.color_space,
                )
            )
        available_range = (
            TimeRange(start=RationalTime.zero(), duration=record.probe.duration)
            if record.probe.duration is not None
            else None
        )
        rotation = (
            record.probe.video_streams[0].rotation_degrees if record.probe.video_streams else 0
        )
        return MediaReference(
            id=record.id,
            uri=str(record.canonical_path),
            sha256=record.sha256,
            available_range=available_range,
            streams=streams,
            rotation_degrees=rotation,
            variable_frame_rate=record.probe.variable_frame_rate,
            hdr=record.probe.hdr,
        )

    def inspect(self, media_id_or_path: str | Path, *, deep_vfr: bool = True) -> MediaRecord:
        value = str(media_id_or_path)
        if value.startswith("media-"):
            try:
                return self.registry.get(value)
            except KeyError as exc:
                raise EngineError(
                    ErrorCode.MEDIA_NOT_FOUND,
                    "media id is not registered",
                    context={"media_id": value},
                ) from exc
        return self.import_media(Path(value), deep_vfr=deep_vfr)

    def validate_source(self, media_id: str, *, verify_hash: bool = True) -> SourceValidation:
        record = self.inspect(media_id)
        errors: list[str] = []
        warnings = list(record.probe.warnings)
        if not record.canonical_path.is_file():
            errors.append(f"canonical source is missing: {record.canonical_path}")
        elif verify_hash and sha256_file(record.canonical_path) != record.sha256:
            errors.append("source SHA-256 does not match registry identity")
        if record.probe.duration is not None and record.probe.duration.value <= 0:
            errors.append("source duration is not positive")
        if not record.probe.streams:
            errors.append("source has no readable streams")
        return SourceValidation(
            media_id=media_id,
            valid=not errors,
            errors=errors,
            warnings=warnings,
        )

    def relink(
        self, media_id: str, source: Path, *, allow_different_content: bool = False
    ) -> MediaRecord:
        record = self.inspect(media_id)
        source = source.resolve()
        digest = sha256_file(source)
        if digest != record.sha256 and not allow_different_content:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "relink target has a different SHA-256",
                context={"expected": record.sha256, "actual": digest, "path": str(source)},
            )
        record.canonical_path = source
        if source not in record.source_paths:
            record.source_paths.append(source)
        if allow_different_content and digest != record.sha256:
            record.sha256 = digest
            record.id = f"media-{digest[:16]}"
            record.probe = probe_media(source, self.config, self.runner)
            record.derivatives.clear()
        return self.registry.upsert(record)

    def _derived_key(
        self,
        record: MediaRecord,
        kind: DerivedAssetKind,
        parameters: dict[str, JsonValue],
    ) -> str:
        payload = json.dumps(
            {
                "source_sha256": record.sha256,
                "kind": kind.value,
                "parameters": parameters,
                "tool": self.tool_fingerprint,
                "engine": DERIVED_RECIPE_VERSION,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _cached(self, record: MediaRecord, key: str) -> DerivedAsset | None:
        asset = next((item for item in record.derivatives if item.key == key), None)
        if (
            asset is None
            or not asset.paths
            or asset.tool_fingerprint != self.tool_fingerprint
            or len(asset.sha256) != len(asset.paths)
            or len(asset.size_bytes) != len(asset.paths)
        ):
            return None
        for path, expected_sha, expected_size in zip(
            asset.paths, asset.sha256, asset.size_bytes, strict=True
        ):
            if not path.is_file() or path.stat().st_size != expected_size:
                return None
            if sha256_file(path) != expected_sha:
                return None
        return asset

    @contextmanager
    def _derived_lock(self, key: str) -> Iterator[None]:
        lock_root = self.derived_root / ".locks" / key[:2]
        lock_root.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            lock_root / f"{key}.lock",
            os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        try:
            flock(descriptor, LOCK_EX)
            yield
        finally:
            flock(descriptor, LOCK_UN)
            os.close(descriptor)

    @staticmethod
    def _temporary_output(destination: Path) -> Path:
        return destination.with_name(
            f".{destination.stem}.{uuid.uuid4().hex}.partial{destination.suffix}"
        )

    @staticmethod
    def _publish_file(temporary: Path, destination: Path) -> None:
        if not temporary.is_file() or temporary.stat().st_size <= 0:
            raise EngineError(
                ErrorCode.RENDER_FAILED,
                "derived asset generation produced no usable output",
                context={"path": str(temporary)},
            )
        os.replace(temporary, destination)

    def _register_derived(
        self,
        record: MediaRecord,
        kind: DerivedAssetKind,
        key: str,
        paths: list[Path],
        parameters: dict[str, JsonValue],
    ) -> DerivedAsset:
        asset = DerivedAsset(
            key=key,
            kind=kind,
            paths=paths,
            parameters=parameters,
            created_at=datetime.now(UTC),
            tool_fingerprint=self.tool_fingerprint,
            sha256=[sha256_file(path) for path in paths],
            size_bytes=[path.stat().st_size for path in paths],
        )
        record.derivatives = [item for item in record.derivatives if item.key != key]
        record.derivatives.append(asset)
        self.registry.upsert(record)
        return asset

    def proxy(
        self,
        media_id: str,
        *,
        width: int = 1280,
        height: int = 720,
        crf: int = 28,
    ) -> DerivedAsset:
        record = self.inspect(media_id)
        parameters: dict[str, JsonValue] = {"width": width, "height": height, "crf": crf}
        key = self._derived_key(record, DerivedAssetKind.PROXY, parameters)
        with self._derived_lock(key):
            record = self.registry.refresh().get(record.id)
            if cached := self._cached(record, key):
                return cached
            source = self._verified_source(record)
            destination = self.derived_root / record.sha256 / key / "proxy.mp4"
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._temporary_output(destination)
            try:
                self.runner.run(
                    [
                        self.config.ffmpeg_path,
                        "-y",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        source,
                        "-map",
                        "0:v:0",
                        "-map",
                        "0:a:0?",
                        "-vf",
                        f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        str(crf),
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "128k",
                        "-ar",
                        "48000",
                        "-movflags",
                        "+faststart",
                        temporary,
                    ]
                )
                self._publish_file(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
            return self._register_derived(
                record, DerivedAssetKind.PROXY, key, [destination], parameters
            )

    def thumbnails(
        self,
        media_id: str,
        *,
        count: int = 12,
        width: int = 320,
    ) -> DerivedAsset:
        if count <= 0 or width <= 0:
            raise ValueError("thumbnail count and width must be positive")
        record = self.inspect(media_id)
        parameters: dict[str, JsonValue] = {"count": count, "width": width, "format": "jpg"}
        key = self._derived_key(record, DerivedAssetKind.THUMBNAILS, parameters)
        with self._derived_lock(key):
            record = self.registry.refresh().get(record.id)
            if cached := self._cached(record, key):
                return cached
            source = self._verified_source(record)
            directory = self.derived_root / record.sha256 / key
            directory.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=f".{key}.stage-", dir=directory.parent))
            duration = (
                record.probe.duration.seconds if record.probe.duration is not None else float(count)
            )
            interval = max(duration / count, 0.001)
            pattern = stage / "thumbnail_%04d.jpg"
            try:
                self.runner.run(
                    [
                        self.config.ffmpeg_path,
                        "-y",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        source,
                        "-vf",
                        f"fps=1/{interval:.9f},scale={width}:-2",
                        "-frames:v",
                        str(count),
                        pattern,
                    ]
                )
                staged_paths = sorted(stage.glob("thumbnail_*.jpg"))
                if not staged_paths:
                    raise EngineError(ErrorCode.RENDER_FAILED, "FFmpeg generated no thumbnails")
                if directory.exists():
                    shutil.rmtree(directory)
                os.replace(stage, directory)
            finally:
                if stage.exists():
                    shutil.rmtree(stage)
            paths = sorted(directory.glob("thumbnail_*.jpg"))
            return self._register_derived(
                record, DerivedAssetKind.THUMBNAILS, key, paths, parameters
            )

    def waveform(
        self,
        media_id: str,
        *,
        width: int = 1600,
        height: int = 320,
    ) -> DerivedAsset:
        record = self.inspect(media_id)
        if not record.probe.audio_streams:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "waveform generation requires an audio stream",
                context={"media_id": media_id},
            )
        parameters: dict[str, JsonValue] = {"width": width, "height": height, "mode": "cline"}
        key = self._derived_key(record, DerivedAssetKind.WAVEFORM, parameters)
        with self._derived_lock(key):
            record = self.registry.refresh().get(record.id)
            if cached := self._cached(record, key):
                return cached
            source = self._verified_source(record)
            directory = self.derived_root / record.sha256 / key
            directory.mkdir(parents=True, exist_ok=True)
            image = directory / "waveform.png"
            temporary_image = self._temporary_output(image)
            metadata = directory / "waveform.json"
            try:
                self.runner.run(
                    [
                        self.config.ffmpeg_path,
                        "-y",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        source,
                        "-filter_complex",
                        f"aformat=channel_layouts=mono,showwavespic=s={width}x{height}:colors=white:scale=sqrt",
                        "-frames:v",
                        "1",
                        temporary_image,
                    ]
                )
                self._publish_file(temporary_image, image)
            finally:
                temporary_image.unlink(missing_ok=True)
            atomic_write_text(
                metadata,
                json.dumps(
                    {
                        "media_id": media_id,
                        "sha256": record.sha256,
                        "width": width,
                        "height": height,
                    },
                    indent=2,
                )
                + "\n",
            )
            return self._register_derived(
                record, DerivedAssetKind.WAVEFORM, key, [image, metadata], parameters
            )

    def conform(
        self,
        media_id: str,
        *,
        width: int,
        height: int,
        frame_rate_numerator: int,
        frame_rate_denominator: int = 1,
        sample_rate: int = 48_000,
        hdr_to_sdr: bool = True,
    ) -> DerivedAsset:
        record = self.inspect(media_id)
        parameters: dict[str, JsonValue] = {
            "width": width,
            "height": height,
            "frame_rate_numerator": frame_rate_numerator,
            "frame_rate_denominator": frame_rate_denominator,
            "sample_rate": sample_rate,
            "hdr_to_sdr": hdr_to_sdr,
        }
        key = self._derived_key(record, DerivedAssetKind.CONFORMED, parameters)
        with self._derived_lock(key):
            record = self.registry.refresh().get(record.id)
            if cached := self._cached(record, key):
                return cached
            source = self._verified_source(record)
            destination = self.derived_root / record.sha256 / key / "conformed.mkv"
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._temporary_output(destination)
            video_filters: list[str] = []
            if hdr_to_sdr and record.probe.hdr:
                video_filters.extend(
                    [
                        "zscale=t=linear:npl=100",
                        "format=gbrpf32le",
                        "zscale=p=bt709",
                        "tonemap=tonemap=hable:desat=0",
                        "zscale=t=bt709:m=bt709:r=tv",
                    ]
                )
            video_filters.extend(
                [
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2",
                    "setsar=1",
                    f"fps={frame_rate_numerator}/{frame_rate_denominator}",
                    "format=yuv420p",
                ]
            )
            try:
                self.runner.run(
                    [
                        self.config.ffmpeg_path,
                        "-y",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        source,
                        "-map",
                        "0:v:0",
                        "-map",
                        "0:a:0?",
                        "-vf",
                        ",".join(video_filters),
                        "-c:v",
                        "ffv1",
                        "-level",
                        "3",
                        "-c:a",
                        "pcm_s24le",
                        "-ar",
                        str(sample_rate),
                        temporary,
                    ]
                )
                self._publish_file(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
            return self._register_derived(
                record, DerivedAssetKind.CONFORMED, key, [destination], parameters
            )

    def looped_conform(
        self,
        media_id: str,
        *,
        duration: RationalTime,
        frame_rate_numerator: int,
        frame_rate_denominator: int = 1,
    ) -> DerivedAsset:
        """Create a frame-conformed, silent video long enough for an authored loop."""
        if duration.value <= 0:
            raise EngineError(ErrorCode.MEDIA_INVALID, "looped conform duration must be positive")
        record = self.inspect(media_id)
        if not record.probe.video_streams:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "looped conform requires a video stream",
                context={"media_id": media_id},
            )
        parameters: dict[str, JsonValue] = {
            "recipe": "looped-video-v1",
            "duration": duration.model_dump(mode="json"),
            "frame_rate_numerator": frame_rate_numerator,
            "frame_rate_denominator": frame_rate_denominator,
        }
        key = self._derived_key(record, DerivedAssetKind.CONFORMED, parameters)
        with self._derived_lock(key):
            record = self.registry.refresh().get(record.id)
            if cached := self._cached(record, key):
                return cached
            source = self._verified_source(record)
            destination = self.derived_root / record.sha256 / key / "looped.mkv"
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._temporary_output(destination)
            try:
                self.runner.run(
                    [
                        self.config.ffmpeg_path,
                        "-y",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-stream_loop",
                        "-1",
                        "-i",
                        source,
                        "-t",
                        f"{duration.seconds:.12f}",
                        "-map",
                        "0:v:0",
                        "-an",
                        "-vf",
                        f"fps={frame_rate_numerator}/{frame_rate_denominator}",
                        "-c:v",
                        "ffv1",
                        "-level",
                        "3",
                        temporary,
                    ]
                )
                self._publish_file(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
            return self._register_derived(
                record, DerivedAssetKind.CONFORMED, key, [destination], parameters
            )
