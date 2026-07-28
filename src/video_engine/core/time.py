"""Exact time primitives for frames, timeline edits, and audio samples."""

from __future__ import annotations

import math
import re
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from functools import total_ordering
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RoundingMode(StrEnum):
    EXACT = "exact"
    FLOOR = "floor"
    CEIL = "ceil"
    NEAREST = "nearest"


class RationalRate(BaseModel):
    """A positive dimensionless rational used for authoritative time mapping."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    numerator: int = Field(gt=0)
    denominator: int = Field(default=1, gt=0)

    @model_validator(mode="before")
    @classmethod
    def parse_scalar(cls, value: Any) -> Any:
        if isinstance(value, (cls, dict)):
            return value
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float, str, Decimal)):
            fraction = Fraction(str(value))
            return {
                "numerator": fraction.numerator,
                "denominator": fraction.denominator,
            }
        return value

    @model_validator(mode="after")
    def normalize(self) -> RationalRate:
        divisor = math.gcd(self.numerator, self.denominator)
        if divisor > 1:
            object.__setattr__(self, "numerator", self.numerator // divisor)
            object.__setattr__(self, "denominator", self.denominator // divisor)
        if self.fraction > 100:
            raise ValueError("rational rate cannot exceed 100")
        return self

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    def __float__(self) -> float:
        return float(self.fraction)


@total_ordering
class RationalTime(BaseModel):
    """A signed integer value measured in ticks of a positive timescale."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: int
    timescale: int = Field(gt=0)

    @classmethod
    def zero(cls) -> RationalTime:
        return cls(value=0, timescale=1)

    @classmethod
    def from_fraction(cls, value: Fraction) -> RationalTime:
        return cls(value=value.numerator, timescale=value.denominator)

    @classmethod
    def from_seconds(cls, seconds: int | str | Decimal, timescale: int) -> RationalTime:
        """Convert boundary seconds exactly when representable at `timescale`."""
        decimal = seconds if isinstance(seconds, Decimal) else Decimal(str(seconds))
        ticks = decimal * timescale
        if ticks != ticks.to_integral_value():
            raise ValueError(f"{seconds!r} seconds is not exact at timescale {timescale}")
        return cls(value=int(ticks), timescale=timescale)

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.value, self.timescale)

    @property
    def seconds(self) -> float:
        return float(self.fraction)

    def rescaled_to(
        self,
        timescale: int,
        rounding: RoundingMode = RoundingMode.EXACT,
    ) -> RationalTime:
        if timescale <= 0:
            raise ValueError("timescale must be positive")
        target = self.fraction * timescale
        if target.denominator == 1:
            return RationalTime(value=target.numerator, timescale=timescale)
        if rounding is RoundingMode.EXACT:
            raise ValueError(f"{self} is not exactly representable at timescale {timescale}")
        if rounding is RoundingMode.FLOOR:
            value = target.numerator // target.denominator
        elif rounding is RoundingMode.CEIL:
            value = -(-target.numerator // target.denominator)
        else:
            value = math.floor(target + Fraction(1, 2))
        return RationalTime(value=value, timescale=timescale)

    def __add__(self, other: object) -> RationalTime:
        if not isinstance(other, RationalTime):
            return NotImplemented
        return RationalTime.from_fraction(self.fraction + other.fraction)

    def __sub__(self, other: object) -> RationalTime:
        if not isinstance(other, RationalTime):
            return NotImplemented
        return RationalTime.from_fraction(self.fraction - other.fraction)

    def __neg__(self) -> RationalTime:
        return RationalTime(value=-self.value, timescale=self.timescale)

    def __mul__(self, factor: int | Fraction) -> RationalTime:
        return RationalTime.from_fraction(self.fraction * factor)

    def __truediv__(self, divisor: int | Fraction) -> RationalTime:
        if divisor == 0:
            raise ZeroDivisionError
        return RationalTime.from_fraction(self.fraction / divisor)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, RationalTime):
            return NotImplemented
        return self.fraction < other.fraction

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RationalTime) and self.fraction == other.fraction

    def __hash__(self) -> int:
        return hash(self.fraction)


class TimeRange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start: RationalTime
    duration: RationalTime

    @model_validator(mode="after")
    def duration_is_nonnegative(self) -> Self:
        if self.duration.value < 0:
            raise ValueError("duration cannot be negative")
        return self

    @classmethod
    def from_start_end(cls, start: RationalTime, end: RationalTime) -> TimeRange:
        if end < start:
            raise ValueError("end cannot precede start")
        return cls(start=start, duration=end - start)

    @property
    def end(self) -> RationalTime:
        return self.start + self.duration

    @property
    def is_empty(self) -> bool:
        return self.duration.value == 0

    def contains(self, time: RationalTime, *, include_end: bool = False) -> bool:
        return self.start <= time <= self.end if include_end else self.start <= time < self.end

    def overlaps(self, other: TimeRange) -> bool:
        return self.start < other.end and other.start < self.end

    def intersection(self, other: TimeRange) -> TimeRange | None:
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        return None if end <= start else TimeRange.from_start_end(start, end)

    def shifted(self, offset: RationalTime) -> TimeRange:
        return TimeRange(start=self.start + offset, duration=self.duration)


class FrameRate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    numerator: int = Field(gt=0)
    denominator: int = Field(default=1, gt=0)

    @model_validator(mode="after")
    def normalize(self) -> Self:
        divisor = math.gcd(self.numerator, self.denominator)
        if divisor > 1:
            object.__setattr__(self, "numerator", self.numerator // divisor)
            object.__setattr__(self, "denominator", self.denominator // divisor)
        return self

    @classmethod
    def fps_23_976(cls) -> FrameRate:
        return cls(numerator=24_000, denominator=1_001)

    @classmethod
    def fps_29_97(cls) -> FrameRate:
        return cls(numerator=30_000, denominator=1_001)

    @classmethod
    def fps_59_94(cls) -> FrameRate:
        return cls(numerator=60_000, denominator=1_001)

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    @property
    def frames_per_second(self) -> float:
        return float(self.fraction)

    @property
    def frame_duration(self) -> RationalTime:
        return RationalTime(value=self.denominator, timescale=self.numerator)

    @property
    def nominal_fps(self) -> int:
        return round(self.frames_per_second)

    def frames_to_time(self, frames: int) -> RationalTime:
        return RationalTime(value=frames * self.denominator, timescale=self.numerator)

    def time_to_frames(
        self,
        time: RationalTime,
        rounding: RoundingMode = RoundingMode.EXACT,
    ) -> int:
        frames = time.fraction * self.fraction
        if frames.denominator == 1:
            return frames.numerator
        if rounding is RoundingMode.EXACT:
            raise ValueError(f"{time} does not land on a {self.numerator}/{self.denominator} frame")
        if rounding is RoundingMode.FLOOR:
            return frames.numerator // frames.denominator
        if rounding is RoundingMode.CEIL:
            return -(-frames.numerator // frames.denominator)
        return math.floor(frames + Fraction(1, 2))


class Timecode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    time: RationalTime
    rate: FrameRate
    drop_frame: bool = False

    @model_validator(mode="after")
    def validate_drop_frame_rate(self) -> Self:
        supported = {(30_000, 1_001), (60_000, 1_001)}
        if self.drop_frame and (self.rate.numerator, self.rate.denominator) not in supported:
            raise ValueError("drop-frame timecode is supported only at 29.97 and 59.94 fps")
        return self

    @classmethod
    def parse(
        cls,
        value: str,
        rate: FrameRate,
        *,
        drop_frame: bool | None = None,
    ) -> Timecode:
        match = re.fullmatch(r"(\d{2}):([0-5]\d):([0-5]\d)([:;])(\d{2})", value)
        if match is None:
            raise ValueError("timecode must be HH:MM:SS:FF or HH:MM:SS;FF")
        hours, minutes, seconds, separator, frame_field = match.groups()
        inferred_drop_frame = separator == ";"
        if drop_frame is not None and drop_frame is not inferred_drop_frame:
            raise ValueError("timecode separator disagrees with explicit drop-frame mode")
        drop_frame = inferred_drop_frame if drop_frame is None else drop_frame
        hours_value = int(hours)
        minutes_value = int(minutes)
        seconds_value = int(seconds)
        frames = int(frame_field)
        nominal = rate.nominal_fps
        if hours_value >= 24 or frames >= nominal:
            raise ValueError("timecode field is outside its valid range")
        total_minutes = hours_value * 60 + minutes_value
        frame_number = (
            (hours_value * 3600 + minutes_value * 60 + seconds_value) * nominal
        ) + frames
        if drop_frame:
            dropped = 2 if nominal == 30 else 4
            if (rate.numerator, rate.denominator) not in {
                (30_000, 1_001),
                (60_000, 1_001),
            }:
                raise ValueError("drop-frame timecode is supported only at 29.97 and 59.94 fps")
            if minutes_value % 10 != 0 and seconds_value == 0 and frames < dropped:
                raise ValueError("timecode uses a dropped frame label")
            frame_number -= dropped * (total_minutes - total_minutes // 10)
        return cls(time=rate.frames_to_time(frame_number), rate=rate, drop_frame=drop_frame)

    @property
    def frame_number(self) -> int:
        return self.rate.time_to_frames(self.time, RoundingMode.NEAREST)

    def __str__(self) -> str:
        nominal = self.rate.nominal_fps
        frames = self.frame_number
        if self.drop_frame:
            drop = 2 if nominal == 30 else 4
            frames_per_hour = nominal * 3600 - drop * 54
            frames_per_10_minutes = nominal * 600 - drop * 9
            frames_per_minute = nominal * 60 - drop
            frames %= frames_per_hour * 24
            ten_minute_blocks, remainder = divmod(frames, frames_per_10_minutes)
            minutes_in_block = (
                0
                if remainder < nominal * 60
                else 1 + (remainder - nominal * 60) // frames_per_minute
            )
            dropped_before = drop * (ten_minute_blocks * 9 + minutes_in_block)
            frames += dropped_before
        hours, remainder = divmod(frames, nominal * 3600)
        minutes, remainder = divmod(remainder, nominal * 60)
        seconds, frame = divmod(remainder, nominal)
        separator = ";" if self.drop_frame else ":"
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{frame:02d}"


class AudioSampleTime(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    samples: int
    sample_rate: int = Field(gt=0)

    @property
    def time(self) -> RationalTime:
        return RationalTime(value=self.samples, timescale=self.sample_rate)

    @classmethod
    def from_time(
        cls,
        time: RationalTime,
        sample_rate: int,
        rounding: RoundingMode = RoundingMode.EXACT,
    ) -> AudioSampleTime:
        scaled = time.rescaled_to(sample_rate, rounding)
        return cls(samples=scaled.value, sample_rate=sample_rate)

    def shifted(self, sample_offset: int) -> AudioSampleTime:
        return AudioSampleTime(samples=self.samples + sample_offset, sample_rate=self.sample_rate)
