"""Measured cross-source audio synchronization evidence."""

from __future__ import annotations

from typing import Any

import numpy as np

from editorial_brain.core.models import (
    Confidence,
    EvidenceKind,
    EvidenceRef,
    SourceSynchronization,
)
from video_engine.api import RationalTime, TimeRange

SynchronizationResult = SourceSynchronization


def correlate_audio(
    reference: np.ndarray[Any, np.dtype[np.floating[Any]]],
    target: np.ndarray[Any, np.dtype[np.floating[Any]]],
    *,
    sample_rate: int,
    reference_media_id: str,
    target_media_id: str,
    reference_media_sha256: str,
    target_media_sha256: str,
    maximum_offset_seconds: int = 30,
) -> SynchronizationResult:
    if sample_rate <= 0 or maximum_offset_seconds <= 0:
        raise ValueError("sample rate and maximum offset must be positive")
    if reference.size == 0 or target.size == 0:
        raise ValueError("synchronization inputs cannot be empty")
    reference_values = _normalize(reference)
    target_values = _normalize(target)
    if max(reference_values.size, target_values.size) >= 10_000:
        try:
            from scipy.signal import correlate  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "long-source synchronization requires the brain-ml optional dependency"
            ) from exc
        correlation = correlate(target_values, reference_values, mode="full", method="fft")
    else:
        correlation = np.correlate(target_values, reference_values, mode="full")
    lags = np.arange(-reference_values.size + 1, target_values.size)
    maximum_lag = maximum_offset_seconds * sample_rate
    mask = np.abs(lags) <= maximum_lag
    bounded = correlation[mask]
    bounded_lags = lags[mask]
    best_index = int(np.argmax(bounded))
    lag = int(bounded_lags[best_index])
    normalized_peak = float(bounded[best_index]) / max(1, min(reference.size, target.size))
    confidence_score = max(0.0, min(1.0, abs(normalized_peak)))
    confidence = Confidence(
        score=confidence_score,
        basis=EvidenceKind.MEASURED,
        calibration="normalized_cross_correlation",
        sample_size=min(reference.size, target.size),
    )
    duration = RationalTime(value=min(reference.size, target.size), timescale=sample_rate)
    evidence = [
        EvidenceRef(
            id=f"evidence:sync:{media_id}",
            kind=EvidenceKind.MEASURED,
            media_id=media_id,
            media_sha256=media_sha256,
            source_range=TimeRange(start=RationalTime.zero(), duration=duration),
            audio_window_id=f"sync-window:{media_id}",
            analysis_version="audio-sync-v1",
            confidence=confidence,
            summary="decoded mono audio used for cross-source correlation",
        )
        for media_id, media_sha256 in (
            (reference_media_id, reference_media_sha256),
            (target_media_id, target_media_sha256),
        )
    ]
    return SynchronizationResult(
        reference_media_id=reference_media_id,
        target_media_id=target_media_id,
        target_offset=RationalTime(value=lag, timescale=sample_rate),
        correlation=max(-1, min(1, normalized_peak)),
        confidence=confidence,
        evidence=evidence,
    )


def _normalize(values: np.ndarray[Any, np.dtype[np.floating[Any]]]) -> np.ndarray[Any, Any]:
    centered = values.astype(np.float64) - float(np.mean(values))
    deviation = float(np.std(centered))
    return centered / deviation if deviation > 1e-12 else centered
