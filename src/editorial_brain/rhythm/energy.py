"""Energy-curve helpers."""

from editorial_brain.core.models import AudioEvent, Shot


def combined_energy(shot: Shot, events: list[AudioEvent]) -> float:
    overlapping = [
        event.energy for event in events if event.source_range.overlaps(shot.source_range)
    ]
    audio = sum(overlapping) / len(overlapping) if overlapping else 0
    return max(0, min(1, shot.motion_energy * 0.6 + audio * 0.4))
