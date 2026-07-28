"""Deterministic chapter-aware planning for independently cacheable render sections."""

from __future__ import annotations

from itertools import pairwise

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import Marker, Sequence
from video_engine.core.time import AudioSampleTime, FrameRate, RationalTime, RoundingMode, TimeRange
from video_engine.errors import EngineError, ErrorCode


class RenderSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")
    index: int = Field(ge=0)
    timeline_range: TimeRange
    chapter_id: str | None = None

    @model_validator(mode="after")
    def positive_duration(self) -> RenderSection:
        if self.timeline_range.duration.value <= 0:
            raise ValueError("render section duration must be positive")
        return self


class SectionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence_id: str = Field(min_length=1)
    timeline_range: TimeRange
    sections: tuple[RenderSection, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def contiguous_coverage(self) -> SectionPlan:
        cursor = self.timeline_range.start
        for index, section in enumerate(self.sections):
            if section.index != index:
                raise ValueError("render section indices must be contiguous")
            if section.timeline_range.start != cursor:
                raise ValueError("render sections must be contiguous and ordered")
            cursor = section.timeline_range.end
        if cursor != self.timeline_range.end:
            raise ValueError("render sections must cover the requested range exactly")
        return self


def is_chapter_marker(marker: Marker) -> bool:
    return marker.extensions.get("kind") == "chapter" or marker.extensions.get("chapter") is True


def chapter_range(sequence: Sequence, chapter_id: str) -> TimeRange:
    chapters = sorted(
        (marker for marker in sequence.timeline.markers if is_chapter_marker(marker)),
        key=lambda marker: (marker.time, marker.id),
    )
    selected_index = next(
        (index for index, marker in enumerate(chapters) if marker.id == chapter_id), None
    )
    if selected_index is None:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "requested chapter marker was not found",
            context={"sequence_id": sequence.id, "chapter_id": chapter_id},
        )
    marker = chapters[selected_index]
    end = (
        marker.time + marker.duration
        if marker.duration is not None and marker.duration.value > 0
        else (
            chapters[selected_index + 1].time
            if selected_index + 1 < len(chapters)
            else sequence.timeline.duration
        )
    )
    if marker.time.value < 0 or end > sequence.timeline.duration or end <= marker.time:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "chapter marker has an invalid timeline range",
            context={"sequence_id": sequence.id, "chapter_id": chapter_id},
        )
    return TimeRange.from_start_end(marker.time, end)


class SectionPlanner:
    def __init__(
        self,
        *,
        frame_rate: FrameRate,
        audio_sample_rate: int,
        max_duration: RationalTime | None,
    ) -> None:
        if audio_sample_rate <= 0:
            raise ValueError("audio sample rate must be positive")
        if max_duration is not None and max_duration.value <= 0:
            raise ValueError("maximum section duration must be positive")
        self.frame_rate = frame_rate
        self.audio_sample_rate = audio_sample_rate
        self.max_duration = max_duration

    def plan(self, sequence: Sequence, timeline_range: TimeRange) -> SectionPlan:
        start_frame = self._exact_frame(timeline_range.start, "render start")
        end_frame = self._exact_frame(timeline_range.end, "render end")
        chapter_markers = sorted(
            (
                marker
                for marker in sequence.timeline.markers
                if is_chapter_marker(marker)
                and timeline_range.start < marker.time < timeline_range.end
            ),
            key=lambda marker: (marker.time, marker.id),
        )
        chapter_by_frame: dict[int, Marker] = {}
        hard_boundaries = {start_frame, end_frame}
        for marker in chapter_markers:
            frame = self._exact_frame(marker.time, f"chapter marker {marker.id!r}")
            self._exact_sample(marker.time, f"chapter marker {marker.id!r}")
            hard_boundaries.add(frame)
            chapter_by_frame[frame] = marker

        boundaries = sorted(hard_boundaries)
        planned_frames: list[int] = [boundaries[0]]
        for hard_end in boundaries[1:]:
            cursor = planned_frames[-1]
            while self.max_duration is not None:
                maximum_frames = self.frame_rate.time_to_frames(
                    self.max_duration, RoundingMode.FLOOR
                )
                if maximum_frames <= 0 or cursor + maximum_frames >= hard_end:
                    break
                candidate = self._sample_aligned_frame(cursor + maximum_frames, cursor)
                if candidate <= cursor:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "no frame and audio-sample aligned render section boundary exists",
                        context={"sequence_id": sequence.id, "after_frame": cursor},
                    )
                planned_frames.append(candidate)
                cursor = candidate
            planned_frames.append(hard_end)

        initial_chapter = self._chapter_at(sequence, timeline_range.start)
        current_chapter = initial_chapter.id if initial_chapter is not None else None
        sections: list[RenderSection] = []
        pairs = tuple(pairwise(planned_frames))
        for index, (left, right) in enumerate(pairs):
            boundary_marker = chapter_by_frame.get(left)
            if boundary_marker is not None:
                current_chapter = boundary_marker.id
            section_range = TimeRange.from_start_end(
                self.frame_rate.frames_to_time(left),
                self.frame_rate.frames_to_time(right),
            )
            if index > 0:
                self._exact_sample(section_range.start, "section start")
            if index + 1 < len(pairs):
                self._exact_sample(section_range.end, "section end")
            sections.append(
                RenderSection(
                    id=f"section-f{left}-f{right}",
                    index=index,
                    timeline_range=section_range,
                    chapter_id=current_chapter,
                )
            )
        return SectionPlan(
            sequence_id=sequence.id,
            timeline_range=timeline_range,
            sections=tuple(sections),
        )

    def _sample_aligned_frame(self, candidate: int, minimum: int) -> int:
        while candidate > minimum:
            time = self.frame_rate.frames_to_time(candidate)
            try:
                AudioSampleTime.from_time(time, self.audio_sample_rate, RoundingMode.EXACT)
                return candidate
            except ValueError:
                candidate -= 1
        return minimum

    def _exact_frame(self, time: RationalTime, label: str) -> int:
        try:
            return self.frame_rate.time_to_frames(time, RoundingMode.EXACT)
        except ValueError as exc:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                f"{label} is not aligned to the delivery frame grid",
                context={"time": time.model_dump(mode="json")},
            ) from exc

    def _exact_sample(self, time: RationalTime, label: str) -> int:
        try:
            return AudioSampleTime.from_time(
                time, self.audio_sample_rate, RoundingMode.EXACT
            ).samples
        except ValueError as exc:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                f"{label} is not aligned to the delivery audio sample grid",
                context={"time": time.model_dump(mode="json")},
            ) from exc

    @staticmethod
    def _chapter_at(sequence: Sequence, time: RationalTime) -> Marker | None:
        preceding = [
            marker
            for marker in sequence.timeline.markers
            if is_chapter_marker(marker) and marker.time <= time
        ]
        return max(preceding, key=lambda marker: (marker.time, marker.id), default=None)
