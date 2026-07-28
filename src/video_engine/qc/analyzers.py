"""Technical ingest, timeline, encoded video, audio, and delivery analyzers."""

from __future__ import annotations

import json
import math
import re
import struct
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from video_engine.captions.layout import validate_caption_layout
from video_engine.config import EngineConfig
from video_engine.core.schema import (
    AudioClip,
    CaptionTrack,
    Clip,
    ColorSpace,
    DeliveryProfile,
    EffectKind,
    Gap,
    GeneratorClip,
    GraphicsTrack,
    NestedSequenceClip,
    Project,
    Sequence,
    StillImageClip,
    VideoTrack,
)
from video_engine.core.time import RationalTime, TimeRange
from video_engine.core.validation import Severity, validate_project
from video_engine.errors import EngineError
from video_engine.graphics.models import GraphicBoundsPolicy
from video_engine.media.models import MediaProbe, MediaStreamProbe
from video_engine.media.probe import probe_media
from video_engine.process import CommandRunner
from video_engine.render.backends.ffmpeg import FFmpegBackend
from video_engine.render.backends.registry import BackendRegistry
from video_engine.render.backends.remotion import RemotionBackend
from video_engine.render.cache import sha256_file
from video_engine.render.compiler import CompiledRender, RenderCompiler
from video_engine.render.models import RenderManifest, RenderMode, RenderRequest
from video_engine.render.nodes import ArtifactType, DecodeNode, MotionGraphicNode

from .models import (
    QCCheckResult,
    QCCheckStatus,
    QCFinding,
    QCMeasurement,
    QCPolicy,
    QCScope,
    QCSeverity,
    check_status,
)


@dataclass(frozen=True, slots=True)
class QCContext:
    project: Project
    project_root: Path
    sequence: Sequence
    profile: DeliveryProfile
    timeline_range: TimeRange
    output_path: Path | None
    report_dir: Path
    config: EngineConfig
    runner: CommandRunner
    compiled: CompiledRender | None = None
    manifest: RenderManifest | None = None
    manifest_output_sha256: str | None = None
    manifest_stale: bool = False
    caption_track_ids: tuple[str, ...] | None = None
    caption_languages: tuple[str, ...] | None = None


def _measurement(
    name: str,
    value: object,
    unit: str | None = None,
    *,
    expected: object = None,
    tolerance: object = None,
) -> QCMeasurement:
    return QCMeasurement(
        name=name,
        value=value,  # type: ignore[arg-type]
        unit=unit,
        expected=expected,  # type: ignore[arg-type]
        tolerance=tolerance,  # type: ignore[arg-type]
    )


def _finding(
    code: str,
    scope: QCScope,
    message: str,
    *,
    blocking: bool,
    path: str | None = None,
    measurements: tuple[QCMeasurement, ...] = (),
    extensions: dict[str, object] | None = None,
) -> QCFinding:
    return QCFinding(
        code=code,
        scope=scope,
        severity=QCSeverity.ERROR if blocking else QCSeverity.WARNING,
        blocking=blocking,
        message=message,
        path=path,
        measurements=measurements,
        extensions=extensions or {},  # type: ignore[arg-type]
    )


def _result(
    code: str,
    scope: QCScope,
    started: float,
    findings: list[QCFinding],
    *,
    summary: str,
    measurements: list[QCMeasurement] | None = None,
) -> QCCheckResult:
    return QCCheckResult(
        code=code,
        scope=scope,
        status=check_status(findings),
        summary=summary,
        duration_seconds=time.monotonic() - started,
        findings=tuple(findings),
        measurements=tuple(measurements or ()),
    )


def skipped_check(
    code: str,
    scope: QCScope,
    started: float,
    message: str,
    *,
    error_code: str = "qc.evidence_unavailable",
    finding: QCFinding | None = None,
) -> QCCheckResult:
    return QCCheckResult(
        code=code,
        scope=scope,
        status=QCCheckStatus.SKIPPED,
        summary=message,
        duration_seconds=time.monotonic() - started,
        findings=(finding,) if finding is not None else (),
        error={"code": error_code, "message": message},
    )


def _resolve_media_path(project_root: Path, uri: str) -> Path:
    path = Path(uri)
    return (path if path.is_absolute() else project_root / path).resolve()


def _merged_ranges(ranges: list[TimeRange], within: TimeRange) -> list[TimeRange]:
    clipped = [intersection for item in ranges if (intersection := item.intersection(within))]
    clipped.sort(key=lambda item: item.start)
    merged: list[TimeRange] = []
    for current in clipped:
        if not merged or current.start > merged[-1].end:
            merged.append(current)
            continue
        end = max(merged[-1].end, current.end)
        merged[-1] = TimeRange(start=merged[-1].start, duration=end - merged[-1].start)
    return merged


def _uncovered_ranges(ranges: list[TimeRange], within: TimeRange) -> list[TimeRange]:
    gaps: list[TimeRange] = []
    cursor = within.start
    for covered in _merged_ranges(ranges, within):
        if covered.start > cursor:
            gaps.append(TimeRange(start=cursor, duration=covered.start - cursor))
        cursor = max(cursor, covered.end)
    if cursor < within.end:
        gaps.append(TimeRange(start=cursor, duration=within.end - cursor))
    return gaps


def _seconds(value: RationalTime) -> float:
    return float(value.fraction)


def _interval_overlaps(interval: tuple[float, float], ranges: list[TimeRange]) -> bool:
    start, end = interval
    return any(start < _seconds(item.end) and _seconds(item.start) < end for item in ranges)


def _codec_name(encoder: str) -> str:
    return {
        "libx264": "h264",
        "libx265": "hevc",
        "h264_nvenc": "h264",
        "hevc_nvenc": "hevc",
        "libaom-av1": "av1",
        "libvpx-vp9": "vp9",
    }.get(encoder, encoder)


def _color_expectation(color_space: ColorSpace) -> tuple[set[str], set[str], set[str]]:
    if color_space is ColorSpace.HLG:
        return {"bt2020"}, {"arib-std-b67"}, {"bt2020nc", "bt2020_ncl"}
    if color_space is ColorSpace.PQ:
        return {"bt2020"}, {"smpte2084"}, {"bt2020nc", "bt2020_ncl"}
    if color_space is ColorSpace.REC2020:
        return {"bt2020"}, {"bt709", "bt2020-10", "bt2020-12"}, {"bt2020nc", "bt2020_ncl"}
    return {"bt709"}, {"bt709"}, {"bt709"}


def _parse_loudnorm(stderr: str) -> dict[str, float] | None:
    candidates = re.findall(r"\{\s*\"input_i\".*?\}", stderr, flags=re.DOTALL)
    if not candidates:
        return None
    try:
        payload = json.loads(candidates[-1])
        return {
            key: float(payload[key]) for key in ("input_i", "input_tp", "input_lra", "input_thresh")
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _parse_astats(stderr: str) -> tuple[list[float], float | None]:
    channel: int | None = None
    channel_rms: dict[int, float] = {}
    overall_rms: float | None = None
    in_overall = False
    for raw_line in stderr.splitlines():
        line = raw_line.rsplit("] ", 1)[-1].strip()
        if line.startswith("Channel: "):
            try:
                channel = int(line.split(":", 1)[1])
            except ValueError:
                channel = None
            in_overall = False
        elif line == "Overall":
            channel = None
            in_overall = True
        elif line.startswith("RMS level dB:"):
            try:
                value = float(line.split(":", 1)[1].strip())
            except ValueError:
                continue
            if channel is not None:
                channel_rms[channel] = value
            elif in_overall:
                overall_rms = value
    return [channel_rms[key] for key in sorted(channel_rms)], overall_rms


def _parse_detect_intervals(stderr: str, prefix: str) -> list[tuple[float, float, float]]:
    if prefix == "black":
        return [
            (float(start), float(end), float(duration))
            for start, end, duration in re.findall(
                r"black_start:([0-9.]+)\s+black_end:([0-9.]+)\s+black_duration:([0-9.]+)",
                stderr,
            )
        ]
    starts = [float(value) for value in re.findall(r"freeze_start:\s*([0-9.]+)", stderr)]
    ends = [float(value) for value in re.findall(r"freeze_end:\s*([0-9.]+)", stderr)]
    durations = [float(value) for value in re.findall(r"freeze_duration:\s*([0-9.]+)", stderr)]
    return [
        (start, end, duration)
        for start, end, duration in zip(starts, ends, durations, strict=False)
    ]


def _mp4_atom_offsets(path: Path) -> dict[str, int]:
    offsets: dict[str, int] = {}
    file_size = path.stat().st_size
    with path.open("rb") as handle:
        offset = 0
        while offset + 8 <= file_size:
            handle.seek(offset)
            header = handle.read(16)
            if len(header) < 8:
                break
            size = struct.unpack(">I", header[:4])[0]
            atom = header[4:8].decode("latin1")
            header_size = 8
            if size == 1:
                if len(header) < 16:
                    break
                size = struct.unpack(">Q", header[8:16])[0]
                header_size = 16
            elif size == 0:
                size = file_size - offset
            if size < header_size or offset + size > file_size:
                break
            offsets.setdefault(atom, offset)
            offset += size
    return offsets


class TechnicalQCAnalyzers:
    def __init__(self, context: QCContext, policy: QCPolicy) -> None:
        self.context = context
        self.policy = policy
        self._output_probe: MediaProbe | None = None
        self._output_probe_error: EngineError | None = None

    def output_probe(self) -> MediaProbe | None:
        if self._output_probe is not None or self._output_probe_error is not None:
            return self._output_probe
        assert self.context.output_path is not None
        try:
            self._output_probe = probe_media(
                self.context.output_path,
                self.context.config,
                self.context.runner,
                deep_vfr=False,
            )
        except EngineError as exc:
            self._output_probe_error = exc
        return self._output_probe

    def ingest(self) -> list[QCCheckResult]:
        started = time.monotonic()
        findings: list[QCFinding] = []
        measurements: list[QCMeasurement] = []
        usages = self._media_usage()
        for media in self.context.project.media:
            path = _resolve_media_path(self.context.project_root, media.uri)
            media_path = f"media[{media.id}]"
            if media.offline:
                findings.append(
                    _finding(
                        "ingest.media_offline",
                        QCScope.INGEST,
                        "media reference is marked offline",
                        blocking=True,
                        path=media_path,
                    )
                )
                continue
            if not path.is_file():
                findings.append(
                    _finding(
                        "ingest.media_missing",
                        QCScope.INGEST,
                        "media source does not exist",
                        blocking=True,
                        path=str(path),
                    )
                )
                continue
            actual_hash = sha256_file(path)
            measurements.append(_measurement(f"{media.id}.sha256", actual_hash))
            if self.policy.verify_source_hashes and media.sha256 and actual_hash != media.sha256:
                findings.append(
                    _finding(
                        "ingest.hash_mismatch",
                        QCScope.INGEST,
                        "media source hash does not match its canonical reference",
                        blocking=True,
                        path=str(path),
                        measurements=(_measurement("sha256", actual_hash, expected=media.sha256),),
                    )
                )
            try:
                media_probe = probe_media(
                    path,
                    self.context.config,
                    self.context.runner,
                    deep_vfr=True,
                )
            except EngineError as exc:
                findings.append(
                    _finding(
                        "ingest.probe_failed",
                        QCScope.INGEST,
                        "media source could not be probed",
                        blocking=True,
                        path=str(path),
                        extensions=exc.to_dict()["error"],
                    )
                )
                continue
            expected_video, expected_audio, duration_required = usages.get(
                media.id, (False, False, False)
            )
            if duration_required and (
                media_probe.duration is None or media_probe.duration.value <= 0
            ):
                findings.append(
                    _finding(
                        "ingest.bad_duration",
                        QCScope.INGEST,
                        "media source has no positive duration",
                        blocking=True,
                        path=str(path),
                    )
                )
            if expected_video and not media_probe.video_streams:
                findings.append(
                    _finding(
                        "ingest.missing_video_stream",
                        QCScope.INGEST,
                        "timeline uses this source as video but it has no video stream",
                        blocking=True,
                        path=str(path),
                    )
                )
            if expected_audio and not media_probe.audio_streams:
                findings.append(
                    _finding(
                        "ingest.missing_audio_stream",
                        QCScope.INGEST,
                        "timeline uses this source as audio but it has no audio stream",
                        blocking=True,
                        path=str(path),
                    )
                )
            if media_probe.variable_frame_rate:
                findings.append(
                    _finding(
                        "ingest.variable_frame_rate",
                        QCScope.INGEST,
                        "variable-frame-rate source should be conformed before frame-accurate use",
                        blocking=False,
                        path=str(path),
                    )
                )
            if self.policy.decode_all_sources:
                decode = self.context.runner.run(
                    [
                        self.context.config.ffmpeg_path,
                        "-v",
                        "error",
                        "-xerror",
                        "-i",
                        path,
                        "-map",
                        "0",
                        "-f",
                        "null",
                        "-",
                    ],
                    check=False,
                )
                if decode.return_code != 0:
                    findings.append(
                        _finding(
                            "ingest.decode_failed",
                            QCScope.INGEST,
                            "media source failed a full decode scan",
                            blocking=True,
                            path=str(path),
                            extensions={
                                "return_code": decode.return_code,
                                "stderr_tail": decode.stderr[-2000:],
                            },
                        )
                    )
        return [
            _result(
                "ingest.sources",
                QCScope.INGEST,
                started,
                findings,
                summary=f"validated {len(self.context.project.media)} media source(s)",
                measurements=measurements,
            )
        ]

    def timeline(self) -> list[QCCheckResult]:
        checks: list[QCCheckResult] = []
        started = time.monotonic()
        findings: list[QCFinding] = []
        validation = validate_project(self.context.project)
        for issue in validation.issues:
            findings.append(
                _finding(
                    issue.code,
                    QCScope.TIMELINE,
                    issue.message,
                    blocking=issue.severity is Severity.ERROR,
                    path=issue.path,
                )
            )
        visual_ranges = [
            item.timeline_range
            for track in self.context.sequence.timeline.tracks
            if isinstance(track, (VideoTrack, GraphicsTrack)) and track.enabled
            for item in track.items
            if item.enabled
        ]
        gaps = _uncovered_ranges(visual_ranges, self.context.timeline_range)
        for gap in gaps:
            findings.append(
                _finding(
                    "timeline.implicit_visual_gap",
                    QCScope.TIMELINE,
                    "no enabled visual item covers this timeline interval",
                    blocking=self.policy.implicit_blank_is_blocking,
                    path=f"sequence:{self.context.sequence.id}",
                    measurements=(
                        _measurement("start", _seconds(gap.start), "seconds"),
                        _measurement("duration", _seconds(gap.duration), "seconds"),
                    ),
                )
            )
        checks.append(
            _result(
                "timeline.invariants",
                QCScope.TIMELINE,
                started,
                findings,
                summary="validated timeline invariants and visual coverage",
                measurements=[_measurement("implicit_gap_count", len(gaps), "intervals")],
            )
        )
        checks.extend(self._caption_layout_checks())
        checks.append(self._compile_capability_check())
        return checks

    def video(self) -> list[QCCheckResult]:
        probe = self.output_probe()
        started = time.monotonic()
        if probe is None:
            error = self._output_probe_error
            finding = _finding(
                "video.output_unreadable",
                QCScope.VIDEO,
                "encoded output could not be probed",
                blocking=True,
                path=str(self.context.output_path),
                extensions=error.to_dict()["error"] if error else {},
            )
            return [
                _result(
                    "video.output",
                    QCScope.VIDEO,
                    started,
                    [finding],
                    summary="encoded video metadata is unreadable",
                )
            ]
        findings: list[QCFinding] = []
        measurements: list[QCMeasurement] = []
        if not probe.video_streams:
            findings.append(
                _finding(
                    "video.missing_stream",
                    QCScope.VIDEO,
                    "encoded output has no video stream",
                    blocking=True,
                    path=str(self.context.output_path),
                )
            )
            return [
                _result(
                    "video.output",
                    QCScope.VIDEO,
                    started,
                    findings,
                    summary="validated encoded video stream",
                )
            ]
        stream = probe.video_streams[0]
        measurements.extend(
            [
                _measurement("width", stream.width, "pixels", expected=self.context.profile.width),
                _measurement(
                    "height", stream.height, "pixels", expected=self.context.profile.height
                ),
                _measurement(
                    "frame_rate",
                    (
                        str(stream.average_frame_rate.fraction)
                        if stream.average_frame_rate is not None
                        else None
                    ),
                    "frames/second",
                    expected=str(self.context.profile.frame_rate.fraction),
                ),
            ]
        )
        if (stream.width, stream.height) != (
            self.context.profile.width,
            self.context.profile.height,
        ):
            findings.append(
                _finding(
                    "video.wrong_dimensions",
                    QCScope.VIDEO,
                    "encoded video dimensions do not match the delivery profile",
                    blocking=True,
                    measurements=tuple(measurements[:2]),
                )
            )
        if stream.average_frame_rate != self.context.profile.frame_rate:
            findings.append(
                _finding(
                    "video.wrong_frame_rate",
                    QCScope.VIDEO,
                    "encoded frame rate does not match the delivery profile",
                    blocking=True,
                    measurements=(measurements[2],),
                )
            )
        findings.extend(self._color_findings(stream))
        checks = [
            _result(
                "video.output",
                QCScope.VIDEO,
                started,
                findings,
                summary="validated dimensions, frame rate, and colour tags",
                measurements=measurements,
            )
        ]
        checks.append(self._video_signal_check())
        checks.append(self._graphics_bounds_check())
        return checks

    def audio(self) -> list[QCCheckResult]:
        probe = self.output_probe()
        started = time.monotonic()
        if probe is None or not probe.audio_streams:
            finding = _finding(
                "audio.missing_stream",
                QCScope.AUDIO,
                "encoded engine output must contain an audio stream",
                blocking=True,
                path=str(self.context.output_path),
            )
            return [
                _result(
                    "audio.output",
                    QCScope.AUDIO,
                    started,
                    [finding],
                    summary="encoded audio stream is missing or unreadable",
                )
            ]
        stream = probe.audio_streams[0]
        checks = [self._audio_signal_check(stream)]
        checks.append(self._audio_duration_check(probe))
        checks.append(self._boundary_pop_check(stream))
        return checks

    def delivery(
        self,
        expected_sha256: str | None,
        caption_paths: tuple[Path, ...],
    ) -> list[QCCheckResult]:
        started = time.monotonic()
        findings: list[QCFinding] = []
        measurements: list[QCMeasurement] = []
        output = self.context.output_path
        assert output is not None
        probe = self.output_probe()
        if not output.is_file() or probe is None:
            findings.append(
                _finding(
                    "delivery.output_unplayable",
                    QCScope.DELIVERY,
                    "delivery output does not exist or cannot be probed",
                    blocking=True,
                    path=str(output),
                )
            )
            return [
                _result(
                    "delivery.output",
                    QCScope.DELIVERY,
                    started,
                    findings,
                    summary="validated delivery container and contract",
                )
            ]
        decode = self.context.runner.run(
            [
                self.context.config.ffmpeg_path,
                "-v",
                "error",
                "-xerror",
                "-i",
                output,
                "-map",
                "0",
                "-f",
                "null",
                "-",
            ],
            check=False,
        )
        if decode.return_code != 0:
            findings.append(
                _finding(
                    "delivery.decode_failed",
                    QCScope.DELIVERY,
                    "delivery output failed a full decode scan",
                    blocking=True,
                    path=str(output),
                    extensions={
                        "return_code": decode.return_code,
                        "stderr_tail": decode.stderr[-2000:],
                    },
                )
            )
        video_streams = probe.video_streams
        audio_streams = probe.audio_streams
        if not video_streams:
            findings.append(
                _finding(
                    "delivery.missing_video",
                    QCScope.DELIVERY,
                    "delivery output has no video stream",
                    blocking=True,
                )
            )
        if not audio_streams:
            findings.append(
                _finding(
                    "delivery.missing_audio",
                    QCScope.DELIVERY,
                    "delivery output has no audio stream",
                    blocking=True,
                )
            )
        if video_streams:
            actual = video_streams[0].codec_name
            expected = _codec_name(self.context.profile.video_codec)
            measurements.append(_measurement("video_codec", actual, expected=expected))
            if actual != expected:
                findings.append(
                    _finding(
                        "delivery.wrong_video_codec",
                        QCScope.DELIVERY,
                        "video codec does not match the delivery profile",
                        blocking=True,
                        measurements=(measurements[-1],),
                    )
                )
        if audio_streams:
            actual = audio_streams[0].codec_name
            expected = _codec_name(self.context.profile.audio_codec)
            measurements.append(_measurement("audio_codec", actual, expected=expected))
            if actual != expected:
                findings.append(
                    _finding(
                        "delivery.wrong_audio_codec",
                        QCScope.DELIVERY,
                        "audio codec does not match the delivery profile",
                        blocking=True,
                        measurements=(measurements[-1],),
                    )
                )
        actual_hash = sha256_file(output)
        measurements.append(_measurement("sha256", actual_hash, expected=expected_sha256))
        authoritative_hash = expected_sha256 or self.context.manifest_output_sha256
        if authoritative_hash is not None and actual_hash != authoritative_hash:
            findings.append(
                _finding(
                    "delivery.checksum_mismatch",
                    QCScope.DELIVERY,
                    "delivery checksum does not match the requested or render-manifest hash",
                    blocking=True,
                    measurements=(
                        _measurement("sha256", actual_hash, expected=authoritative_hash),
                    ),
                )
            )
        for caption_path in caption_paths:
            resolved = (
                caption_path
                if caption_path.is_absolute()
                else self.context.project_root / caption_path
            ).resolve()
            if not resolved.is_file():
                findings.append(
                    _finding(
                        "delivery.caption_sidecar_missing",
                        QCScope.DELIVERY,
                        "declared caption sidecar is missing",
                        blocking=True,
                        path=str(resolved),
                    )
                )
        if self.context.profile.fast_start and output.suffix.lower() in {".mp4", ".mov", ".m4v"}:
            atoms = _mp4_atom_offsets(output)
            measurements.append(_measurement("mp4_atom_offsets", atoms))
            if "moov" not in atoms or "mdat" not in atoms or atoms["moov"] > atoms["mdat"]:
                findings.append(
                    _finding(
                        "delivery.fast_start_missing",
                        QCScope.DELIVERY,
                        "MP4/MOV metadata is not placed before media data",
                        blocking=True,
                        measurements=(measurements[-1],),
                    )
                )
        expected_duration = _seconds(self.context.timeline_range.duration)
        actual_duration = _seconds(probe.duration) if probe.duration is not None else None
        frame_tolerance = self.policy.duration_tolerance_frames / float(
            self.context.profile.frame_rate.fraction
        )
        measurements.append(
            _measurement(
                "duration",
                actual_duration,
                "seconds",
                expected=expected_duration,
                tolerance=frame_tolerance,
            )
        )
        if actual_duration is None or abs(actual_duration - expected_duration) > frame_tolerance:
            findings.append(
                _finding(
                    "delivery.wrong_duration",
                    QCScope.DELIVERY,
                    "delivery duration differs from the rendered timeline range",
                    blocking=True,
                    measurements=(measurements[-1],),
                )
            )
        return [
            _result(
                "delivery.output",
                QCScope.DELIVERY,
                started,
                findings,
                summary="validated playability, streams, codecs, duration, fast-start, and hashes",
                measurements=measurements,
            )
        ]

    def _media_usage(self) -> dict[str, tuple[bool, bool, bool]]:
        usage: dict[str, tuple[bool, bool, bool]] = {}
        for sequence in self.context.project.sequences:
            for track in sequence.timeline.tracks:
                if not track.enabled:
                    continue
                for item in track.items:
                    if not item.enabled:
                        continue
                    if isinstance(item, (Clip, StillImageClip)):
                        video, audio, timed = usage.get(
                            item.media_reference_id, (False, False, False)
                        )
                        usage[item.media_reference_id] = (
                            True,
                            audio or (isinstance(item, Clip) and item.source_audio_enabled),
                            timed or isinstance(item, Clip),
                        )
                    elif isinstance(item, AudioClip):
                        video, _, _ = usage.get(item.media_reference_id, (False, False, False))
                        usage[item.media_reference_id] = (video, True, True)
                    elif isinstance(item, GeneratorClip):
                        for asset in item.assets:
                            previous = usage.get(asset.media_reference_id, (False, False, False))
                            usage[asset.media_reference_id] = (
                                True,
                                previous[1],
                                previous[2],
                            )
        return usage

    def _caption_layout_checks(self) -> list[QCCheckResult]:
        started = time.monotonic()
        if self.context.manifest_stale:
            return [
                skipped_check(
                    "timeline.caption_layout",
                    QCScope.TIMELINE,
                    started,
                    "render manifest revision differs from the loaded project",
                    error_code="qc.stale_manifest",
                )
            ]
        findings: list[QCFinding] = []
        selected = 0
        for track in self.context.sequence.timeline.tracks:
            if not isinstance(track, CaptionTrack) or not track.enabled:
                continue
            if self.context.caption_track_ids is not None and track.id not in (
                self.context.caption_track_ids
            ):
                continue
            if self.context.caption_languages is not None and track.language not in (
                self.context.caption_languages
            ):
                continue
            selected += 1
            result = validate_caption_layout(
                track,
                self.context.project.caption_styles,
                width=self.context.profile.width,
                height=self.context.profile.height,
                config=self.context.config,
            )
            for issue in result.issues:
                findings.append(
                    _finding(
                        issue.code,
                        QCScope.TIMELINE,
                        issue.message,
                        blocking=issue.severity == "error",
                        path=f"caption_track:{track.id}/cue:{issue.cue_id}",
                        extensions=issue.context,
                    )
                )
        return [
            _result(
                "timeline.caption_layout",
                QCScope.TIMELINE,
                started,
                findings,
                summary=f"validated {selected} selected caption track(s)",
            )
        ]

    def _compile_capability_check(self) -> QCCheckResult:
        started = time.monotonic()
        if self.context.manifest_stale:
            return skipped_check(
                "timeline.render_capabilities",
                QCScope.TIMELINE,
                started,
                "render manifest revision differs from the loaded project",
                error_code="qc.stale_manifest",
            )
        try:
            request = RenderRequest(
                output_path=self.context.report_dir / ".qc-compile-probe.mp4",
                mode=RenderMode.PREVIEW,
                sequence_id=self.context.sequence.id,
                delivery_profile_id=self.context.profile.id,
                timeline_range=self.context.timeline_range,
                caption_track_ids=self.context.caption_track_ids,
                caption_languages=self.context.caption_languages,
            )
            compiled = self.context.compiled or RenderCompiler(
                self.context.project,
                self.context.project_root,
                self.context.config,
            ).compile(request)
            registry = BackendRegistry()
            registry.register(FFmpegBackend(self.context.config))
            registry.register(RemotionBackend(self.context.config, self.context.project_root))
            registry.plan(compiled.graph.pruned(), "ffmpeg")
        except EngineError as exc:
            finding = _finding(
                "timeline.unsupported_render_capability",
                QCScope.TIMELINE,
                exc.message,
                blocking=True,
                extensions=exc.to_dict()["error"],
            )
            return _result(
                "timeline.render_capabilities",
                QCScope.TIMELINE,
                started,
                [finding],
                summary="timeline cannot be compiled by the registered render backends",
            )
        return _result(
            "timeline.render_capabilities",
            QCScope.TIMELINE,
            started,
            [],
            summary="timeline compiles to supported backend capabilities",
        )

    def _color_findings(self, stream: MediaStreamProbe) -> list[QCFinding]:
        video = stream
        expected_primaries, expected_transfer, expected_space = _color_expectation(
            self.context.profile.output_color_space
        )
        measurements = (
            _measurement(
                "color_primaries",
                video.color_primaries,
                expected=sorted(expected_primaries),
            ),
            _measurement(
                "color_transfer",
                video.color_transfer,
                expected=sorted(expected_transfer),
            ),
            _measurement(
                "color_space",
                video.color_space,
                expected=sorted(expected_space),
            ),
        )
        values = [
            video.color_primaries,
            video.color_transfer,
            video.color_space,
        ]
        expected = [expected_primaries, expected_transfer, expected_space]
        if any(value not in allowed for value, allowed in zip(values, expected, strict=True)):
            return [
                _finding(
                    "video.invalid_color_tags",
                    QCScope.VIDEO,
                    "encoded colour metadata does not match the delivery transform",
                    blocking=True,
                    measurements=measurements,
                )
            ]
        return []

    def _video_signal_check(self) -> QCCheckResult:
        started = time.monotonic()
        if self.context.manifest_stale:
            return skipped_check(
                "video.signal",
                QCScope.VIDEO,
                started,
                "black/freeze intervals cannot be correlated to a different project revision",
                error_code="qc.stale_manifest",
            )
        output = self.context.output_path
        assert output is not None
        result = self.context.runner.run(
            [
                self.context.config.ffmpeg_path,
                "-hide_banner",
                "-nostats",
                "-i",
                output,
                "-map",
                "0:v:0",
                "-vf",
                (
                    f"blackdetect=d={self.policy.black_min_duration_seconds}:"
                    "pix_th=0.10:pic_th=0.98,"
                    f"freezedetect=n=-60dB:d={self.policy.freeze_min_duration_seconds}"
                ),
                "-an",
                "-f",
                "null",
                "-",
            ],
            check=False,
        )
        if result.return_code != 0:
            return skipped_check(
                "video.signal",
                QCScope.VIDEO,
                started,
                "FFmpeg could not produce black/freeze detector evidence",
                error_code="qc.video_detector_failed",
            )
        black = _parse_detect_intervals(result.stderr, "black")
        frozen = _parse_detect_intervals(result.stderr, "freeze")
        visual_ranges = [
            item.timeline_range
            for track in self.context.sequence.timeline.tracks
            if isinstance(track, (VideoTrack, GraphicsTrack)) and track.enabled
            for item in track.items
            if item.enabled and not isinstance(item, Gap)
        ]
        dynamic_ranges = [
            item.timeline_range
            for track in self.context.sequence.timeline.tracks
            if isinstance(track, (VideoTrack, GraphicsTrack)) and track.enabled
            for item in track.items
            if item.enabled
            and isinstance(item, Clip)
            and not any(
                effect.enabled and effect.kind is EffectKind.FREEZE for effect in item.effects
            )
        ]
        findings: list[QCFinding] = []
        for start, end, duration in black:
            absolute = (
                start + _seconds(self.context.timeline_range.start),
                end + _seconds(self.context.timeline_range.start),
            )
            if _interval_overlaps(absolute, visual_ranges):
                findings.append(
                    _finding(
                        "video.unexpected_black",
                        QCScope.VIDEO,
                        "black frames occur while an enabled visual item is expected",
                        blocking=self.policy.black_is_blocking,
                        measurements=(
                            _measurement("start", absolute[0], "seconds"),
                            _measurement("duration", duration, "seconds"),
                        ),
                    )
                )
        for start, end, duration in frozen:
            absolute = (
                start + _seconds(self.context.timeline_range.start),
                end + _seconds(self.context.timeline_range.start),
            )
            if _interval_overlaps(absolute, dynamic_ranges):
                findings.append(
                    _finding(
                        "video.unexpected_freeze",
                        QCScope.VIDEO,
                        "frozen frames occur during a dynamic source interval",
                        blocking=self.policy.freeze_is_blocking,
                        measurements=(
                            _measurement("start", absolute[0], "seconds"),
                            _measurement("duration", duration, "seconds"),
                        ),
                    )
                )
        return _result(
            "video.signal",
            QCScope.VIDEO,
            started,
            findings,
            summary="scanned encoded frames for unexpected black and frozen intervals",
            measurements=[
                _measurement("black_interval_count", len(black), "intervals"),
                _measurement("freeze_interval_count", len(frozen), "intervals"),
            ],
        )

    def _graphics_bounds_check(self) -> QCCheckResult:
        started = time.monotonic()
        graphics = (
            [
                node
                for node in self.context.compiled.graph.nodes
                if isinstance(node, MotionGraphicNode)
            ]
            if self.context.compiled is not None
            else []
        )
        if not graphics:
            return _result(
                "video.graphics_bounds",
                QCScope.VIDEO,
                started,
                [],
                summary="timeline contains no designed graphics requiring bounds telemetry",
            )
        records = (
            {record.node_id: record for record in self.context.manifest.records}
            if self.context.manifest is not None
            else {}
        )
        missing: list[str] = []
        findings: list[QCFinding] = []
        measurements = [_measurement("graphics_count", len(graphics), "items")]
        for node in graphics:
            record = records.get(node.id)
            bounds = record.artifact_metadata.get("content_bounds") if record is not None else None
            if not isinstance(bounds, dict) or bounds.get("available") is not True:
                missing.append(node.id)
                continue
            measurements.append(_measurement(f"{node.id}.content_bounds", bounds))
            frame_bounds_count = int(bounds.get("frame_bounds_count", 0))
            edge_touch_frames = int(bounds.get("edge_touch_frames", 0))
            if frame_bounds_count == 0:
                findings.append(
                    _finding(
                        "video.blank_graphic",
                        QCScope.VIDEO,
                        "designed graphic produced no visible alpha content",
                        blocking=True,
                        path=f"render-node:{node.id}",
                    )
                )
                continue
            if node.bounds_policy is not GraphicBoundsPolicy.SAFE_AREA:
                continue
            edge_fraction = edge_touch_frames / frame_bounds_count
            if edge_fraction > 0.25:
                findings.append(
                    _finding(
                        "video.cropped_graphic",
                        QCScope.VIDEO,
                        "designed graphic content touches the canvas edge for too many frames",
                        blocking=True,
                        path=f"render-node:{node.id}",
                        measurements=(
                            _measurement(
                                "edge_touch_fraction",
                                edge_fraction,
                                expected="<=0.25",
                            ),
                        ),
                    )
                )
        if missing:
            finding = _finding(
                "video.graphics_bounds_evidence_unavailable",
                QCScope.VIDEO,
                "render manifest lacks alpha-bounds telemetry for designed graphics",
                blocking=False,
                measurements=(_measurement("missing_node_ids", missing),),
            )
            return skipped_check(
                "video.graphics_bounds",
                QCScope.VIDEO,
                started,
                "cropped-graphics analysis is incomplete without alpha-bounds telemetry",
                error_code="qc.graphics_bounds_telemetry_missing",
                finding=finding,
            )
        return _result(
            "video.graphics_bounds",
            QCScope.VIDEO,
            started,
            findings,
            summary="validated per-frame alpha bounds for designed graphics",
            measurements=measurements,
        )

    def _compiled_has_meaningful_audio(self) -> bool:
        if self.context.compiled is not None:
            roots = tuple(
                output.audio_node_id
                for output in self.context.compiled.section_outputs
                if output.audio_node_id is not None
            )
            if roots:
                closure = self.context.compiled.graph.ancestor_closure(roots)
                return any(
                    isinstance(node, DecodeNode)
                    and node.artifact_type is ArtifactType.AUDIO
                    and node.id in closure
                    for node in self.context.compiled.graph.nodes
                )
        return self._fallback_meaningful_audio(self.context.sequence, set())

    def _fallback_meaningful_audio(self, sequence: Sequence, seen: set[str]) -> bool:
        if sequence.id in seen:
            return False
        seen.add(sequence.id)
        for track in sequence.timeline.tracks:
            if not track.enabled:
                continue
            for item in track.items:
                if not item.enabled or not item.timeline_range.overlaps(
                    self.context.timeline_range
                ):
                    continue
                if isinstance(item, AudioClip):
                    return True
                if isinstance(item, Clip) and item.source_audio_enabled:
                    return True
                if isinstance(item, NestedSequenceClip) and item.source_audio_enabled:
                    try:
                        child = self.context.project.resolve_sequence(
                            item.sequence_id, item.sequence_version
                        )
                    except StopIteration:
                        continue
                    if self._fallback_meaningful_audio(child, seen):
                        return True
        return False

    def _audio_signal_check(self, stream: object) -> QCCheckResult:
        started = time.monotonic()
        output = self.context.output_path
        assert output is not None
        loudness = self.context.profile.loudness
        target_i = loudness.integrated_lufs if loudness is not None else -24
        target_tp = loudness.true_peak_dbtp if loudness is not None else -2
        target_lra = loudness.loudness_range_lu if loudness is not None else 7
        filter_value = (
            f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:print_format=json,"
            f"silencedetect=noise={self.policy.silence_noise_db}dB:"
            f"d={self.policy.silence_min_duration_seconds},astats=metadata=0:reset=0"
        )
        result = self.context.runner.run(
            [
                self.context.config.ffmpeg_path,
                "-hide_banner",
                "-nostats",
                "-i",
                output,
                "-map",
                "0:a:0",
                "-af",
                filter_value,
                "-vn",
                "-f",
                "null",
                "-",
            ],
            check=False,
        )
        if result.return_code != 0:
            return skipped_check(
                "audio.signal",
                QCScope.AUDIO,
                started,
                "FFmpeg could not produce loudness and signal evidence",
                error_code="qc.audio_analyzer_failed",
            )
        measured = _parse_loudnorm(result.stderr)
        if measured is None:
            return skipped_check(
                "audio.signal",
                QCScope.AUDIO,
                started,
                "FFmpeg loudness measurements could not be parsed",
                error_code="qc.audio_measurement_parse_failed",
            )
        findings: list[QCFinding] = []
        measurements = [
            _measurement("integrated_loudness", measured["input_i"], "LUFS"),
            _measurement("true_peak", measured["input_tp"], "dBTP"),
            _measurement("loudness_range", measured["input_lra"], "LU"),
        ]
        if loudness is not None:
            measurements[0] = measurements[0].model_copy(
                update={
                    "expected": loudness.integrated_lufs,
                    "tolerance": self.policy.loudness_tolerance_lu,
                }
            )
            measurements[1] = measurements[1].model_copy(
                update={"expected": f"<= {loudness.true_peak_dbtp}"}
            )
            measurements[2] = measurements[2].model_copy(
                update={
                    "expected": loudness.loudness_range_lu,
                    "tolerance": self.policy.loudness_range_tolerance_lu,
                }
            )
            if abs(measured["input_i"] - loudness.integrated_lufs) > (
                self.policy.loudness_tolerance_lu
            ):
                findings.append(
                    _finding(
                        "audio.loudness_failure",
                        QCScope.AUDIO,
                        "integrated loudness is outside the configured delivery tolerance",
                        blocking=True,
                        measurements=(measurements[0],),
                    )
                )
            if measured["input_tp"] > loudness.true_peak_dbtp:
                findings.append(
                    _finding(
                        "audio.true_peak_failure",
                        QCScope.AUDIO,
                        "true peak exceeds the configured delivery ceiling",
                        blocking=True,
                        measurements=(measurements[1],),
                    )
                )
            if abs(measured["input_lra"] - loudness.loudness_range_lu) > (
                self.policy.loudness_range_tolerance_lu
            ):
                findings.append(
                    _finding(
                        "audio.loudness_range_failure",
                        QCScope.AUDIO,
                        "loudness range is outside the configured delivery tolerance",
                        blocking=False,
                        measurements=(measurements[2],),
                    )
                )
        if measured["input_tp"] >= self.policy.clipping_threshold_dbfs:
            findings.append(
                _finding(
                    "audio.clipping",
                    QCScope.AUDIO,
                    "encoded audio reaches the configured clipping threshold",
                    blocking=True,
                    measurements=(
                        _measurement(
                            "true_peak",
                            measured["input_tp"],
                            "dBTP",
                            expected=f"< {self.policy.clipping_threshold_dbfs}",
                        ),
                    ),
                )
            )
        silence_starts = [
            float(value) for value in re.findall(r"silence_start:\s*([0-9.]+)", result.stderr)
        ]
        silence_ends = [
            float(value) for value in re.findall(r"silence_end:\s*([0-9.]+)", result.stderr)
        ]
        if not self.context.manifest_stale and self._compiled_has_meaningful_audio():
            for start_value, end_value in zip(silence_starts, silence_ends, strict=False):
                findings.append(
                    _finding(
                        "audio.unexpected_silence",
                        QCScope.AUDIO,
                        "silence exceeds the configured duration while decoded audio is expected",
                        blocking=self.policy.unexpected_silence_is_blocking,
                        measurements=(
                            _measurement("start", start_value, "seconds"),
                            _measurement("duration", end_value - start_value, "seconds"),
                        ),
                    )
                )
        channel_rms, _ = _parse_astats(result.stderr)
        if len(channel_rms) >= 2:
            finite = [value for value in channel_rms if math.isfinite(value)]
            imbalance = max(finite) - min(finite) if len(finite) >= 2 else math.inf
            measurements.append(_measurement("channel_imbalance", imbalance, "dB"))
            if imbalance > self.policy.channel_imbalance_db:
                findings.append(
                    _finding(
                        "audio.channel_imbalance",
                        QCScope.AUDIO,
                        "audio channels differ beyond the configured RMS tolerance",
                        blocking=False,
                        measurements=(measurements[-1],),
                    )
                )
            mono = self.context.runner.run(
                [
                    self.context.config.ffmpeg_path,
                    "-hide_banner",
                    "-nostats",
                    "-i",
                    output,
                    "-map",
                    "0:a:0",
                    "-af",
                    "pan=mono|c0=0.5*c0+0.5*c1,astats=metadata=0:reset=0",
                    "-vn",
                    "-f",
                    "null",
                    "-",
                ],
                check=False,
            )
            _, mono_rms = _parse_astats(mono.stderr)
            source_rms = sum(finite) / len(finite) if finite else None
            if mono.return_code == 0 and mono_rms is not None and source_rms is not None:
                cancellation = source_rms - mono_rms
                measurements.append(_measurement("mono_cancellation", cancellation, "dB"))
                if cancellation > self.policy.mono_cancellation_db:
                    findings.append(
                        _finding(
                            "audio.mono_compatibility",
                            QCScope.AUDIO,
                            "stereo mix loses substantial level when folded to mono",
                            blocking=False,
                            measurements=(measurements[-1],),
                        )
                    )
        return _result(
            "audio.signal",
            QCScope.AUDIO,
            started,
            findings,
            summary="measured loudness, peak, silence, channel balance, and mono compatibility",
            measurements=measurements,
        )

    def _audio_duration_check(self, probe: MediaProbe) -> QCCheckResult:
        started = time.monotonic()
        video = probe.video_streams[0] if probe.video_streams else None
        audio = probe.audio_streams[0] if probe.audio_streams else None
        video_duration = video.duration if video is not None else None
        audio_duration = audio.duration if audio is not None else None
        if video_duration is None or audio_duration is None:
            return skipped_check(
                "audio.duration_sync",
                QCScope.AUDIO,
                started,
                "stream-level audio/video durations are unavailable",
                error_code="qc.stream_duration_missing",
            )
        delta = abs(_seconds(video_duration - audio_duration))
        tolerance = (
            self.policy.audio_video_tolerance_samples / self.context.profile.audio_sample_rate
        )
        findings: list[QCFinding] = []
        measurement = _measurement(
            "audio_video_duration_delta", delta, "seconds", expected=0, tolerance=tolerance
        )
        if delta > tolerance:
            findings.append(
                _finding(
                    "audio.video_duration_mismatch",
                    QCScope.AUDIO,
                    "audio and video stream durations differ beyond the sample tolerance",
                    blocking=True,
                    measurements=(measurement,),
                )
            )
        return _result(
            "audio.duration_sync",
            QCScope.AUDIO,
            started,
            findings,
            summary="compared stream-level audio and video durations",
            measurements=[measurement],
        )

    def _cut_times(self) -> list[RationalTime]:
        points: set[RationalTime] = set()
        within = self.context.timeline_range
        for track in self.context.sequence.timeline.tracks:
            if not track.enabled:
                continue
            for item in track.items:
                if not item.enabled:
                    continue
                for point in (item.timeline_range.start, item.timeline_range.end):
                    if within.start < point < within.end:
                        points.add(point - within.start)
        return sorted(points)

    def _boundary_pop_check(self, stream: object) -> QCCheckResult:
        started = time.monotonic()
        if self.context.manifest_stale:
            return skipped_check(
                "audio.boundary_pops",
                QCScope.AUDIO,
                started,
                "audio boundaries cannot be correlated to a different project revision",
                error_code="qc.stale_manifest",
            )
        output = self.context.output_path
        assert output is not None
        cuts = self._cut_times()
        if not cuts:
            return _result(
                "audio.boundary_pops",
                QCScope.AUDIO,
                started,
                [],
                summary="timeline range has no internal item boundaries",
            )
        selected = cuts[: self.policy.max_boundary_checks]
        channels = int(getattr(stream, "channels", None) or self.context.profile.audio_channels)
        sample_rate = int(
            getattr(stream, "sample_rate", None) or self.context.profile.audio_sample_rate
        )
        window_seconds = 0.012
        findings: list[QCFinding] = []
        maximum_jump = 0.0
        raw_path = self.context.report_dir / ".boundary-samples.f32le"
        for cut in selected:
            start_value = max(0.0, _seconds(cut) - window_seconds / 2)
            command = self.context.runner.run(
                [
                    self.context.config.ffmpeg_path,
                    "-v",
                    "error",
                    "-y",
                    "-ss",
                    f"{start_value:.9f}",
                    "-i",
                    output,
                    "-map",
                    "0:a:0",
                    "-t",
                    f"{window_seconds:.9f}",
                    "-ac",
                    str(channels),
                    "-ar",
                    str(sample_rate),
                    "-c:a",
                    "pcm_f32le",
                    "-f",
                    "f32le",
                    raw_path,
                ],
                check=False,
            )
            if command.return_code != 0 or not raw_path.is_file():
                continue
            samples = np.fromfile(raw_path, dtype="<f4")
            if samples.size < channels * 3:
                continue
            frames = samples[: samples.size - samples.size % channels].reshape(-1, channels)
            center = min(
                len(frames) - 2,
                max(1, round((_seconds(cut) - start_value) * sample_rate)),
            )
            jump = float(np.max(np.abs(frames[center] - frames[center - 1])))
            maximum_jump = max(maximum_jump, jump)
            if jump > self.policy.boundary_pop_threshold:
                findings.append(
                    _finding(
                        "audio.boundary_pop",
                        QCScope.AUDIO,
                        "sample discontinuity at an edit boundary exceeds the threshold",
                        blocking=True,
                        measurements=(
                            _measurement("timeline_time", _seconds(cut), "seconds"),
                            _measurement(
                                "sample_jump",
                                jump,
                                "linear amplitude",
                                expected=f"<= {self.policy.boundary_pop_threshold}",
                            ),
                        ),
                    )
                )
        raw_path.unlink(missing_ok=True)
        if len(cuts) > len(selected):
            findings.append(
                _finding(
                    "audio.boundary_scan_limited",
                    QCScope.AUDIO,
                    "boundary scan reached the configured maximum number of cut points",
                    blocking=False,
                    measurements=(
                        _measurement("total_boundaries", len(cuts), "boundaries"),
                        _measurement("checked_boundaries", len(selected), "boundaries"),
                    ),
                )
            )
        return _result(
            "audio.boundary_pops",
            QCScope.AUDIO,
            started,
            findings,
            summary=f"sampled {len(selected)} audio edit boundary/boundaries",
            measurements=[_measurement("maximum_sample_jump", maximum_jump, "linear amplitude")],
        )
