"""Measured subtitle-stream caption density."""

from pathlib import Path
from typing import Any

import numpy as np

from video_engine.api import RationalTime


def caption_density(subtitle_stream_count: int, duration: RationalTime) -> float:
    seconds = float(duration.fraction)
    if seconds <= 0 or subtitle_stream_count <= 0:
        return 0
    return min(1, subtitle_stream_count / max(seconds / 60, 1))


def visual_overlay_density(frame_paths: list[Path]) -> tuple[float, dict[str, float]]:
    """Measure high-contrast text/graphic-like regions by vertical zone."""
    if not frame_paths:
        return 0, {}
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("overlay density requires brain-analysis dependencies") from exc
    scores: list[float] = []
    zones = {"top": 0.0, "center": 0.0, "bottom": 0.0}
    for path in frame_paths:
        frame: np.ndarray[Any, Any] | None = cv2.imread(str(path))
        if frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        height = edges.shape[0]
        zone_values = {
            "top": float(np.mean(edges[: height // 3] > 0)),
            "center": float(np.mean(edges[height // 3 : 2 * height // 3] > 0)),
            "bottom": float(np.mean(edges[2 * height // 3 :] > 0)),
        }
        for key, value in zone_values.items():
            zones[key] += value
        scores.append(min(1, sum(zone_values.values()) / 0.45))
    if not scores:
        return 0, {}
    normalized_zones = {key: value / len(scores) for key, value in zones.items()}
    total = sum(normalized_zones.values()) or 1
    placement = {key: value / total for key, value in normalized_zones.items()}
    return sum(scores) / len(scores), placement
