"""Music alignment as one bounded signal, never a mandatory beat grid."""

from editorial_brain.core.models import MusicEvent
from video_engine.api import RationalTime


def nearest_music_alignment(
    time: RationalTime, events: list[MusicEvent], tolerance_ms: int = 120
) -> float:
    if not events:
        return 0.5
    delta = min(abs(float(time.fraction - event.source_range.start.fraction)) for event in events)
    tolerance = tolerance_ms / 1000
    return max(0, 1 - delta / max(tolerance, 0.001))
