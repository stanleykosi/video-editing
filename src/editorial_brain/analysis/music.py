"""Beat/bar measurements for sources containing music."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from editorial_brain.core.models import (
    Confidence,
    EvidenceKind,
    EvidenceRef,
    MusicEvent,
)
from video_engine.api import RationalTime, TimeRange


def analyze_music(
    path: Path,
    *,
    media_id: str,
    media_sha256: str,
    sample_rate: int = 22_050,
    timescale: int = 1_000_000,
    analysis_version: str = "music-librosa-v1",
) -> tuple[list[MusicEvent], list[EvidenceRef]]:
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError("music analysis requires the brain-analysis dependencies") from exc
    samples = _decode_mono(path, sample_rate)
    actual_rate = sample_rate
    if not isinstance(samples, np.ndarray) or samples.size == 0:
        return [], []
    tempo, beat_frames = librosa.beat.beat_track(y=samples, sr=actual_rate)
    beat_times = librosa.frames_to_time(beat_frames, sr=actual_rate)
    tempo_value = float(np.asarray(tempo).reshape(-1)[0])
    events: list[MusicEvent] = []
    evidence: list[EvidenceRef] = []
    for position, seconds in enumerate(beat_times):
        start = RationalTime(value=round(float(seconds) * timescale), timescale=timescale)
        duration = RationalTime(value=1, timescale=actual_rate)
        source_range = TimeRange(start=start, duration=duration)
        ref = EvidenceRef(
            id=f"evidence:{media_id}:music:{position:08d}",
            kind=EvidenceKind.MEASURED,
            media_id=media_id,
            media_sha256=media_sha256,
            source_range=source_range,
            audio_window_id=f"music-beat:{media_id}:{position:08d}",
            analysis_version=analysis_version,
            confidence=Confidence(
                score=0.75,
                basis=EvidenceKind.MEASURED,
                calibration="librosa_beat_tracker",
            ),
            summary=f"tracked beat at estimated tempo {tempo_value:.3f} BPM",
        )
        evidence.append(ref)
        events.append(
            MusicEvent(
                id=f"music:{media_id}:beat:{position:08d}",
                media_id=media_id,
                source_range=source_range,
                kind="downbeat" if position % 4 == 0 else "beat",
                strength=1 if position % 4 == 0 else 0.6,
                tempo_bpm=tempo_value,
                confidence=ref.confidence,
            )
        )
        if position % 4 == 0:
            events.append(
                MusicEvent(
                    id=f"music:{media_id}:bar:{position // 4:06d}",
                    media_id=media_id,
                    source_range=source_range,
                    kind="bar",
                    strength=1,
                    tempo_bpm=tempo_value,
                    confidence=ref.confidence,
                )
            )
    return events, evidence


def _decode_mono(path: Path, sample_rate: int) -> np.ndarray[Any, np.dtype[np.floating[Any]]]:
    process = subprocess.run(
        [
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
        ],
        check=False,
        capture_output=True,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace")[-500:]
        raise RuntimeError(f"FFmpeg music analysis failed: {detail}")
    return np.frombuffer(process.stdout, dtype="<f4").copy()
