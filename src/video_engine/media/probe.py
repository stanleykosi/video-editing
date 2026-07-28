"""FFprobe metadata extraction and media characteristic detection."""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any

from video_engine.config import EngineConfig
from video_engine.core.time import FrameRate, RationalTime
from video_engine.errors import EngineError, ErrorCode
from video_engine.media.models import MediaKind, MediaProbe, MediaStreamProbe
from video_engine.process import CommandRunner

HDR_TRANSFERS = {"arib-std-b67", "smpte2084"}


def _fraction(value: object) -> Fraction | None:
    if value in {None, "", "N/A", "0/0"}:
        return None
    try:
        if isinstance(value, str) and "/" in value:
            numerator, denominator = value.split("/", 1)
            if int(denominator) == 0:
                return None
            return Fraction(int(numerator), int(denominator))
        return Fraction(Decimal(str(value)))
    except (ValueError, ZeroDivisionError, InvalidOperation):
        return None


def _duration(value: object) -> RationalTime | None:
    fraction = _fraction(value)
    return RationalTime.from_fraction(fraction) if fraction is not None and fraction >= 0 else None


def _frame_rate(value: object) -> FrameRate | None:
    fraction = _fraction(value)
    if fraction is None or fraction <= 0:
        return None
    return FrameRate(numerator=fraction.numerator, denominator=fraction.denominator)


def _int(value: object) -> int | None:
    try:
        return int(str(value)) if value not in {None, "", "N/A"} else None
    except ValueError:
        return None


def _rotation(stream: dict[str, Any]) -> int:
    tags = stream.get("tags") or {}
    if "rotate" in tags:
        try:
            return int(float(tags["rotate"])) % 360
        except (ValueError, TypeError):
            pass
    for side_data in stream.get("side_data_list") or []:
        if side_data.get("rotation") is not None:
            return int(float(side_data["rotation"])) % 360
    return 0


def _kind(value: object) -> MediaKind:
    try:
        return MediaKind(str(value))
    except ValueError:
        return MediaKind.UNKNOWN


def _stream_probe(stream: dict[str, Any]) -> MediaStreamProbe:
    tags = stream.get("tags") or {}
    time_base_fraction = _fraction(stream.get("time_base"))
    return MediaStreamProbe(
        index=int(stream.get("index", 0)),
        kind=_kind(stream.get("codec_type")),
        codec_name=stream.get("codec_name"),
        codec_long_name=stream.get("codec_long_name"),
        profile=str(stream["profile"]) if stream.get("profile") is not None else None,
        duration=_duration(stream.get("duration")),
        time_base=(
            RationalTime.from_fraction(time_base_fraction)
            if time_base_fraction is not None
            else None
        ),
        average_frame_rate=_frame_rate(stream.get("avg_frame_rate")),
        real_frame_rate=_frame_rate(stream.get("r_frame_rate")),
        frame_count=_int(stream.get("nb_frames")),
        width=_int(stream.get("width")),
        height=_int(stream.get("height")),
        pixel_format=stream.get("pix_fmt"),
        sample_aspect_ratio=stream.get("sample_aspect_ratio"),
        display_aspect_ratio=stream.get("display_aspect_ratio"),
        color_range=stream.get("color_range"),
        color_space=stream.get("color_space"),
        color_transfer=stream.get("color_transfer"),
        color_primaries=stream.get("color_primaries"),
        bits_per_raw_sample=_int(stream.get("bits_per_raw_sample")),
        sample_rate=_int(stream.get("sample_rate")),
        channels=_int(stream.get("channels")),
        channel_layout=stream.get("channel_layout"),
        rotation_degrees=_rotation(stream),
        language=tags.get("language"),
        disposition={
            str(key): int(value) for key, value in (stream.get("disposition") or {}).items()
        },
    )


def _deep_vfr(path: Path, config: EngineConfig, runner: CommandRunner) -> bool | None:
    result = runner.run(
        [
            config.ffmpeg_path,
            "-hide_banner",
            "-nostats",
            "-i",
            path,
            "-map",
            "0:v:0",
            "-vf",
            "vfrdet",
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=False,
    )
    match = re.search(r"VFR:([0-9.]+)", result.stderr)
    return float(match.group(1)) > 0 if match else None


def probe_media(
    path: Path,
    config: EngineConfig,
    runner: CommandRunner,
    *,
    deep_vfr: bool = True,
) -> MediaProbe:
    if not path.is_file():
        raise EngineError(
            ErrorCode.MEDIA_NOT_FOUND,
            "media source does not exist",
            context={"path": str(path)},
        )
    result = runner.run(
        [
            config.ffprobe_path,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            path,
        ]
    )
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise EngineError(
            ErrorCode.MEDIA_INVALID,
            "ffprobe returned invalid JSON",
            context={"path": str(path), "detail": str(exc)},
        ) from exc
    streams = [_stream_probe(stream) for stream in raw.get("streams", [])]
    if not streams:
        raise EngineError(
            ErrorCode.MEDIA_INVALID,
            "media has no readable streams",
            context={"path": str(path)},
        )
    format_data = raw.get("format") or {}
    video_streams = [stream for stream in streams if stream.kind is MediaKind.VIDEO]
    heuristic_vfr = any(
        stream.average_frame_rate is not None
        and stream.real_frame_rate is not None
        and abs(
            stream.average_frame_rate.frames_per_second - stream.real_frame_rate.frames_per_second
        )
        > 0.001
        for stream in video_streams
    )
    measured_vfr = _deep_vfr(path, config, runner) if deep_vfr and video_streams else None
    variable_frame_rate = measured_vfr if measured_vfr is not None else heuristic_vfr
    hdr = any(stream.color_transfer in HDR_TRANSFERS for stream in video_streams)
    warnings: list[str] = []
    if variable_frame_rate:
        warnings.append("variable frame rate detected; conform before frame-accurate editing")
    if hdr:
        warnings.append("HDR transfer metadata detected")
    if not video_streams:
        warnings.append("media has no video stream")
    if not any(stream.kind is MediaKind.AUDIO for stream in streams):
        warnings.append("media has no audio stream")
    return MediaProbe(
        format_name=str(format_data.get("format_name") or "unknown"),
        format_long_name=format_data.get("format_long_name"),
        duration=_duration(format_data.get("duration")),
        size_bytes=path.stat().st_size,
        bit_rate=_int(format_data.get("bit_rate")),
        streams=streams,
        variable_frame_rate=variable_frame_rate,
        hdr=hdr,
        warnings=warnings,
        extensions={"ffprobe:format_tags": format_data.get("tags") or {}},
    )
