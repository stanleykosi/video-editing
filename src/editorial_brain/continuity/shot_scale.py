"""Shot-scale compatibility and jump-cut detection."""

from editorial_brain.core.models import CameraDescriptor

SCALE_ORDER = {
    "extreme_wide": 0,
    "wide": 1,
    "medium": 2,
    "close": 3,
    "detail": 4,
}


def shot_scale_score(left: CameraDescriptor, right: CameraDescriptor) -> float:
    if left.shot_scale == "unknown" or right.shot_scale == "unknown":
        return 0.6
    difference = abs(SCALE_ORDER[left.shot_scale] - SCALE_ORDER[right.shot_scale])
    if difference == 0:
        return 0.35
    if difference == 1:
        return 0.85
    if difference == 2:
        return 1
    return 0.7
