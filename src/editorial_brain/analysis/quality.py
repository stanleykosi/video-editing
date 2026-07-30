"""Measured frame quality features."""

from __future__ import annotations

from typing import Any

import numpy as np


def frame_quality(frame_bgr: np.ndarray[Any, Any]) -> dict[str, float]:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "frame quality requires the brain-analysis optional dependencies"
        ) from exc
    if frame_bgr.ndim != 3 or frame_bgr.shape[2] < 3:
        raise ValueError("quality input must be a BGR color frame")
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharpness = 1 - np.exp(-laplacian_variance / 500.0)
    luminance = gray.astype(np.float32) / 255.0
    clipped = float(np.mean((luminance <= 0.02) | (luminance >= 0.98)))
    mean = float(np.mean(luminance))
    exposure_center = max(0.0, 1 - abs(mean - 0.5) * 2)
    exposure = exposure_center * (1 - clipped)
    return {
        "sharpness": _unit(sharpness),
        "exposure": _unit(exposure),
        "mean_luminance": _unit(mean),
        "clipped_fraction": _unit(clipped),
    }


def color_histogram(frame_bgr: np.ndarray[Any, Any], bins: int = 16) -> list[float]:
    if bins <= 0:
        raise ValueError("histogram bins must be positive")
    histogram: list[float] = []
    for channel in range(3):
        values, _ = np.histogram(frame_bgr[:, :, channel], bins=bins, range=(0, 256))
        normalized = values.astype(np.float64)
        normalized /= max(1, int(normalized.sum()))
        histogram.extend(float(value) for value in normalized)
    return histogram


def histogram_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("histograms must be nonempty and equal length")
    distance = sum(abs(a - b) for a, b in zip(left, right, strict=True)) / 2
    return _unit(1 - distance / 3)


def _unit(value: float | np.floating[Any]) -> float:
    return max(0.0, min(1.0, float(value)))
