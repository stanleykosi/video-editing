"""Reference shot-duration and rhythm statistics."""

from __future__ import annotations

from video_engine.api import RationalTime, TimeRange


def duration_quantiles(ranges: list[TimeRange]) -> dict[str, RationalTime]:
    if not ranges:
        return {key: RationalTime.zero() for key in ("p10", "p25", "p50", "p75", "p90")}
    ordered = sorted(float(item.duration.fraction) for item in ranges)
    return {
        label: RationalTime(value=round(_quantile(ordered, value) * 1_000_000), timescale=1_000_000)
        for label, value in {"p10": 0.1, "p25": 0.25, "p50": 0.5, "p75": 0.75, "p90": 0.9}.items()
    }


def rhythm_curve(ranges: list[TimeRange]) -> list[float]:
    if not ranges:
        return []
    maximum = max(float(item.duration.fraction) for item in ranges)
    return [1 - float(item.duration.fraction) / max(maximum, 0.001) for item in ranges]


def _quantile(values: list[float], quantile: float) -> float:
    position = quantile * (len(values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight
