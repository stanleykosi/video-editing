"""Deterministic subject-aware crop planning."""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from video_engine.core.time import RationalTime
from video_engine.visual.models import (
    CropKeyframe,
    MultiSubjectFallback,
    NormalizedBox,
    ReframeDecision,
    ReframeMode,
    ReframePlan,
    ReframeSettings,
    SplitScreenPanel,
    TrackingObservation,
    TrackingResult,
)


def _union_box(observations: list[TrackingObservation]) -> NormalizedBox:
    boxes = [item.box for item in observations if item.box is not None]
    if not boxes:
        centers = [item.center for item in observations]
        left = min(point.x for point in centers)
        right = max(point.x for point in centers)
        top = min(point.y for point in centers)
        bottom = max(point.y for point in centers)
        padding = 0.05
        x = max(0, left - padding)
        y = max(0, top - padding)
        return NormalizedBox(
            x=x,
            y=y,
            width=min(1 - x, max(2 * padding, right - left + 2 * padding)),
            height=min(1 - y, max(2 * padding, bottom - top + 2 * padding)),
        )
    left = min(box.x for box in boxes)
    top = min(box.y for box in boxes)
    right = max(box.x + box.width for box in boxes)
    bottom = max(box.y + box.height for box in boxes)
    return NormalizedBox(x=left, y=top, width=right - left, height=bottom - top)


def _centered_crop(
    center_x: float,
    center_y: float,
    required_width: float,
    required_height: float,
    source_width: int,
    source_height: int,
    output_width: int,
    output_height: int,
) -> NormalizedBox:
    normalized_aspect = (output_width / output_height) / (source_width / source_height)
    width = max(required_width, required_height * normalized_aspect)
    if width <= 0:
        width = min(1, normalized_aspect)
        height = min(1, 1 / normalized_aspect)
    else:
        height = width / normalized_aspect
    if height > 1:
        height = 1
        width = min(1, normalized_aspect)
    if width > 1:
        width = 1
        height = min(1, 1 / normalized_aspect)
    x = min(max(0, center_x - width / 2), 1 - width)
    y = min(max(0, center_y - height / 2), 1 - height)
    return NormalizedBox(x=x, y=y, width=width, height=height)


def _smooth_box(previous: NormalizedBox, current: NormalizedBox, amount: float) -> NormalizedBox:
    retain = amount
    apply = 1 - amount
    width = previous.width * retain + current.width * apply
    height = previous.height * retain + current.height * apply
    center_x = previous.center.x * retain + current.center.x * apply
    center_y = previous.center.y * retain + current.center.y * apply
    x = min(max(0, center_x - width / 2), 1 - width)
    y = min(max(0, center_y - height / 2), 1 - height)
    return NormalizedBox(x=x, y=y, width=width, height=height)


class ReframePlanner:
    def plan(
        self,
        result: TrackingResult,
        *,
        source_width: int,
        source_height: int,
        output_width: int,
        output_height: int,
        settings: ReframeSettings | None = None,
        plan_id: str | None = None,
    ) -> ReframePlan:
        options = settings or ReframeSettings()
        grouped: dict[RationalTime, list[TrackingObservation]] = defaultdict(list)
        for observation in result.observations:
            grouped[observation.time].append(observation)
        keyframes: list[CropKeyframe] = []
        panels: list[SplitScreenPanel] = []
        decisions: list[ReframeDecision] = []
        previous: NormalizedBox | None = None
        for time in sorted(grouped):
            decision_mode: Literal["tracked", "center", "contain", "split_screen"]
            observed = grouped[time]
            confident = [item for item in observed if item.confidence >= options.minimum_confidence]
            if options.mode in {ReframeMode.CONTAIN, ReframeMode.STRETCH}:
                crop = NormalizedBox(x=0, y=0, width=1, height=1)
                decision_mode = "contain" if options.mode is ReframeMode.CONTAIN else "center"
                reason = f"{options.mode.value} mode uses the full source frame"
                selected = confident
            elif not confident:
                crop = _centered_crop(
                    0.5,
                    0.5,
                    0,
                    0,
                    source_width,
                    source_height,
                    output_width,
                    output_height,
                )
                decision_mode = "center"
                reason = "no observation met the confidence threshold"
                selected = []
            else:
                selected = confident
                subject_box = _union_box(confident)
                span = max(subject_box.width, subject_box.height)
                if (
                    len({item.subject_id for item in confident}) > 1
                    and span > options.multi_subject_max_span
                    and options.multi_subject_fallback is MultiSubjectFallback.SPLIT_SCREEN
                ):
                    crop = NormalizedBox(x=0, y=0, width=1, height=1)
                    decision_mode = "split_screen"
                    reason = "subjects exceed the configured shared-crop span"
                    for item in confident:
                        box = item.box or NormalizedBox(
                            x=max(0, item.center.x - 0.05),
                            y=max(0, item.center.y - 0.05),
                            width=min(0.1, 1 - max(0, item.center.x - 0.05)),
                            height=min(0.1, 1 - max(0, item.center.y - 0.05)),
                        )
                        panel_crop = _centered_crop(
                            box.center.x,
                            box.center.y,
                            min(1, box.width + options.subject_margin),
                            min(1, box.height + options.subject_margin),
                            source_width,
                            source_height,
                            output_width,
                            output_height,
                        )
                        panels.append(
                            SplitScreenPanel(
                                time=time,
                                subject_id=item.subject_id,
                                crop=panel_crop,
                                confidence=item.confidence,
                            )
                        )
                elif (
                    len({item.subject_id for item in confident}) > 1
                    and span > options.multi_subject_max_span
                    and options.multi_subject_fallback is MultiSubjectFallback.CONTAIN
                ):
                    crop = NormalizedBox(x=0, y=0, width=1, height=1)
                    decision_mode = "contain"
                    reason = "subjects exceed the configured shared-crop span"
                elif (
                    len({item.subject_id for item in confident}) > 1
                    and span > options.multi_subject_max_span
                    and options.multi_subject_fallback is MultiSubjectFallback.CENTER
                ):
                    crop = _centered_crop(
                        0.5,
                        0.5,
                        0,
                        0,
                        source_width,
                        source_height,
                        output_width,
                        output_height,
                    )
                    decision_mode = "center"
                    reason = "subjects exceed the shared crop; using centered fallback"
                else:
                    crop = _centered_crop(
                        subject_box.center.x,
                        subject_box.center.y,
                        min(1, subject_box.width + options.subject_margin),
                        min(1, subject_box.height + options.subject_margin),
                        source_width,
                        source_height,
                        output_width,
                        output_height,
                    )
                    decision_mode = "tracked"
                    reason = "crop follows confident subject geometry"
            if previous is not None and decision_mode == "tracked":
                crop = _smooth_box(previous, crop, options.smoothing)
            previous = crop
            subject_ids = tuple(sorted({item.subject_id for item in selected}))
            confidence = min((item.confidence for item in selected), default=0)
            keyframes.append(
                CropKeyframe(
                    time=time,
                    crop=crop,
                    confidence=confidence,
                    subject_ids=subject_ids,
                    manual=any(item.manual for item in selected),
                )
            )
            decisions.append(
                ReframeDecision(
                    time=time,
                    mode=decision_mode,
                    reason=reason,
                    subject_ids=subject_ids,
                )
            )
        return ReframePlan(
            id=plan_id or f"reframe-{result.id}",
            tracking_result_id=result.id,
            source_width=source_width,
            source_height=source_height,
            output_width=output_width,
            output_height=output_height,
            mode=options.mode,
            keyframes=tuple(keyframes),
            split_screen_panels=tuple(panels),
            decisions=tuple(decisions),
        )
