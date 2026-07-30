"""Translation from editorial segments to backend-neutral engine DTO payloads."""

from __future__ import annotations

from typing import Any, cast

from editorial_brain.core.models import AudioPictureRelationship, EditorialPlan, PlannedSegment
from video_engine.api import AudioClip, Clip, Marker, Project, RationalTime, Transition


def operation_payloads(
    project: Project,
    plan: EditorialPlan,
    video_track_id: str,
    audio_track_id: str,
) -> tuple[list[dict[str, object]], dict[str, list[int]]]:
    operations: list[dict[str, object]] = []
    decision_map: dict[str, list[int]] = {decision.id: [] for decision in plan.decisions}
    decision_by_select = {
        decision.selected_id: decision.id
        for decision in plan.decisions
        if decision.selected_id is not None
    }
    has_audio = {
        media.id: any(stream.codec_type == "audio" for stream in media.streams)
        for media in project.media
    }
    audio_items: dict[int, str] = {}
    video_items: dict[int, str] = {}
    if plan.narration_media_id is not None and plan.narration_source_range is not None:
        narration_item = AudioClip(
            id=f"brain-narration-{plan.id}",
            name="Editorial narration / voice-over",
            timeline_range=plan.narration_source_range.model_copy(
                update={"start": RationalTime.zero()}
            ),
            media_reference_id=plan.narration_media_id,
            source_range=plan.narration_source_range,
            extensions={
                "editorial_brain:plan_id": plan.id,
                "editorial_brain:role": "narration",
            },
        )
        operations.append(
            {"operation": "append", "track_id": audio_track_id, "item": narration_item}
        )
    for position, segment in enumerate(plan.assembly.segments):
        metadata = _metadata(plan, segment)
        video_item = Clip(
            id=f"brain-video-{plan.id}-{position:05d}",
            name=f"{segment.beat_id} / {segment.role}",
            timeline_range=segment.timeline_range,
            media_reference_id=segment.media_id,
            source_range=segment.source_range,
            source_audio_enabled=(
                plan.narration_media_id is None and not has_audio.get(segment.media_id, False)
            ),
            extensions=metadata,
        )
        video_items[position] = video_item.id
        _record(
            operations,
            {"operation": "append", "track_id": video_track_id, "item": video_item},
            decision_map,
            decision_by_select.get(segment.select_id),
        )
        if plan.narration_media_id is None and has_audio.get(segment.media_id, False):
            audio_item_id = f"brain-audio-{plan.id}-{position:05d}"
            audio_items[position] = audio_item_id
            audio_item = AudioClip(
                id=audio_item_id,
                name=f"{segment.beat_id} source audio",
                timeline_range=segment.timeline_range,
                media_reference_id=segment.media_id,
                source_range=segment.source_range,
                replaces_embedded_audio_item_id=video_item.id,
                extensions=metadata,
            )
            _record(
                operations,
                {"operation": "append", "track_id": audio_track_id, "item": audio_item},
                decision_map,
                decision_by_select.get(segment.select_id),
            )
        marker = Marker(
            id=f"brain-marker-{plan.id}-{position:05d}",
            time=segment.timeline_range.start,
            duration=segment.timeline_range.duration,
            name=segment.beat_id,
            comment=f"{segment.role}; select={segment.select_id}",
            extensions=metadata,
        )
        _record(
            operations,
            {"operation": "add_marker", "target_type": "timeline", "marker": marker},
            decision_map,
            decision_by_select.get(segment.select_id),
        )
    for position, segment in enumerate(plan.assembly.segments):
        relation = segment.audio_relationship
        if relation is AudioPictureRelationship.J_CUT and position in audio_items:
            extension = _start_extension(segment)
            if extension.value > 0:
                operations.append(
                    {
                        "operation": "j_cut",
                        "audio_track_id": audio_track_id,
                        "audio_item_id": audio_items[position],
                        "extension": extension,
                    }
                )
                _map_boundary_operation(operations, decision_map, plan, position)
        if position > 0 and segment.transition not in {"cut", "none"}:
            duration = min(
                RationalTime(value=1, timescale=4),
                segment.timeline_range.duration / 4,
                plan.assembly.segments[position - 1].timeline_range.duration / 4,
            )
            operations.append(
                {
                    "operation": "add_transition",
                    "track_id": video_track_id,
                    "transition": Transition(
                        id=f"brain-transition-{plan.id}-{position:05d}",
                        # The editorial enum is deliberately a strict subset of the
                        # engine enum. Pydantic performs the public DTO conversion.
                        kind=cast(Any, segment.transition),
                        from_item_id=video_items[position - 1],
                        to_item_id=video_items[position],
                        duration=duration,
                        extensions={
                            "editorial_brain:plan_id": plan.id,
                            "editorial_brain:motivation": "planned_editorial_transition",
                        },
                    ),
                }
            )
            _map_boundary_operation(operations, decision_map, plan, position)
        if (
            position > 0
            and segment.audio_relationship is AudioPictureRelationship.AUDIO_BRIDGE
            and position - 1 in audio_items
            and position in audio_items
        ):
            operations.append(
                {
                    "operation": "audio_crossfade",
                    "track_id": audio_track_id,
                    "left_item_id": audio_items[position - 1],
                    "right_item_id": audio_items[position],
                    "duration": RationalTime(value=1, timescale=10),
                    "transition_id": f"brain-audio-bridge-{plan.id}-{position:05d}",
                }
            )
            _map_boundary_operation(operations, decision_map, plan, position)
        if (
            relation
            in {
                AudioPictureRelationship.L_CUT,
                AudioPictureRelationship.REACTION_CONTINUING_DIALOGUE,
                AudioPictureRelationship.AMBIENCE_CONTINUATION,
            }
            and position - 1 in audio_items
        ):
            extension = _end_extension(plan.assembly.segments[position - 1], segment)
            if extension.value > 0:
                operations.append(
                    {
                        "operation": "l_cut",
                        "audio_track_id": audio_track_id,
                        "audio_item_id": audio_items[position - 1],
                        "extension": extension,
                    }
                )
                _map_boundary_operation(operations, decision_map, plan, position)
    return operations, decision_map


def _metadata(plan: EditorialPlan, segment: PlannedSegment) -> dict[str, Any]:
    return {
        "editorial_brain:plan_id": plan.id,
        "editorial_brain:beat_id": segment.beat_id,
        "editorial_brain:select_id": segment.select_id,
        "editorial_brain:role": segment.role,
        "editorial_brain:confidence": segment.confidence.score,
        "editorial_brain:evidence_ids": [item.id for item in segment.evidence],
    }


def _record(
    operations: list[dict[str, object]],
    payload: dict[str, object],
    decision_map: dict[str, list[int]],
    decision_id: str | None,
) -> None:
    index = len(operations)
    operations.append(payload)
    if decision_id is not None:
        decision_map[decision_id].append(index)


def _map_boundary_operation(
    operations: list[dict[str, object]],
    decision_map: dict[str, list[int]],
    plan: EditorialPlan,
    position: int,
) -> None:
    if position <= 0:
        return
    decision_id = f"decision:{plan.assembly.id}:cut:{position - 1:04d}"
    if decision_id in decision_map:
        decision_map[decision_id].append(len(operations) - 1)


def _start_extension(segment: PlannedSegment) -> RationalTime:
    if segment.audio_source_range is None:
        return RationalTime.zero()
    return max(RationalTime.zero(), segment.source_range.start - segment.audio_source_range.start)


def _end_extension(previous: PlannedSegment, incoming: PlannedSegment) -> RationalTime:
    if incoming.audio_source_range is None:
        return RationalTime.zero()
    return max(RationalTime.zero(), incoming.audio_source_range.end - previous.source_range.end)
