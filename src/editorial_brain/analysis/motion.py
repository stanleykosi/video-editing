"""Measured optical-flow motion energy."""

from __future__ import annotations

from typing import Any

import numpy as np


def optical_flow_energy(
    previous_bgr: np.ndarray[Any, Any], current_bgr: np.ndarray[Any, Any]
) -> float:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "optical flow requires the brain-analysis optional dependencies"
        ) from exc
    previous = cv2.cvtColor(previous_bgr, cv2.COLOR_BGR2GRAY)
    current = cv2.cvtColor(current_bgr, cv2.COLOR_BGR2GRAY)
    if previous.shape != current.shape:
        raise ValueError("optical-flow frames must have equal dimensions")
    flow = cv2.calcOpticalFlowFarneback(  # type: ignore[call-overload]
        previous, current, None, 0.5, 3, 15, 3, 5, 1.2, 0
    )
    magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    robust = float(np.percentile(magnitude, 75))
    height, width = previous.shape[:2]
    diagonal = max(1.0, float(np.hypot(height, width)))
    return max(0.0, min(1.0, robust / (diagonal * 0.02)))


def motion_direction(previous_bgr: np.ndarray[Any, Any], current_bgr: np.ndarray[Any, Any]) -> str:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("motion direction requires brain-analysis dependencies") from exc
    previous = cv2.cvtColor(previous_bgr, cv2.COLOR_BGR2GRAY)
    current = cv2.cvtColor(current_bgr, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(  # type: ignore[call-overload]
        previous, current, None, 0.5, 3, 15, 3, 5, 1.2, 0
    )
    horizontal = float(np.median(flow[..., 0]))
    if abs(horizontal) < 0.1:
        return "neutral"
    return "left_to_right" if horizontal > 0 else "right_to_left"
