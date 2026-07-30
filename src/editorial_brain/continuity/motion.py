"""Camera and subject-motion compatibility."""

from editorial_brain.core.models import Shot


def motion_score(left: Shot, right: Shot) -> float:
    difference = abs(left.motion_energy - right.motion_energy)
    energy_score = max(0, 1 - difference)
    if left.camera.motion == "unknown" or right.camera.motion == "unknown":
        camera_score = 0.6
    elif left.camera.motion == right.camera.motion:
        camera_score = 1
    elif "locked" in {left.camera.motion, right.camera.motion}:
        camera_score = 0.65
    else:
        camera_score = 0.45
    return (energy_score + camera_score) / 2
