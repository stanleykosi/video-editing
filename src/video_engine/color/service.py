"""Public color pipeline and measured correction facade."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from fcntl import LOCK_EX, LOCK_UN, flock
from fractions import Fraction
from functools import cached_property
from pathlib import Path

from video_engine.color.models import (
    AutoGradePolicy,
    ColorMeasurements,
    ColorPipeline,
    CreativeGrade,
    MeasuredAutoGrade,
    TechnicalNormalization,
)
from video_engine.config import EngineConfig
from video_engine.core.schema import ColorSpace, Effect, EffectKind
from video_engine.core.time import RationalTime, TimeRange
from video_engine.errors import EngineError, ErrorCode
from video_engine.media.identity import SourceIdentityStore
from video_engine.process import CommandRunner
from video_engine.storage.atomic import atomic_write_text
from video_engine.temp import TemporaryWorkspace

ANALYZER_VERSION = "signalstats-v3"
MAXIMUM_SAMPLE_COUNT = 256


def _parse_metadata_value(line: str) -> float | None:
    try:
        return float(line.rsplit("=", 1)[1])
    except (IndexError, ValueError):
        return None


class ColorService:
    def __init__(
        self,
        project_root: Path | None = None,
        config: EngineConfig | None = None,
        runner: CommandRunner | None = None,
    ) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self.config = EngineConfig.from_environment(config).materialize(self.project_root)
        self.runner = runner or CommandRunner()
        self.source_identities = SourceIdentityStore(
            self.project_root / ".video-engine" / "source-identities.json"
        )
        self.cache_root = self.config.cache_dir / "color-analysis"

    @cached_property
    def ffmpeg_fingerprint(self) -> str:
        probes: list[str] = []
        for arguments in (("-version",), ("-buildconf",), ("-filters",)):
            probes.append(self.runner.run([self.config.ffmpeg_path, *arguments]).stdout)
        payload = "\0".join(probes)
        first_line = probes[0].splitlines()[0] if probes and probes[0] else "unknown"
        return (
            f"{first_line.strip()};analysis_sha256="
            f"{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"
        )

    @cached_property
    def ffprobe_fingerprint(self) -> str:
        result = self.runner.run([self.config.ffprobe_path, "-version"])
        first_line = result.stdout.splitlines()[0] if result.stdout else "unknown"
        return (
            f"{first_line.strip()};analysis_sha256="
            f"{hashlib.sha256(result.stdout.encode('utf-8')).hexdigest()}"
        )

    @contextmanager
    def _cache_lock(self, key: str) -> Iterator[None]:
        lock_root = self.cache_root / ".locks"
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

    def _probe_duration(self, source: Path) -> RationalTime:
        result = self.runner.run(
            [
                self.config.ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                source,
            ]
        )
        try:
            duration = RationalTime.from_fraction(Fraction(result.stdout.strip()))
        except (ValueError, ZeroDivisionError) as exc:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "color analysis could not determine a positive source duration",
                context={"source": str(source), "ffprobe_output": result.stdout.strip()},
            ) from exc
        if duration.value <= 0:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "color analysis requires a positive source duration",
                context={"source": str(source)},
            )
        return duration

    def _probe_bit_depth(self, source: Path) -> int:
        result = self.runner.run(
            [
                self.config.ffprobe_path,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=pix_fmt,bits_per_raw_sample",
                "-of",
                "json",
                source,
            ]
        )
        try:
            payload = json.loads(result.stdout)
            stream = payload["streams"][0]
            raw_depth = int(stream.get("bits_per_raw_sample") or 0)
            pixel_format = str(stream.get("pix_fmt") or "")
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "color analysis could not determine source pixel depth",
                context={"source": str(source)},
            ) from exc
        if raw_depth >= 8:
            return raw_depth
        for candidate in (16, 14, 12, 10, 9):
            if str(candidate) in pixel_format:
                return candidate
        return 8

    def _cache_key(
        self,
        source_sha256: str,
        source_range: TimeRange,
        sample_count: int,
    ) -> str:
        payload = {
            "analyzer_version": ANALYZER_VERSION,
            "source_sha256": source_sha256,
            "source_range": {
                "start": [
                    source_range.start.fraction.numerator,
                    source_range.start.fraction.denominator,
                ],
                "duration": [
                    source_range.duration.fraction.numerator,
                    source_range.duration.fraction.denominator,
                ],
            },
            "sample_count": sample_count,
            "ffmpeg_fingerprint": self.ffmpeg_fingerprint,
            "ffprobe_fingerprint": self.ffprobe_fingerprint,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _quarantine(path: Path) -> None:
        try:
            os.replace(path, path.with_name(f".{path.name}.corrupt-{uuid.uuid4().hex}"))
        except FileNotFoundError:
            return

    def _cached_measurements(
        self,
        destination: Path,
        *,
        key: str,
        source_sha256: str,
    ) -> ColorMeasurements | None:
        try:
            measurements = ColorMeasurements.model_validate_json(
                destination.read_text(encoding="utf-8")
            )
        except FileNotFoundError:
            return None
        except (OSError, ValueError):
            self._quarantine(destination)
            return None
        if (
            measurements.cache_key != key
            or measurements.source_sha256 != source_sha256
            or measurements.ffmpeg_fingerprint != self.ffmpeg_fingerprint
            or measurements.ffprobe_fingerprint != self.ffprobe_fingerprint
        ):
            self._quarantine(destination)
            return None
        return measurements.model_copy(update={"cache_hit": True})

    def analyze(
        self,
        source: Path,
        *,
        source_range: TimeRange | None = None,
        sample_count: int = 10,
    ) -> ColorMeasurements:
        if not 1 <= sample_count <= MAXIMUM_SAMPLE_COUNT:
            raise EngineError(
                ErrorCode.INVALID_OPERATION,
                "color analysis sample_count must be between 1 and 256",
                context={"sample_count": sample_count},
            )
        source = source.resolve()
        if not source.is_file():
            raise EngineError(
                ErrorCode.MEDIA_NOT_FOUND,
                "color analysis source does not exist",
                context={"source": str(source)},
            )
        source_sha256, _ = self.source_identities.verify(source)
        snapshot = self.source_identities.materialize_verified(
            source,
            self.config.cache_dir
            / "source-snapshots"
            / source_sha256[:2]
            / f"{source_sha256}{source.suffix.lower()}",
            expected_sha256=source_sha256,
        )
        source_duration = self._probe_duration(snapshot) if source_range is None else None
        analyzed_range = source_range or TimeRange(
            start=RationalTime.zero(),
            duration=source_duration or RationalTime.zero(),
        )
        if analyzed_range.start.value < 0 or analyzed_range.duration.value <= 0:
            raise EngineError(
                ErrorCode.INVALID_OPERATION,
                "color analysis range must be nonnegative with positive duration",
                context={"source_range": analyzed_range.model_dump(mode="json")},
            )
        key = self._cache_key(source_sha256, analyzed_range, sample_count)
        destination = self.cache_root / f"{key}.json"
        with self._cache_lock(key):
            cached = self._cached_measurements(
                destination,
                key=key,
                source_sha256=source_sha256,
            )
            if cached is not None:
                return cached

            available_duration = source_duration or self._probe_duration(snapshot)
            if analyzed_range.end > available_duration:
                raise EngineError(
                    ErrorCode.INVALID_OPERATION,
                    "color analysis range exceeds the source duration",
                    context={
                        "source": str(source),
                        "source_range": analyzed_range.model_dump(mode="json"),
                        "available_duration": available_duration.model_dump(mode="json"),
                    },
                )
            storage_bit_depth = self._probe_bit_depth(snapshot)
            with TemporaryWorkspace(
                root=self.config.temp_dir,
                prefix="video-engine-color-",
                keep=self.config.keep_temporary_files,
            ) as workspace:
                lines: list[str] = []
                for index in range(sample_count):
                    offset = analyzed_range.duration * Fraction(
                        (2 * index) + 1,
                        2 * sample_count,
                    )
                    sample_time = analyzed_range.start + offset
                    metadata_path = workspace / f"signalstats-{index:04d}.txt"
                    escaped_metadata = (
                        str(metadata_path)
                        .replace("\\", "\\\\")
                        .replace(":", "\\:")
                        .replace("'", "\\'")
                    )
                    self.runner.run(
                        [
                            self.config.ffmpeg_path,
                            "-y",
                            "-hide_banner",
                            "-nostats",
                            "-ss",
                            f"{float(sample_time.fraction):.12g}",
                            "-i",
                            snapshot,
                            "-frames:v",
                            "1",
                            "-vf",
                            "select=eq(n\\,0),signalstats,"
                            f"metadata=mode=print:file='{escaped_metadata}'",
                            "-an",
                            "-f",
                            "null",
                            "-",
                        ]
                    )
                    try:
                        lines.extend(metadata_path.read_text(encoding="utf-8").splitlines())
                    except OSError as exc:
                        raise EngineError(
                            ErrorCode.MEDIA_INVALID,
                            "FFmpeg color analysis did not produce signal metadata",
                            context={"source": str(source), "sample_index": index},
                        ) from exc

            y_avgs: list[float] = []
            y_mins: list[float] = []
            y_maxs: list[float] = []
            saturation_avgs: list[float] = []
            for line in lines:
                value = _parse_metadata_value(line.strip())
                if value is None:
                    continue
                if "lavfi.signalstats.YAVG" in line:
                    y_avgs.append(value)
                elif "lavfi.signalstats.YMIN" in line:
                    y_mins.append(value)
                elif "lavfi.signalstats.YMAX" in line:
                    y_maxs.append(value)
                elif "lavfi.signalstats.SATAVG" in line:
                    saturation_avgs.append(value)
            if not y_avgs:
                raise EngineError(
                    ErrorCode.MEDIA_INVALID,
                    "FFmpeg color analysis returned no luma samples",
                    context={
                        "source": str(source),
                        "source_range": analyzed_range.model_dump(mode="json"),
                    },
                )
            maximum_value = (2**storage_bit_depth) - 1
            y_mean = (sum(y_avgs) / len(y_avgs)) / maximum_value
            y_range = (
                ((sum(y_maxs) / len(y_maxs)) - (sum(y_mins) / len(y_mins))) / maximum_value
                if y_maxs and y_mins
                else 0.7
            )
            saturation_mean = (
                (sum(saturation_avgs) / len(saturation_avgs)) / maximum_value
                if saturation_avgs
                else 0.25
            )
            measurements = ColorMeasurements(
                source_sha256=source_sha256,
                source_range=analyzed_range,
                requested_samples=sample_count,
                frames_analyzed=len(y_avgs),
                bit_depth=storage_bit_depth,
                y_mean=y_mean,
                y_range=y_range,
                y_std=y_range / 4,
                saturation_mean=saturation_mean,
                ffmpeg_fingerprint=self.ffmpeg_fingerprint,
                ffprobe_fingerprint=self.ffprobe_fingerprint,
                cache_key=key,
            )
            atomic_write_text(destination, measurements.model_dump_json(indent=2) + "\n")
            return measurements

    def auto_grade(
        self,
        source: Path,
        *,
        source_range: TimeRange | None = None,
        sample_count: int = 10,
        policy: AutoGradePolicy | None = None,
        effect_id: str = "measured-auto-grade",
    ) -> MeasuredAutoGrade:
        selected_policy = policy or AutoGradePolicy()
        measurements = self.analyze(
            source,
            source_range=source_range,
            sample_count=sample_count,
        )
        grade = selected_policy.grade(measurements)
        semantic_measurements = measurements.model_copy(update={"cache_hit": False})
        effect = Effect(
            id=effect_id,
            kind=EffectKind.COLOR_GRADE,
            parameters=grade.model_dump(mode="json"),
            extensions={
                "auto_grade_policy": selected_policy.model_dump(mode="json"),
                "color_measurements": semantic_measurements.model_dump(mode="json"),
            },
        )
        return MeasuredAutoGrade(
            policy=selected_policy,
            measurements=measurements,
            grade=grade,
            effect=effect,
        )

    def pipeline(
        self,
        *,
        input_space: ColorSpace,
        working_space: ColorSpace = ColorSpace.REC709,
        normalization: TechnicalNormalization | None = None,
        creative_grade: CreativeGrade | None = None,
        lut_path: Path | None = None,
        output_space: ColorSpace = ColorSpace.REC709,
        output_pixel_format: str = "yuv420p",
    ) -> ColorPipeline:
        return ColorPipeline(
            input_space=input_space,
            working_space=working_space,
            normalization=normalization,
            creative_grade=creative_grade,
            lut_path=lut_path,
            output_space=output_space,
            output_pixel_format=output_pixel_format,
        )
