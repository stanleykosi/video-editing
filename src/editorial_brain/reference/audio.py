"""Reference audio-energy and silence grammar."""

from editorial_brain.analysis.audio_events import AudioWindow


def audio_profile(windows: list[AudioWindow], bins: int = 50) -> tuple[list[float], float]:
    if not windows:
        return [], 0
    size = max(1, len(windows) // bins)
    curve = [
        sum(item.rms for item in windows[start : start + size]) / len(windows[start : start + size])
        for start in range(0, len(windows), size)
    ][:bins]
    maximum = max(curve) or 1
    normalized = [min(1, value / maximum) for value in curve]
    silence = sum(window.silent for window in windows) / len(windows)
    return normalized, silence
