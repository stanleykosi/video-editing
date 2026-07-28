"""Stable visual processing facade."""

from __future__ import annotations

import math
from collections.abc import Iterable
from itertools import pairwise

from video_engine.core.schema import (
    AnyTimelineItem,
    CaptionCollisionRegion,
    CaptionTrack,
    Clip,
    Effect,
    EffectKind,
    GeneratorClip,
    GraphicsTrack,
    Interpolation,
    JsonValue,
    Keyframe,
    NestedSequenceClip,
    Project,
    StillImageClip,
    Track,
    VideoTrack,
)
from video_engine.core.time import RationalTime, RoundingMode, TimeRange
from video_engine.errors import EngineError, ErrorCode
from video_engine.operations.models import (
    AddCaptionCollisionRegionOperation,
    AddEffectOperation,
    TimelineOperation,
    TimelinePatch,
)
from video_engine.visual.models import (
    NormalizedBox,
    NormalizedPoint,
    ReframePlan,
    ReframeSettings,
    TrackingBinding,
    TrackingBindingApplication,
    TrackingMappingEvidence,
    TrackingObservation,
    TrackingRequest,
    TrackingResult,
)
from video_engine.visual.reframing import ReframePlanner
from video_engine.visual.tracking import TrackingBackendRegistry, builtin_tracking_registry


class VisualService:
    def __init__(self, registry: TrackingBackendRegistry | None = None) -> None:
        self.registry = registry or builtin_tracking_registry()
        self._planner = ReframePlanner()

    def track(self, request: TrackingRequest, *, backend: str = "manual") -> TrackingResult:
        return self.registry.get(backend).track(request)

    def plan_reframe(
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
        return self._planner.plan(
            result,
            source_width=source_width,
            source_height=source_height,
            output_width=output_width,
            output_height=output_height,
            settings=settings,
            plan_id=plan_id,
        )

    @staticmethod
    def _clip_time(clip: Clip, source_time: RationalTime) -> RationalTime | None:
        if not clip.source_range.contains(source_time, include_end=True):
            return None
        source_offset = (
            clip.source_range.end - source_time
            if clip.retime.reverse
            else source_time - clip.source_range.start
        )
        return clip.retime.timeline_offset_at(source_offset, clip.timeline_range.duration)

    @staticmethod
    def _timeline_item(project: Project, sequence_id: str, item_id: str) -> AnyTimelineItem:
        for track in project.sequence(sequence_id).timeline.tracks:
            for item in track.items:
                if item.id == item_id:
                    return item
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "tracking binding references a missing timeline item",
            context={"item_id": item_id, "sequence_id": sequence_id},
        )

    @staticmethod
    def _timeline_item_location(
        project: Project, sequence_id: str, item_id: str
    ) -> tuple[Track, AnyTimelineItem]:
        for track in project.sequence(sequence_id).timeline.tracks:
            for item in track.items:
                if item.id == item_id:
                    return track, item
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "tracking binding references a missing timeline item",
            context={"item_id": item_id, "sequence_id": sequence_id},
        )

    @staticmethod
    def _padded_box(box: NormalizedBox, padding: float) -> NormalizedBox:
        horizontal = box.width * padding
        vertical = box.height * padding
        left = max(0.0, box.x - horizontal)
        top = max(0.0, box.y - vertical)
        right = min(1.0, box.x + box.width + horizontal)
        bottom = min(1.0, box.y + box.height + vertical)
        return NormalizedBox(x=left, y=top, width=right - left, height=bottom - top)

    @staticmethod
    def _project_box(box: NormalizedBox, binding: TrackingBinding) -> NormalizedBox:
        geometry = binding.geometry
        source_width = float(geometry.source_width)
        source_height = float(geometry.source_height)
        canvas_width = float(geometry.canvas_width)
        canvas_height = float(geometry.canvas_height)
        if geometry.fit.value == "stretch":
            scale_x = canvas_width / source_width
            scale_y = canvas_height / source_height
            offset_x = 0.0
            offset_y = 0.0
        else:
            candidate_x = canvas_width / source_width
            candidate_y = canvas_height / source_height
            scale = (
                max(candidate_x, candidate_y)
                if geometry.fit.value == "cover"
                else min(candidate_x, candidate_y)
            )
            if geometry.fit.value == "cover":
                scale *= geometry.zoom
                offset_x = (canvas_width - source_width * scale) * geometry.focus_x
                offset_y = (canvas_height - source_height * scale) * geometry.focus_y
            else:
                offset_x = (canvas_width - source_width * scale) / 2
                offset_y = (canvas_height - source_height * scale) / 2
            scale_x = scale_y = scale
        left = box.x * source_width * scale_x + offset_x
        top = box.y * source_height * scale_y + offset_y
        right = left + box.width * source_width * scale_x
        bottom = top + box.height * source_height * scale_y
        clipped_left = min(canvas_width, max(0.0, left))
        clipped_top = min(canvas_height, max(0.0, top))
        clipped_right = min(canvas_width, max(0.0, right))
        clipped_bottom = min(canvas_height, max(0.0, bottom))
        if clipped_right <= clipped_left or clipped_bottom <= clipped_top:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracked subject falls outside the configured output geometry",
                context={"binding_id": binding.id},
            )
        return NormalizedBox(
            x=clipped_left / canvas_width,
            y=clipped_top / canvas_height,
            width=(clipped_right - clipped_left) / canvas_width,
            height=(clipped_bottom - clipped_top) / canvas_height,
        )

    @staticmethod
    def _project_point(point: NormalizedPoint, binding: TrackingBinding) -> tuple[float, float]:
        geometry = binding.geometry
        source_width = float(geometry.source_width)
        source_height = float(geometry.source_height)
        canvas_width = float(geometry.canvas_width)
        canvas_height = float(geometry.canvas_height)
        if geometry.fit.value == "stretch":
            x = point.x * canvas_width
            y = point.y * canvas_height
        else:
            scale = (
                max(canvas_width / source_width, canvas_height / source_height)
                if geometry.fit.value == "cover"
                else min(canvas_width / source_width, canvas_height / source_height)
            )
            if geometry.fit.value == "cover":
                scale *= geometry.zoom
                offset_x = (canvas_width - source_width * scale) * geometry.focus_x
                offset_y = (canvas_height - source_height * scale) * geometry.focus_y
            else:
                offset_x = (canvas_width - source_width * scale) / 2
                offset_y = (canvas_height - source_height * scale) / 2
            x = point.x * source_width * scale + offset_x
            y = point.y * source_height * scale + offset_y
        return x / canvas_width, y / canvas_height

    @staticmethod
    def _reframe_values(
        box: NormalizedBox,
        *,
        source_width: int,
        source_height: int,
        canvas_width: int,
        canvas_height: int,
    ) -> dict[str, float]:
        base_scale = max(canvas_width / source_width, canvas_height / source_height)
        base_width = source_width * base_scale
        base_height = source_height * base_scale
        visible_width = canvas_width / base_width
        visible_height = canvas_height / base_height
        zoom = min(
            100.0,
            max(1.0, min(visible_width / box.width, visible_height / box.height)),
        )
        scaled_width = base_width * zoom
        scaled_height = base_height * zoom

        def focus(center: float, scaled: float, canvas: int) -> float:
            overflow = scaled - canvas
            if overflow <= 1e-9:
                return 0.5
            origin = center * scaled - canvas / 2
            return min(1.0, max(0.0, origin / overflow))

        return {
            "focus_x": focus(box.center.x, scaled_width, canvas_width),
            "focus_y": focus(box.center.y, scaled_height, canvas_height),
            "zoom": zoom,
        }

    @staticmethod
    def _effect_keyframes(
        effect_id: str,
        samples: Iterable[tuple[RationalTime, dict[str, float]]],
        interpolation: Interpolation,
    ) -> list[Keyframe]:
        return [
            Keyframe(
                id=f"{effect_id}-{index}-{property_path}",
                property_path=property_path,
                time=time,
                value=value,
                interpolation=interpolation,
            )
            for index, (time, values) in enumerate(samples)
            for property_path, value in values.items()
        ]

    @staticmethod
    def _interpolation_progress(progress: float, interpolation: Interpolation) -> float:
        if interpolation is Interpolation.HOLD:
            return 0.0
        if interpolation is Interpolation.EASE_IN:
            return progress * progress
        if interpolation is Interpolation.EASE_OUT:
            return 1 - (1 - progress) * (1 - progress)
        if interpolation in {Interpolation.EASE_IN_OUT, Interpolation.BEZIER}:
            return progress * progress * (3 - 2 * progress)
        return progress

    @classmethod
    def _interpolate_observation(
        cls,
        left: TrackingObservation,
        right: TrackingObservation,
        progress: float,
        interpolation: Interpolation,
        source_time: RationalTime,
    ) -> TrackingObservation:
        curved = cls._interpolation_progress(progress, interpolation)

        def value(start: float, end: float) -> float:
            return start + (end - start) * curved

        box: NormalizedBox | None = None
        focus: NormalizedPoint | None = None
        if left.box is not None and right.box is not None:
            box = NormalizedBox(
                x=value(left.box.x, right.box.x),
                y=value(left.box.y, right.box.y),
                width=value(left.box.width, right.box.width),
                height=value(left.box.height, right.box.height),
            )
        else:
            focus = NormalizedPoint(
                x=value(left.center.x, right.center.x),
                y=value(left.center.y, right.center.y),
            )
        return TrackingObservation(
            time=source_time,
            subject_id=left.subject_id,
            confidence=min(left.confidence, right.confidence),
            box=box,
            focus=focus,
            manual=left.manual and right.manual,
            extensions={"synthesized_target_boundary": True},
        )

    @staticmethod
    def _select_subject(
        result: TrackingResult,
        binding: TrackingBinding,
        source: Clip,
    ) -> tuple[str, list[TrackingObservation]]:
        candidates = [
            observation
            for observation in result.observations
            if source.source_range.contains(observation.time, include_end=True)
        ]
        eligible = [
            observation
            for observation in candidates
            if observation.confidence >= binding.minimum_confidence
        ]
        subjects = sorted({observation.subject_id for observation in eligible})
        if binding.subject_id is None:
            if len(subjects) != 1:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "tracking subject is ambiguous; subject_id is required",
                    context={"binding_id": binding.id, "eligible_subject_ids": subjects},
                )
            subject_id = subjects[0]
        else:
            subject_id = binding.subject_id
        selected = [observation for observation in eligible if observation.subject_id == subject_id]
        if not selected:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking binding has no eligible observations",
                context={
                    "binding_id": binding.id,
                    "subject_id": subject_id,
                    "minimum_confidence": binding.minimum_confidence,
                },
            )
        selected.sort(key=lambda observation: observation.time)
        rejected_between = [
            observation
            for observation in candidates
            if observation.subject_id == subject_id
            and observation.confidence < binding.minimum_confidence
            and selected[0].time < observation.time < selected[-1].time
        ]
        excessive_gaps = (
            []
            if binding.maximum_source_gap is None
            else [
                (left.time, right.time)
                for left, right in pairwise(selected)
                if right.time - left.time > binding.maximum_source_gap
            ]
        )
        if binding.missing_policy == "error" and (rejected_between or excessive_gaps):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking binding contains an unowned confidence or sampling gap",
                context={
                    "binding_id": binding.id,
                    "rejected_observation_times": [
                        observation.time.model_dump(mode="json") for observation in rejected_between
                    ],
                    "excessive_gaps": [
                        [left.model_dump(mode="json"), right.model_dump(mode="json")]
                        for left, right in excessive_gaps
                    ],
                },
            )
        return subject_id, selected

    def materialize_binding(
        self,
        project: Project,
        result: TrackingResult,
        binding: TrackingBinding,
        *,
        sequence_id: str | None = None,
    ) -> TrackingBindingApplication:
        """Compile canonical tracking observations into an auditable timeline patch."""

        target_sequence_id = sequence_id or project.active_sequence_id
        sequence = project.sequence(target_sequence_id)
        effective_frame_rate = sequence.settings_override.frame_rate or project.settings.frame_rate
        if binding.timeline_frame_rate != effective_frame_rate:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking binding frame rate does not match the target sequence",
                context={
                    "binding_id": binding.id,
                    "binding_frame_rate": binding.timeline_frame_rate.model_dump(mode="json"),
                    "sequence_frame_rate": effective_frame_rate.model_dump(mode="json"),
                },
            )
        if result.id != binding.tracking_result_id:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking result does not match the binding",
                context={"binding_id": binding.id, "tracking_result_id": result.id},
            )
        _source_track, source_item = self._timeline_item_location(
            project, target_sequence_id, binding.source_item_id
        )
        if not isinstance(source_item, Clip):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking bindings require a source-backed video clip",
                context={"item_id": binding.source_item_id},
            )
        if not source_item.enabled:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking binding source clip is disabled",
                context={"item_id": source_item.id},
            )
        if source_item.media_reference_id != result.media_reference_id:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking result media does not match the source clip",
                context={
                    "binding_id": binding.id,
                    "result_media_id": result.media_reference_id,
                    "clip_media_id": source_item.media_reference_id,
                },
            )
        media = next(item for item in project.media if item.id == source_item.media_reference_id)
        video_streams = [stream for stream in media.streams if stream.codec_type == "video"]
        if source_item.video_stream_index >= len(video_streams):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking binding source video dimensions are unavailable",
                context={"binding_id": binding.id, "media_reference_id": media.id},
            )
        source_stream = video_streams[source_item.video_stream_index]
        if source_stream.width is None or source_stream.height is None:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking binding source video dimensions are unavailable",
                context={"binding_id": binding.id, "media_reference_id": media.id},
            )
        display_width, display_height = source_stream.width, source_stream.height
        if media.rotation_degrees % 180:
            display_width, display_height = display_height, display_width
        if (binding.geometry.source_width, binding.geometry.source_height) != (
            display_width,
            display_height,
        ):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking binding source geometry does not match the media display dimensions",
                context={
                    "binding_id": binding.id,
                    "binding_dimensions": [
                        binding.geometry.source_width,
                        binding.geometry.source_height,
                    ],
                    "media_dimensions": [display_width, display_height],
                },
            )
        canvas_width = sequence.settings_override.width or project.settings.width
        canvas_height = sequence.settings_override.height or project.settings.height
        if (binding.geometry.canvas_width, binding.geometry.canvas_height) != (
            canvas_width,
            canvas_height,
        ):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking binding canvas geometry does not match the target sequence",
                context={
                    "binding_id": binding.id,
                    "binding_dimensions": [
                        binding.geometry.canvas_width,
                        binding.geometry.canvas_height,
                    ],
                    "sequence_dimensions": [canvas_width, canvas_height],
                },
            )
        reframe_effects = [
            effect
            for effect in source_item.effects
            if effect.enabled and effect.kind is EffectKind.REFRAME
        ]
        if binding.driver == "crop" and reframe_effects:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "crop tracking cannot add a second reframe effect",
                context={"binding_id": binding.id, "item_id": source_item.id},
            )
        if binding.driver != "crop":
            if len(reframe_effects) > 1:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "tracking source has multiple active reframe effects",
                    context={"binding_id": binding.id, "item_id": source_item.id},
                )
            expected_fit = "cover"
            raw_focus_x = source_item.extensions.get("focus_x", 0.5)
            raw_focus_y = source_item.extensions.get("focus_y", 0.5)
            if (
                isinstance(raw_focus_x, bool)
                or not isinstance(raw_focus_x, (str, int, float))
                or isinstance(raw_focus_y, bool)
                or not isinstance(raw_focus_y, (str, int, float))
            ):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "tracking source focus extensions must be numeric",
                    context={"binding_id": binding.id, "item_id": source_item.id},
                )
            expected_focus_x = float(raw_focus_x)
            expected_focus_y = float(raw_focus_y)
            expected_zoom = 1.0
            if reframe_effects:
                from video_engine.render.effects import ReframeParameters, parse_visual_parameters

                reframe = reframe_effects[0]
                if reframe.keyframes:
                    raise EngineError(
                        ErrorCode.UNSUPPORTED_CAPABILITY,
                        "tracking bindings cannot project through an animated source reframe",
                        context={"binding_id": binding.id, "effect_id": reframe.id},
                    )
                parsed_reframe = parse_visual_parameters(reframe)
                assert isinstance(parsed_reframe, ReframeParameters)
                if parsed_reframe.target_width is not None:
                    raise EngineError(
                        ErrorCode.UNSUPPORTED_CAPABILITY,
                        "tracking bindings cannot project through a panel-sized source reframe",
                        context={"binding_id": binding.id, "effect_id": reframe.id},
                    )
                expected_fit = parsed_reframe.fit
                expected_focus_x = parsed_reframe.focus_x
                expected_focus_y = parsed_reframe.focus_y
                expected_zoom = parsed_reframe.zoom
            else:
                profile_fits = {
                    profile.fit
                    for profile in project.delivery_profiles
                    if (profile.width, profile.height) == (canvas_width, canvas_height)
                }
                if len(profile_fits) > 1:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "tracking geometry is ambiguous across delivery profile fit modes",
                        context={"binding_id": binding.id, "fit_modes": sorted(profile_fits)},
                    )
                if profile_fits:
                    expected_fit = next(iter(profile_fits))
            actual_geometry = (
                binding.geometry.fit.value,
                binding.geometry.focus_x,
                binding.geometry.focus_y,
                binding.geometry.zoom,
            )
            expected_geometry = (
                expected_fit,
                expected_focus_x,
                expected_focus_y,
                expected_zoom,
            )
            if actual_geometry != expected_geometry:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "tracking geometry does not match the tracked source render geometry",
                    context={
                        "binding_id": binding.id,
                        "binding_geometry": list(actual_geometry),
                        "source_geometry": list(expected_geometry),
                    },
                )
        target_item: AnyTimelineItem | None = None
        target_track: Track | None = None
        if binding.target_item_id is not None:
            target_track, target_item = self._timeline_item_location(
                project, target_sequence_id, binding.target_item_id
            )
            if not isinstance(
                target_item,
                (
                    Clip,
                    GeneratorClip,
                    NestedSequenceClip,
                    StillImageClip,
                ),
            ):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "visual tracking binding requires a visual target item",
                    context={"item_id": binding.target_item_id},
                )
            if not target_item.enabled:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "tracking binding target item is disabled",
                    context={"item_id": target_item.id},
                )
            if binding.driver == "crop" and (
                target_item.id != source_item.id or not isinstance(target_item, Clip)
            ):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "crop tracking must target the tracked source clip",
                    context={"binding_id": binding.id, "target_item_id": target_item.id},
                )
            if binding.driver == "graphic_attachment" and not isinstance(
                target_track, GraphicsTrack
            ):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "graphic attachment tracking requires an item on a graphics track",
                    context={"binding_id": binding.id, "target_item_id": target_item.id},
                )
        else:
            caption_track = next(
                (
                    track
                    for track in sequence.timeline.tracks
                    if track.id == binding.target_track_id
                ),
                None,
            )
            if not isinstance(caption_track, CaptionTrack):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "caption-exclusion binding references a missing caption track",
                    context={"track_id": binding.target_track_id},
                )

        subject_id, observations = self._select_subject(result, binding, source_item)
        start_frame = effective_frame_rate.time_to_frames(
            source_item.timeline_range.start, RoundingMode.CEIL
        )
        end_frame = effective_frame_rate.time_to_frames(
            source_item.timeline_range.end, RoundingMode.FLOOR
        )
        mapped: list[
            tuple[
                TrackingObservation,
                TrackingMappingEvidence,
                NormalizedBox | None,
                NormalizedBox | None,
            ]
        ] = []
        for observation in observations:
            source_offset = (
                source_item.source_range.end - observation.time
                if source_item.retime.reverse
                else observation.time - source_item.source_range.start
            )
            local = source_item.retime.timeline_offset_at(
                source_offset,
                source_item.timeline_range.duration,
                timescale=binding.inverse_timescale,
            )
            raw_timeline_time = source_item.timeline_range.start + local
            frame_number = min(
                end_frame,
                max(
                    start_frame,
                    effective_frame_rate.time_to_frames(raw_timeline_time, RoundingMode.NEAREST),
                ),
            )
            timeline_time = effective_frame_rate.frames_to_time(frame_number)
            if target_item is not None:
                target_time = timeline_time - target_item.timeline_range.start
            else:
                target_time = timeline_time
            snapped_local = timeline_time - source_item.timeline_range.start
            snapped_offset = source_item.retime.source_offset_at(snapped_local)
            snapped_source_time = (
                source_item.source_range.end - snapped_offset
                if source_item.retime.reverse
                else source_item.source_range.start + snapped_offset
            )
            padded_box = (
                self._padded_box(observation.box, binding.padding_ratio)
                if observation.box is not None
                else None
            )
            projected_box = (
                self._project_box(padded_box, binding) if padded_box is not None else None
            )
            evidence = TrackingMappingEvidence(
                subject_id=subject_id,
                source_time=observation.time,
                timeline_time=timeline_time,
                target_time=target_time,
                frame_number=frame_number,
                source_mapping_error=snapped_source_time - observation.time,
                confidence=observation.confidence,
                manual=observation.manual,
            )
            mapped.append((observation, evidence, padded_box, projected_box))

        mapped.sort(key=lambda sample: (sample[1].timeline_time, sample[0].time))
        deduplicated: list[
            tuple[
                TrackingObservation,
                TrackingMappingEvidence,
                NormalizedBox | None,
                NormalizedBox | None,
            ]
        ] = []
        for sample in mapped:
            if deduplicated and sample[1].timeline_time == deduplicated[-1][1].timeline_time:
                previous = deduplicated[-1]
                if sample[0].box != previous[0].box or sample[0].center != previous[0].center:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "tracking observations collapse to conflicting geometry on one frame",
                        context={
                            "binding_id": binding.id,
                            "frame_number": sample[1].frame_number,
                        },
                    )
                if (sample[0].manual, sample[0].confidence) > (
                    previous[0].manual,
                    previous[0].confidence,
                ):
                    deduplicated[-1] = sample
                continue
            deduplicated.append(sample)
        mapped = deduplicated
        if target_item is not None:
            overlap = source_item.timeline_range.intersection(target_item.timeline_range)
            if overlap is None:
                mapped = []
            else:
                boundary_frames = {
                    effective_frame_rate.time_to_frames(overlap.start, RoundingMode.CEIL),
                    effective_frame_rate.time_to_frames(overlap.end, RoundingMode.FLOOR),
                }
                for boundary_frame in sorted(boundary_frames):
                    boundary = effective_frame_rate.frames_to_time(boundary_frame)
                    if any(sample[1].timeline_time == boundary for sample in mapped):
                        continue
                    left = next(
                        (
                            sample
                            for sample in reversed(mapped)
                            if sample[1].timeline_time < boundary
                        ),
                        None,
                    )
                    right = next(
                        (sample for sample in mapped if sample[1].timeline_time > boundary),
                        None,
                    )
                    local = boundary - source_item.timeline_range.start
                    source_offset = source_item.retime.source_offset_at(local)
                    source_time = (
                        source_item.source_range.end - source_offset
                        if source_item.retime.reverse
                        else source_item.source_range.start + source_offset
                    )
                    if left is None or right is None:
                        if boundary == overlap.start and binding.missing_policy == "error":
                            raise EngineError(
                                ErrorCode.INVALID_TIMELINE,
                                "tracking observations do not bracket the binding target start",
                                context={
                                    "binding_id": binding.id,
                                    "target_start": boundary.model_dump(mode="json"),
                                },
                            )
                        if binding.missing_policy != "hold":
                            continue
                        nearest = left or right
                        assert nearest is not None
                        observation = nearest[0].model_copy(
                            update={
                                "time": source_time,
                                "extensions": {"synthesized_target_boundary": True},
                            }
                        )
                    else:
                        span = right[1].timeline_time - left[1].timeline_time
                        progress = float(
                            (boundary - left[1].timeline_time).fraction / span.fraction
                        )
                        observation = self._interpolate_observation(
                            left[0],
                            right[0],
                            progress,
                            (
                                Interpolation.HOLD
                                if binding.missing_policy == "hold"
                                else binding.interpolation
                            ),
                            source_time,
                        )
                    padded_box = (
                        self._padded_box(observation.box, binding.padding_ratio)
                        if observation.box is not None
                        else None
                    )
                    projected_box = (
                        self._project_box(padded_box, binding) if padded_box is not None else None
                    )
                    mapped.append(
                        (
                            observation,
                            TrackingMappingEvidence(
                                subject_id=subject_id,
                                source_time=observation.time,
                                timeline_time=boundary,
                                target_time=boundary - target_item.timeline_range.start,
                                frame_number=boundary_frame,
                                source_mapping_error=RationalTime.zero(),
                                confidence=observation.confidence,
                                manual=observation.manual,
                            ),
                            padded_box,
                            projected_box,
                        )
                    )
                mapped.sort(key=lambda sample: (sample[1].timeline_time, sample[0].time))
                mapped = [
                    sample
                    for sample in mapped
                    if target_item.timeline_range.contains(
                        sample[1].timeline_time, include_end=True
                    )
                ]
        if not mapped:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "tracking observations do not overlap the binding target",
                context={"binding_id": binding.id},
            )

        operations: list[TimelineOperation] = []
        effect_ids: tuple[str, ...] = ()
        collision_region_ids: list[str] = []
        if binding.driver == "caption_exclusion":
            for index, sample in enumerate(mapped):
                box = sample[3]
                if box is None:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "caption exclusion tracking requires bounding boxes",
                        context={"binding_id": binding.id},
                    )
                start = sample[1].timeline_time
                end = (
                    mapped[index + 1][1].timeline_time
                    if index + 1 < len(mapped)
                    else source_item.timeline_range.end
                )
                if end <= start:
                    continue
                region_id = f"{binding.id}-collision-{index}"
                collision_region_ids.append(region_id)
                operations.append(
                    AddCaptionCollisionRegionOperation(
                        track_id=binding.target_track_id or "",
                        region=CaptionCollisionRegion(
                            id=region_id,
                            timeline_range=TimeRange.from_start_end(start, end),
                            x=box.x,
                            y=box.y,
                            width=box.width,
                            height=box.height,
                            kind=binding.caption_region_kind,
                            extensions={
                                "tracking_binding_id": binding.id,
                                "tracking_result_id": result.id,
                                "subject_id": subject_id,
                                "tracking_canvas_width": binding.geometry.canvas_width,
                                "tracking_canvas_height": binding.geometry.canvas_height,
                            },
                        ),
                    )
                )
            if not operations:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "tracking observations do not produce positive caption collision ranges",
                    context={"binding_id": binding.id},
                )
        else:
            assert target_item is not None and binding.target_item_id is not None
            effect_id = f"{binding.id}-{binding.driver}"
            sample_values: list[tuple[RationalTime, dict[str, float]]] = []
            parameters: dict[str, JsonValue]
            if binding.driver == "crop":
                for _, evidence, box, _ in mapped:
                    if box is None:
                        raise EngineError(
                            ErrorCode.INVALID_TIMELINE,
                            "crop tracking requires bounding boxes",
                            context={"binding_id": binding.id},
                        )
                    sample_values.append(
                        (
                            evidence.target_time,
                            self._reframe_values(
                                box,
                                source_width=binding.geometry.source_width,
                                source_height=binding.geometry.source_height,
                                canvas_width=binding.geometry.canvas_width,
                                canvas_height=binding.geometry.canvas_height,
                            ),
                        )
                    )
                kind = EffectKind.REFRAME
                parameters = {
                    "fit": "cover",
                    **sample_values[0][1],
                }
            elif binding.driver in {"position", "graphic_attachment"}:
                for observation, evidence, _, _ in mapped:
                    projected_x, projected_y = self._project_point(observation.center, binding)
                    center_x = projected_x * binding.geometry.canvas_width
                    center_y = projected_y * binding.geometry.canvas_height
                    direction = 1 if binding.driver == "graphic_attachment" else -1
                    sample_values.append(
                        (
                            evidence.target_time,
                            {
                                "x": direction * (center_x - binding.geometry.canvas_width / 2)
                                + binding.position_offset_x,
                                "y": direction * (center_y - binding.geometry.canvas_height / 2)
                                + binding.position_offset_y,
                            },
                        )
                    )
                kind = EffectKind.POSITION
                parameters = dict(sample_values[0][1])
            elif binding.driver == "mask":
                for _, evidence, _, box in mapped:
                    if box is None:
                        raise EngineError(
                            ErrorCode.INVALID_TIMELINE,
                            "mask tracking requires bounding boxes",
                            context={"binding_id": binding.id},
                        )
                    sample_values.append(
                        (
                            evidence.target_time,
                            {"x": box.x, "y": box.y, "width": box.width, "height": box.height},
                        )
                    )
                kind = EffectKind.MASK
                parameters = {
                    "shape": binding.mask_shape,
                    **sample_values[0][1],
                    "feather": binding.feather,
                    "invert": binding.mask_region == "outside",
                }
            else:
                assert binding.driver == "blur" and binding.blur_region is not None
                for _, evidence, _, box in mapped:
                    if box is None:
                        raise EngineError(
                            ErrorCode.INVALID_TIMELINE,
                            "selective blur tracking requires bounding boxes",
                            context={"binding_id": binding.id},
                        )
                    sample_values.append(
                        (
                            evidence.target_time,
                            {"x": box.x, "y": box.y, "width": box.width, "height": box.height},
                        )
                    )
                kind = EffectKind.BACKGROUND_BLUR
                parameters = {
                    "sigma": binding.blur_sigma,
                    "steps": binding.blur_steps,
                    "region_shape": binding.blur_shape,
                    "region_policy": binding.blur_region,
                    **sample_values[0][1],
                    "feather": binding.feather,
                }
            keyframe_interpolation = (
                Interpolation.HOLD if binding.missing_policy == "hold" else binding.interpolation
            )
            effect = Effect(
                id=effect_id,
                kind=kind,
                parameters=parameters,
                keyframes=self._effect_keyframes(effect_id, sample_values, keyframe_interpolation),
                extensions={
                    "tracking_binding_id": binding.id,
                    "tracking_result_id": result.id,
                    "tracking_source_item_id": source_item.id,
                    "subject_id": subject_id,
                    "tracking_canvas_width": binding.geometry.canvas_width,
                    "tracking_canvas_height": binding.geometry.canvas_height,
                    "tracking_source_width": binding.geometry.source_width,
                    "tracking_source_height": binding.geometry.source_height,
                },
            )
            operations.append(AddEffectOperation(item_id=binding.target_item_id, effect=effect))
            effect_ids = (effect_id,)

        mapping_evidence = tuple(sample[1] for sample in mapped)
        patch = TimelinePatch(
            patch_id=f"tracking-{binding.id}",
            sequence_id=target_sequence_id,
            expected_project_revision=project.revision,
            operations=operations,
            metadata={
                "tracking_binding_id": binding.id,
                "tracking_result_id": result.id,
                "subject_id": subject_id,
                "mapping_evidence": [item.model_dump(mode="json") for item in mapping_evidence],
            },
        )
        return TrackingBindingApplication(
            binding_id=binding.id,
            patch=patch,
            effect_ids=effect_ids,
            collision_region_ids=tuple(collision_region_ids),
            evidence=mapping_evidence,
        )

    @staticmethod
    def reframe_effect(
        plan: ReframePlan,
        *,
        effect_id: str = "tracked-reframe",
        clip: Clip | None = None,
    ) -> Effect:
        if plan.split_screen_panels:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "split-screen plans must be applied with split_screen_tracks",
                context={"plan_id": plan.id},
            )
        mapped_keyframes = []
        for item in plan.keyframes:
            if clip is None:
                mapped_keyframes.append((item.time, item))
                continue
            timeline_time = VisualService._clip_time(clip, item.time)
            if timeline_time is None:
                continue
            mapped_keyframes.append((timeline_time, item))
        mapped_keyframes.sort(key=lambda value: value[0])
        if not mapped_keyframes:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "reframe plan has no tracking samples inside the clip source range",
                context={
                    "plan_id": plan.id,
                    "clip_id": clip.id if clip is not None else None,
                },
            )
        first = mapped_keyframes[0][1]

        contain_fallback = any(decision.mode == "contain" for decision in plan.decisions)
        is_cover = plan.mode.value == "cover" and not contain_fallback
        first_values = VisualService._reframe_values(
            first.crop,
            source_width=plan.source_width,
            source_height=plan.source_height,
            canvas_width=plan.output_width,
            canvas_height=plan.output_height,
        )
        keyframes: list[Keyframe] = []
        selected_keyframes = mapped_keyframes if is_cover else ()
        for index, (timeline_time, item) in enumerate(selected_keyframes):
            values = VisualService._reframe_values(
                item.crop,
                source_width=plan.source_width,
                source_height=plan.source_height,
                canvas_width=plan.output_width,
                canvas_height=plan.output_height,
            )
            for property_path, value in values.items():
                keyframes.append(
                    Keyframe(
                        id=f"{effect_id}-{index}-{property_path}",
                        property_path=property_path,
                        time=timeline_time,
                        value=value,
                        interpolation=Interpolation.EASE_IN_OUT,
                    )
                )
        return Effect(
            id=effect_id,
            kind=EffectKind.REFRAME,
            parameters={
                "fit": "contain" if contain_fallback else plan.mode.value,
                "focus_x": first_values["focus_x"] if is_cover else 0.5,
                "focus_y": first_values["focus_y"] if is_cover else 0.5,
                "zoom": first_values["zoom"] if is_cover else 1.0,
            },
            keyframes=keyframes,
            extensions={"tracking_result_id": plan.tracking_result_id, "reframe_plan_id": plan.id},
        )

    @staticmethod
    def split_screen_tracks(
        plan: ReframePlan,
        clip: Clip,
        *,
        id_prefix: str = "tracked-split",
    ) -> tuple[VideoTrack, ...]:
        if not plan.split_screen_panels:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "reframe plan has no split-screen fallback panels",
                context={"plan_id": plan.id},
            )
        conflicting = [
            effect.id
            for effect in clip.effects
            if effect.enabled and effect.kind in {EffectKind.REFRAME, EffectKind.POSITION}
        ]
        if conflicting:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "split-screen application conflicts with existing position or reframe effects",
                context={"clip_id": clip.id, "effect_ids": conflicting},
            )
        subject_ids = sorted({panel.subject_id for panel in plan.split_screen_panels})
        columns = math.ceil(math.sqrt(len(subject_ids)))
        rows = math.ceil(len(subject_ids) / columns)
        panel_width = plan.output_width // columns
        panel_height = plan.output_height // rows
        tracks: list[VideoTrack] = []
        for index, subject_id in enumerate(subject_ids):
            source_panels = sorted(
                (panel for panel in plan.split_screen_panels if panel.subject_id == subject_id),
                key=lambda panel: panel.time,
            )
            mapped = [
                (timeline_time, panel)
                for panel in source_panels
                if (timeline_time := VisualService._clip_time(clip, panel.time)) is not None
            ]
            mapped.sort(key=lambda value: value[0])
            if not mapped:
                continue
            first = mapped[0][1]
            reframe = Effect(
                id=f"{id_prefix}-{index}-reframe",
                kind=EffectKind.REFRAME,
                parameters={
                    "fit": "cover",
                    "focus_x": first.crop.center.x,
                    "focus_y": first.crop.center.y,
                    "zoom": 1,
                    "target_width": panel_width,
                    "target_height": panel_height,
                },
                keyframes=[
                    Keyframe(
                        id=f"{id_prefix}-{index}-{keyframe_index}-{property_path}",
                        property_path=property_path,
                        time=timeline_time,
                        value=value,
                        interpolation=Interpolation.EASE_IN_OUT,
                    )
                    for keyframe_index, (timeline_time, panel) in enumerate(mapped)
                    for property_path, value in (
                        ("focus_x", panel.crop.center.x),
                        ("focus_y", panel.crop.center.y),
                    )
                ],
                extensions={"reframe_plan_id": plan.id, "subject_id": subject_id},
            )
            column = index % columns
            row = index // columns
            position = Effect(
                id=f"{id_prefix}-{index}-position",
                kind=EffectKind.POSITION,
                parameters={
                    "x": (column + 0.5) * panel_width - plan.output_width / 2,
                    "y": (row + 0.5) * panel_height - plan.output_height / 2,
                },
            )
            panel_clip = clip.model_copy(
                deep=True,
                update={
                    "id": f"{id_prefix}-{index}-{clip.id}",
                    "name": f"{clip.name} / {subject_id}",
                    "source_audio_enabled": clip.source_audio_enabled and index == 0,
                    "effects": [*clip.effects, reframe, position],
                    "extensions": {
                        **clip.extensions,
                        "reframe_plan_id": plan.id,
                        "tracked_subject_id": subject_id,
                    },
                },
            )
            tracks.append(
                VideoTrack(
                    id=f"{id_prefix}-{index}-track",
                    name=f"Split Screen / {subject_id}",
                    items=[panel_clip],
                )
            )
        if not tracks:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "split-screen panels do not overlap the clip source range",
                context={"plan_id": plan.id, "clip_id": clip.id},
            )
        return tuple(tracks)
