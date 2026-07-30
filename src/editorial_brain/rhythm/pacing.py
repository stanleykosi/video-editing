"""Global pacing-curve analysis that permits motivated long holds."""

from __future__ import annotations

from itertools import pairwise

from pydantic import Field

from editorial_brain.core.models import BrainModel, PlannedSegment, RhythmScore
from editorial_brain.policies.models import PacingPolicy
from video_engine.api import RationalTime


class PacingSample(BrainModel):
    segment_id: str
    duration: RationalTime
    motion_energy: float = Field(ge=0, le=1)
    information_density: float = Field(ge=0, le=1)
    audio_energy: float = Field(ge=0, le=1)
    emotional_intensity: float = Field(ge=0, le=1)
    intentional_hold: bool = False


class PacingCurve(BrainModel):
    samples: list[PacingSample]
    mean_duration: RationalTime
    duration_variation: float = Field(ge=0)
    monotony_score: float = Field(ge=0, le=1)
    density_overload: float = Field(ge=0, le=1)
    breathing_room: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


def build_pacing_curve(samples: list[PacingSample], policy: PacingPolicy) -> PacingCurve:
    if not samples:
        return PacingCurve(
            samples=[],
            mean_duration=RationalTime.zero(),
            duration_variation=0,
            monotony_score=0,
            density_overload=0,
            breathing_room=1,
        )
    durations = [float(sample.duration.fraction) for sample in samples]
    mean = sum(durations) / len(durations)
    variance = sum((duration - mean) ** 2 for duration in durations) / len(durations)
    coefficient = variance**0.5 / max(mean, 1e-9)
    identical_runs = _maximum_near_identical_run(durations)
    monotony = min(1, max(0, 1 - coefficient) * identical_runs / len(durations))
    overload = sum(
        sample.information_density > 0.8 and sample.motion_energy > 0.75 for sample in samples
    ) / len(samples)
    breathing = sum(
        sample.intentional_hold
        or sample.information_density < 0.45
        or float(sample.duration.fraction) >= float(policy.preferred_shot_duration.fraction)
        for sample in samples
    ) / len(samples)
    warnings: list[str] = []
    if identical_runs > policy.maximum_identical_duration_run:
        warnings.append("repeated_identical_shot_durations")
    if overload > 0.5:
        warnings.append("excessive_visual_information_density")
    preferred_seconds = float(policy.preferred_shot_duration.fraction)
    if all(duration < preferred_seconds * 0.7 for duration in durations):
        warnings.append("monotonically_fast_editing")
    if all(duration > preferred_seconds * 1.7 for duration in durations):
        warnings.append("monotonically_slow_editing")
    return PacingCurve(
        samples=samples,
        mean_duration=RationalTime(value=round(mean * 1_000_000), timescale=1_000_000),
        duration_variation=coefficient,
        monotony_score=monotony,
        density_overload=overload,
        breathing_room=breathing,
        warnings=warnings,
    )


def score_rhythm(
    segments: list[PlannedSegment],
    samples: list[PacingSample],
    policy: PacingPolicy,
) -> RhythmScore:
    curve = build_pacing_curve(samples, policy)
    preferred = float(policy.preferred_shot_duration.fraction)
    duration_fit = (
        sum(
            1 / (1 + abs(float(item.timeline_range.duration.fraction) - preferred))
            for item in segments
        )
        / len(segments)
        if segments
        else 0
    )
    energy_fit = 1 - _mean_step_error([sample.audio_energy for sample in samples])
    density_fit = 1 - curve.density_overload
    novelty = 1 - _adjacent_role_repetition(segments)
    repetition = max(curve.monotony_score, _source_repetition(segments))
    overall = (
        duration_fit * 0.25
        + energy_fit * 0.15
        + density_fit * 0.2
        + novelty * 0.2
        + curve.breathing_room * 0.2
    ) * (1 - repetition * 0.35)
    return RhythmScore(
        duration_fit=duration_fit,
        energy_fit=energy_fit,
        density_fit=density_fit,
        novelty=novelty,
        breathing_room=curve.breathing_room,
        repetition_penalty=repetition,
        overall=max(0, min(1, overall)),
    )


def samples_from_segments(segments: list[PlannedSegment]) -> list[PacingSample]:
    return [
        PacingSample(
            segment_id=segment.id,
            duration=segment.timeline_range.duration,
            motion_energy=0.5,
            information_density=0.55 if segment.role == "primary" else 0.35,
            audio_energy=0.5,
            emotional_intensity=0.5,
            intentional_hold=segment.protected,
        )
        for segment in segments
    ]


def _maximum_near_identical_run(values: list[float], tolerance: float = 0.04) -> int:
    maximum = current = 1
    for left, right in pairwise(values):
        current = current + 1 if abs(left - right) <= tolerance else 1
        maximum = max(maximum, current)
    return maximum


def _mean_step_error(values: list[float]) -> float:
    if len(values) < 2:
        return 0
    step_error = sum(abs(right - left) for left, right in pairwise(values))
    return min(1, step_error / (len(values) - 1))


def _adjacent_role_repetition(segments: list[PlannedSegment]) -> float:
    if len(segments) < 2:
        return 0
    repeats = sum(left.role == right.role for left, right in pairwise(segments))
    return repeats / (len(segments) - 1)


def _source_repetition(segments: list[PlannedSegment]) -> float:
    if not segments:
        return 0
    unique = {
        (item.media_id, item.source_range.start.fraction, item.source_range.end.fraction)
        for item in segments
    }
    return 1 - len(unique) / len(segments)
