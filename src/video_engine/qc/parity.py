"""Decoded media comparison for legacy migration and golden-output evidence."""

from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile as sf  # type: ignore[import-untyped]
from numpy.typing import NDArray
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.config import EngineConfig
from video_engine.core.time import FrameRate, RationalTime, RoundingMode
from video_engine.errors import EngineError, ErrorCode
from video_engine.process import CommandRunner
from video_engine.render.cache import sha256_file
from video_engine.storage.atomic import atomic_write_text
from video_engine.temp import TemporaryWorkspace


class ParityPolicy(BaseModel):
    """Caller-owned migration expectations; no creative scoring lives here."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    frame_rate: FrameRate
    expected_candidate_duration: RationalTime
    frame_sample_times: tuple[RationalTime, ...] = ()
    max_frame_hash_distance: int | None = Field(default=None, ge=0, le=64)
    audio_sample_times: tuple[RationalTime, ...] = ()
    audio_window: RationalTime = Field(default_factory=lambda: RationalTime(value=1, timescale=5))
    audio_frequency_tolerance_hz: float = Field(default=8, ge=0, le=1_000)
    audio_rms_tolerance_db: float = Field(default=18, ge=0, le=60)
    require_audio_channel_match: bool = True
    duration_tolerance_frames: int = Field(default=0, ge=0, le=100)
    documented_improvements: tuple[str, ...] = ()

    @model_validator(mode="after")
    def valid_samples(self) -> ParityPolicy:
        if self.expected_candidate_duration.value <= 0:
            raise ValueError("expected candidate duration must be positive")
        if self.audio_window.value <= 0:
            raise ValueError("audio comparison window must be positive")
        for value in (*self.frame_sample_times, *self.audio_sample_times):
            if value.value < 0 or value >= self.expected_candidate_duration:
                raise ValueError("parity sample times must fall inside candidate duration")
        if self.frame_sample_times and self.max_frame_hash_distance is None:
            raise ValueError("frame samples require max_frame_hash_distance")
        return self


class MediaStreamSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_rate: str = Field(min_length=1)
    duration: RationalTime
    frame_count: int = Field(ge=0)
    audio_sample_rate: int | None = Field(default=None, gt=0)
    audio_channels: int | None = Field(default=None, gt=0)


class FrameParitySample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    time: RationalTime
    reference_hash: str = Field(pattern=r"^[0-9a-f]{16}$")
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{16}$")
    hamming_distance: int = Field(ge=0, le=64)
    passed: bool


class AudioParitySample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    time: RationalTime
    duration: RationalTime
    reference_dominant_hz: float = Field(ge=0)
    candidate_dominant_hz: float = Field(ge=0)
    frequency_delta_hz: float = Field(ge=0)
    reference_rms_dbfs: float
    candidate_rms_dbfs: float
    rms_delta_db: float = Field(ge=0)
    passed: bool


class MediaParityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    reference_path: Path
    candidate_path: Path
    reference_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference: MediaStreamSummary
    candidate: MediaStreamSummary
    exact_candidate_duration: bool
    frame_samples: tuple[FrameParitySample, ...] = ()
    audio_samples: tuple[AudioParitySample, ...] = ()
    documented_improvements: tuple[str, ...] = ()
    passed: bool


class MediaParityService:
    def __init__(
        self,
        project_root: Path,
        config: EngineConfig,
        runner: CommandRunner | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)
        self.runner = runner or CommandRunner()

    def compare(
        self,
        reference_path: Path,
        candidate_path: Path,
        policy: ParityPolicy,
    ) -> MediaParityReport:
        reference = reference_path.resolve()
        candidate = candidate_path.resolve()
        for label, path in (("reference", reference), ("candidate", candidate)):
            if not path.is_file():
                raise EngineError(
                    ErrorCode.STORAGE,
                    f"parity {label} media does not exist",
                    context={"path": str(path)},
                )
        reference_summary = self._summary(reference, policy.frame_rate)
        candidate_summary = self._summary(candidate, policy.frame_rate)
        expected_frames = policy.frame_rate.time_to_frames(
            policy.expected_candidate_duration,
            RoundingMode.EXACT,
        )
        frame_delta = abs(candidate_summary.frame_count - expected_frames)
        exact_duration = frame_delta <= policy.duration_tolerance_frames
        with TemporaryWorkspace(
            root=self.config.temp_dir,
            prefix="parity-",
            keep=False,
        ) as workspace:
            frame_samples = tuple(
                self._frame_sample(reference, candidate, time, policy, workspace)
                for time in policy.frame_sample_times
            )
            audio_samples = self._audio_samples(
                reference,
                candidate,
                policy,
                workspace,
            )
        metadata_matches = (
            reference_summary.width == candidate_summary.width
            and reference_summary.height == candidate_summary.height
            and candidate_summary.frame_rate == str(policy.frame_rate.fraction)
            and reference_summary.audio_sample_rate == candidate_summary.audio_sample_rate
            and (
                not policy.require_audio_channel_match
                or reference_summary.audio_channels == candidate_summary.audio_channels
            )
        )
        passed = (
            exact_duration
            and metadata_matches
            and all(sample.passed for sample in frame_samples)
            and all(sample.passed for sample in audio_samples)
        )
        return MediaParityReport(
            reference_path=reference,
            candidate_path=candidate,
            reference_sha256=sha256_file(reference),
            candidate_sha256=sha256_file(candidate),
            reference=reference_summary,
            candidate=candidate_summary,
            exact_candidate_duration=exact_duration,
            frame_samples=frame_samples,
            audio_samples=audio_samples,
            documented_improvements=policy.documented_improvements,
            passed=passed,
        )

    def write(self, report: MediaParityReport, json_path: Path, markdown_path: Path) -> None:
        atomic_write_text(json_path.resolve(), report.model_dump_json(indent=2) + "\n")
        rows = [
            "# Media Parity Report",
            "",
            f"- Status: **{'passed' if report.passed else 'failed'}**",
            f"- Reference: `{report.reference_path}`",
            f"- Candidate: `{report.candidate_path}`",
            f"- Candidate frames: {report.candidate.frame_count}",
            f"- Candidate duration exact: {report.exact_candidate_duration}",
            "",
            "## Frame Samples",
            "",
            "| Time | Reference | Candidate | Distance | Pass |",
            "| --- | --- | --- | ---: | --- |",
        ]
        rows.extend(
            f"| {sample.time.value}/{sample.time.timescale}s | "
            f"`{sample.reference_hash}` | `{sample.candidate_hash}` | "
            f"{sample.hamming_distance} | {sample.passed} |"
            for sample in report.frame_samples
        )
        rows.extend(["", "## Audio Samples", ""])
        rows.extend(
            f"- {sample.time.value}/{sample.time.timescale}s: "
            f"{sample.reference_dominant_hz:.2f} Hz vs "
            f"{sample.candidate_dominant_hz:.2f} Hz "
            f"(frequency delta {sample.frequency_delta_hz:.2f} Hz, "
            f"RMS delta {sample.rms_delta_db:.2f} dB, pass={sample.passed})"
            for sample in report.audio_samples
        )
        if report.documented_improvements:
            rows.extend(["", "## Documented Improvements", ""])
            rows.extend(f"- {item}" for item in report.documented_improvements)
        atomic_write_text(markdown_path.resolve(), "\n".join(rows) + "\n")

    def _summary(self, path: Path, rate: FrameRate) -> MediaStreamSummary:
        result = self.runner.run(
            [
                self.config.ffprobe_path,
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ]
        )
        try:
            payload = json.loads(result.stdout)
            video = next(stream for stream in payload["streams"] if stream["codec_type"] == "video")
            audio = next(
                (stream for stream in payload["streams"] if stream["codec_type"] == "audio"),
                None,
            )
            duration = RationalTime.from_fraction(
                Fraction(str(video.get("duration") or payload["format"]["duration"]))
            )
            frame_count = int(
                video.get("nb_frames")
                or rate.time_to_frames(
                    duration,
                    RoundingMode.NEAREST,
                )
            )
            frame_rate = str(Fraction(video["avg_frame_rate"]))
            return MediaStreamSummary(
                width=int(video["width"]),
                height=int(video["height"]),
                frame_rate=frame_rate,
                duration=duration,
                frame_count=frame_count,
                audio_sample_rate=(int(audio["sample_rate"]) if audio is not None else None),
                audio_channels=(int(audio["channels"]) if audio is not None else None),
            )
        except (KeyError, StopIteration, TypeError, ValueError) as exc:
            raise EngineError(
                ErrorCode.QC_FAILED,
                "parity media metadata is incomplete",
                context={"path": str(path), "detail": str(exc)},
            ) from exc

    def _frame_sample(
        self,
        reference: Path,
        candidate: Path,
        time: RationalTime,
        policy: ParityPolicy,
        workspace: Path,
    ) -> FrameParitySample:
        reference_hash = self._frame_hash(reference, time, workspace / "reference.png")
        candidate_hash = self._frame_hash(candidate, time, workspace / "candidate.png")
        distance = (int(reference_hash, 16) ^ int(candidate_hash, 16)).bit_count()
        limit = policy.max_frame_hash_distance
        assert limit is not None
        return FrameParitySample(
            time=time,
            reference_hash=reference_hash,
            candidate_hash=candidate_hash,
            hamming_distance=distance,
            passed=distance <= limit,
        )

    def _frame_hash(self, path: Path, time: RationalTime, output: Path) -> str:
        self.runner.run(
            [
                self.config.ffmpeg_path,
                "-y",
                "-v",
                "error",
                "-i",
                str(path),
                "-ss",
                str(time.seconds),
                "-frames:v",
                "1",
                str(output),
            ]
        )
        with Image.open(output) as source:
            values = np.asarray(
                source.convert("L").resize((9, 8), Image.Resampling.LANCZOS),
                dtype=np.int16,
            )
        bits = values[:, 1:] > values[:, :-1]
        integer = 0
        for value in bits.ravel():
            integer = (integer << 1) | int(value)
        return f"{integer:016x}"

    def _audio_samples(
        self,
        reference: Path,
        candidate: Path,
        policy: ParityPolicy,
        workspace: Path,
    ) -> tuple[AudioParitySample, ...]:
        if not policy.audio_sample_times:
            return ()
        reference_wav = workspace / "reference.wav"
        candidate_wav = workspace / "candidate.wav"
        for source, output in ((reference, reference_wav), (candidate, candidate_wav)):
            self.runner.run(
                [
                    self.config.ffmpeg_path,
                    "-y",
                    "-v",
                    "error",
                    "-i",
                    str(source),
                    "-map",
                    "0:a:0",
                    "-ac",
                    "2",
                    "-ar",
                    "48000",
                    "-c:a",
                    "pcm_f32le",
                    str(output),
                ]
            )
        reference_audio, reference_rate = sf.read(
            reference_wav,
            dtype="float32",
            always_2d=True,
        )
        candidate_audio, candidate_rate = sf.read(
            candidate_wav,
            dtype="float32",
            always_2d=True,
        )
        if reference_rate != candidate_rate:
            raise EngineError(
                ErrorCode.QC_FAILED,
                "parity audio sample rates differ after decode",
                context={"reference": reference_rate, "candidate": candidate_rate},
            )
        samples: list[AudioParitySample] = []
        window_count = max(1, round(policy.audio_window.seconds * reference_rate))
        for time in policy.audio_sample_times:
            start = round(time.seconds * reference_rate)
            reference_window = reference_audio[start : start + window_count]
            candidate_window = candidate_audio[start : start + window_count]
            if len(reference_window) != window_count or len(candidate_window) != window_count:
                raise EngineError(
                    ErrorCode.QC_FAILED,
                    "parity audio window falls outside decoded media",
                    context={"time": time.model_dump(mode="json")},
                )
            reference_hz, reference_rms = self._audio_measurement(
                reference_window,
                reference_rate,
            )
            candidate_hz, candidate_rms = self._audio_measurement(
                candidate_window,
                candidate_rate,
            )
            delta = abs(reference_hz - candidate_hz)
            rms_delta = abs(reference_rms - candidate_rms)
            samples.append(
                AudioParitySample(
                    time=time,
                    duration=policy.audio_window,
                    reference_dominant_hz=reference_hz,
                    candidate_dominant_hz=candidate_hz,
                    frequency_delta_hz=delta,
                    reference_rms_dbfs=reference_rms,
                    candidate_rms_dbfs=candidate_rms,
                    rms_delta_db=rms_delta,
                    passed=(
                        delta <= policy.audio_frequency_tolerance_hz
                        and rms_delta <= policy.audio_rms_tolerance_db
                    ),
                )
            )
        return tuple(samples)

    @staticmethod
    def _audio_measurement(
        samples: NDArray[np.float32],
        sample_rate: int,
    ) -> tuple[float, float]:
        mono = samples.mean(axis=1, dtype=np.float64)
        rms = float(np.sqrt(np.mean(np.square(mono))))
        rms_dbfs = 20 * math.log10(max(rms, 1e-12))
        windowed = mono * np.hanning(len(mono))
        spectrum = np.abs(np.fft.rfft(windowed))
        spectrum[0] = 0
        dominant = int(np.argmax(spectrum))
        frequency = dominant * sample_rate / len(mono)
        return frequency, rms_dbfs
