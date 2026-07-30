"""Screen-direction compatibility."""

from editorial_brain.core.models import CameraDescriptor


def screen_direction_score(left: CameraDescriptor, right: CameraDescriptor) -> float:
    neutral = {"neutral", "unknown"}
    if left.screen_direction in neutral or right.screen_direction in neutral:
        return 0.7
    return 1 if left.screen_direction == right.screen_direction else 0
