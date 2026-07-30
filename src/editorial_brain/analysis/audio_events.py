"""Streaming waveform, RMS, peak, silence, and transient analysis."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from pydantic import Field

from editorial_brain.core.models import (
    AudioEvent,
    BrainModel,
    Confidence,
    EvidenceKind,
    EvidenceRef,
)
from video_engine.api import RationalTime, TimeRange


class AudioWindow(BrainModel):
    id: str
    media_id: str
    source_range: TimeRange
    rms: float = Field(ge=0)
    peak: float = Field(ge=0)
    transient_strength: float = Field(ge=0)
    silent: bool


def analyze_audio_windows(
    path: Path,
    *,
    media_id: str,
    media_sha256: str,
    sample_rate: int = 16_000,
    window_samples: int = 1600,
    silence_rms: float = 0.008,
    analysis_version: str = "audio-stream-v1",
) -> tuple[list[AudioWindow], list[AudioEvent], list[EvidenceRef]]:
    if sample_rate <= 0 or window_samples <= 0:
        raise ValueError("sample rate and window size must be positive")
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "pipe:1",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdout is not None
    windows: list[AudioWindow] = []
    events: list[AudioEvent] = []
    evidence: list[EvidenceRef] = []
    previous_rms = 0.0
    index = 0
    block_bytes = window_samples * 4
    while block := process.stdout.read(block_bytes):
        samples = np.frombuffer(block, dtype="<f4")
        if samples.size == 0:
            continue
        start = RationalTime(value=index * window_samples, timescale=sample_rate)
        duration = RationalTime(value=int(samples.size), timescale=sample_rate)
        source_range = TimeRange(start=start, duration=duration)
        rms = float(np.sqrt(np.mean(np.square(samples.astype(np.float64)))))
        peak = float(np.max(np.abs(samples)))
        transient = max(0.0, rms - previous_rms)
        silent = rms <= silence_rms
        window_id = f"audio-window:{media_id}:{index:08d}"
        window = AudioWindow(
            id=window_id,
            media_id=media_id,
            source_range=source_range,
            rms=rms,
            peak=peak,
            transient_strength=transient,
            silent=silent,
        )
        windows.append(window)
        ref = EvidenceRef(
            id=f"evidence:{window_id}",
            kind=EvidenceKind.MEASURED,
            media_id=media_id,
            media_sha256=media_sha256,
            source_range=source_range,
            audio_window_id=window_id,
            analysis_version=analysis_version,
            confidence=Confidence(
                score=1,
                basis=EvidenceKind.MEASURED,
                calibration="decoded_pcm",
            ),
            summary=f"RMS={rms:.6f}, peak={peak:.6f}, transient={transient:.6f}",
        )
        evidence.append(ref)
        if transient >= max(0.025, previous_rms * 0.75):
            events.append(
                AudioEvent(
                    id=f"audio-event:{media_id}:transient:{index:08d}",
                    media_id=media_id,
                    source_range=source_range,
                    kind="transient",
                    energy=rms,
                    evidence=[ref],
                    confidence=Confidence(
                        score=min(1, transient / 0.1),
                        basis=EvidenceKind.DERIVED,
                        calibration="rms_delta",
                    ),
                )
            )
        previous_rms = rms
        index += 1
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"FFmpeg audio analysis failed: {stderr[-500:]}")
    return windows, events, evidence


def merge_silence_windows(windows: list[AudioWindow]) -> list[TimeRange]:
    ranges: list[TimeRange] = []
    start: RationalTime | None = None
    end: RationalTime | None = None
    for window in windows:
        if window.silent:
            if start is None:
                start = window.source_range.start
            end = window.source_range.end
        elif start is not None and end is not None:
            ranges.append(TimeRange.from_start_end(start, end))
            start = None
            end = None
    if start is not None and end is not None:
        ranges.append(TimeRange.from_start_end(start, end))
    return ranges
