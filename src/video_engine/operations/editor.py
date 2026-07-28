"""Atomic operation executor with audit, inverse patches, undo, and redo."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

from video_engine.core.schema import (
    AdjustmentClip,
    AdjustmentTrack,
    AnyTimelineItem,
    AudioClip,
    AudioTrack,
    CaptionCue,
    CaptionTrack,
    Clip,
    Effect,
    EffectKind,
    Gap,
    GeneratorClip,
    GraphicsTrack,
    LinkGroup,
    Marker,
    NestedSequenceClip,
    Project,
    Retime,
    Sequence,
    SequenceSnapshot,
    StillImageClip,
    Timeline,
    Track,
    Transition,
    TransitionKind,
    VideoTrack,
)
from video_engine.core.time import FrameRate, RationalTime, TimeRange
from video_engine.core.validation import validate_project
from video_engine.errors import EngineError, ErrorCode
from video_engine.operations.models import (
    AddCaptionCollisionRegionOperation,
    AddEffectOperation,
    AddKeyframeOperation,
    AddMarkerOperation,
    AddTransitionOperation,
    AppendOperation,
    AudioCrossfadeOperation,
    AudioExtensionOperation,
    AuditEntry,
    DisableOperation,
    DuplicateOperation,
    EnableOperation,
    ExtractOperation,
    GroupOperation,
    HistoryResult,
    InsertOperation,
    JCutOperation,
    LCutOperation,
    LiftOperation,
    LinkOperation,
    MoveOperation,
    NestOperation,
    OperationKind,
    OperationResult,
    OverwriteOperation,
    PatchResult,
    RemoveCaptionCollisionRegionOperation,
    RemoveEffectOperation,
    RemoveKeyframeOperation,
    RemoveMarkerOperation,
    RemoveTransitionOperation,
    ReplaceOperation,
    RestoreProjectOperation,
    RippleDeleteOperation,
    RippleTrimOperation,
    RollOperation,
    SlideOperation,
    SlipOperation,
    SplitOperation,
    TimelineOperation,
    TimelinePatch,
    TrimOperation,
    UngroupOperation,
    UnlinkOperation,
    UnnestOperation,
)


def _invalid(message: str, **context: object) -> EngineError:
    return EngineError(ErrorCode.INVALID_OPERATION, message, context=dict(context))


def _items(track: Track) -> list[AnyTimelineItem]:
    return cast(list[AnyTimelineItem], track.items)


def _transitions(track: Track) -> list[Transition]:
    if not hasattr(track, "transitions"):
        raise _invalid("track type does not support transitions", track_id=track.id)
    return cast(list[Transition], track.transitions)


def _find_track(timeline: Timeline, track_id: str) -> Track:
    for track in timeline.tracks:
        if track.id == track_id:
            return track
    raise _invalid("track was not found", track_id=track_id)


def _find_item(timeline: Timeline, item_id: str) -> tuple[Track, AnyTimelineItem]:
    for track in timeline.tracks:
        for item in _items(track):
            if item.id == item_id:
                return track, item
    raise _invalid("timeline item was not found", item_id=item_id)


def _track_item(track: Track, item_id: str) -> AnyTimelineItem:
    for item in _items(track):
        if item.id == item_id:
            return item
    raise _invalid("item was not found on track", track_id=track.id, item_id=item_id)


def _assert_unlocked(track: Track, item: AnyTimelineItem | None = None) -> None:
    if track.locked:
        raise _invalid("track is locked", track_id=track.id)
    if item is not None and item.locked:
        raise _invalid("item is locked", track_id=track.id, item_id=item.id)


def _compatible(track: Track, item: AnyTimelineItem) -> bool:
    if isinstance(track, VideoTrack):
        return isinstance(item, (Clip, Gap, NestedSequenceClip, GeneratorClip, StillImageClip))
    if isinstance(track, AudioTrack):
        return isinstance(item, (AudioClip, Gap))
    if isinstance(track, CaptionTrack):
        return isinstance(item, (CaptionCue, Gap))
    if isinstance(track, GraphicsTrack):
        return isinstance(item, (Clip, Gap, GeneratorClip, StillImageClip))
    if isinstance(track, AdjustmentTrack):
        return isinstance(item, (AdjustmentClip, Gap))


def _assert_compatible(track: Track, item: AnyTimelineItem) -> None:
    if not _compatible(track, item):
        raise _invalid(
            "item type is incompatible with track",
            track_id=track.id,
            track_type=track.track_type,
            item_id=item.id,
            item_type=item.item_type,
        )


def _source_range(item: AnyTimelineItem) -> TimeRange | None:
    if isinstance(item, (Clip, AudioClip, NestedSequenceClip)):
        return item.source_range
    return None


def _validated_item_update(item: AnyTimelineItem, **updates: object) -> None:
    payload = item.model_dump(mode="python")
    payload.update(updates)
    validated = type(item).model_validate(payload)
    for field_name in updates:
        object.__setattr__(item, field_name, getattr(validated, field_name))


def _set_source_range(
    item: AnyTimelineItem,
    source_range: TimeRange,
    *,
    effects: list[Effect] | None = None,
) -> None:
    if isinstance(item, (Clip, AudioClip, NestedSequenceClip)):
        updates: dict[str, object] = {"source_range": source_range}
        if effects is not None:
            updates["effects"] = effects
        _validated_item_update(item, **updates)


def _set_item_ranges(
    item: AnyTimelineItem,
    timeline_range: TimeRange,
    source_range: TimeRange,
    *,
    retime: Retime | None = None,
    effects: list[Effect] | None = None,
) -> None:
    if not isinstance(item, (Clip, AudioClip, NestedSequenceClip)):
        raise _invalid("timeline item does not have a source range", item_id=item.id)
    updates: dict[str, object] = {
        "timeline_range": timeline_range,
        "source_range": source_range,
    }
    if retime is not None:
        updates["retime"] = retime
    if effects is not None:
        updates["effects"] = effects
    _validated_item_update(item, **updates)


def _shift_item(item: AnyTimelineItem, offset: RationalTime) -> None:
    shifted = item.timeline_range.shifted(offset)
    if shifted.start.value < 0:
        raise _invalid("operation would move an item before timeline zero", item_id=item.id)
    item.timeline_range = shifted


def _freeze_effects_for_trim(
    item: Clip,
    new_duration: RationalTime,
    frame_rate: FrameRate,
) -> list[Effect]:
    frame_duration = frame_rate.frames_to_time(1)
    updated: list[Effect] = []
    for effect in item.effects:
        if not effect.enabled or effect.kind is not EffectKind.FREEZE:
            updated.append(effect.model_copy(deep=True))
            continue
        parameters = dict(effect.parameters)
        frame_time = RationalTime.model_validate(parameters["frame_time"])
        if parameters.get("source_range") is None:
            try:
                frame_rate.time_to_frames(frame_time)
            except ValueError as exc:
                raise _invalid(
                    "freeze frame time must align to the sequence frame grid",
                    item_id=item.id,
                    effect_id=effect.id,
                ) from exc
            source_offset_start = item.retime.source_offset_at(frame_time)
            source_offset_end = item.retime.source_offset_at(frame_time + frame_duration)
            if source_offset_end > item.source_range.duration:
                raise _invalid(
                    "freeze frame time lies outside the owning source context",
                    item_id=item.id,
                    effect_id=effect.id,
                )
            source_start = (
                item.source_range.end - source_offset_end
                if item.retime.reverse
                else item.source_range.start + source_offset_start
            )
            parameters["source_range"] = TimeRange(
                start=source_start,
                duration=source_offset_end - source_offset_start,
            ).model_dump(mode="json")
            parameters["source_reverse"] = item.retime.reverse
        parameters["duration"] = new_duration.model_dump(mode="json")
        updated.append(effect.model_copy(deep=True, update={"parameters": parameters}))
    return updated


def _trim_item(
    item: AnyTimelineItem,
    new_range: TimeRange,
    frame_rate: FrameRate | None = None,
) -> None:
    if new_range.duration.value <= 0 or new_range.start.value < 0:
        raise _invalid("trimmed range must be positive and nonnegative", item_id=item.id)
    old_range = item.timeline_range
    start_delta = new_range.start - old_range.start
    source = _source_range(item)
    if source is not None:
        assert isinstance(item, (Clip, AudioClip, NestedSequenceClip))
        effects = None
        if isinstance(item, Clip) and any(
            effect.enabled and effect.kind is EffectKind.FREEZE for effect in item.effects
        ):
            if frame_rate is None:
                raise _invalid(
                    "editing a frozen clip requires the sequence frame rate",
                    item_id=item.id,
                )
            effects = _freeze_effects_for_trim(item, new_range.duration, frame_rate)
        relative_end = new_range.end - old_range.start
        source_offset_start = item.retime.source_offset_at(start_delta)
        source_offset_end = item.retime.source_offset_at(relative_end)
        if item.retime.reverse:
            new_source_start = source.end - source_offset_end
        else:
            new_source_start = source.start + source_offset_start
        if new_source_start.value < 0:
            raise _invalid("trim would move before source zero", item_id=item.id)
        new_retime = item.retime.window(start_delta, new_range.duration)
        _set_item_ranges(
            item,
            new_range,
            TimeRange(
                start=new_source_start,
                duration=source_offset_end - source_offset_start,
            ),
            retime=new_retime,
            effects=effects,
        )
    else:
        item.timeline_range = new_range


def _split_item(
    item: AnyTimelineItem,
    at: RationalTime,
    left_id: str,
    right_id: str,
    frame_rate: FrameRate | None = None,
) -> tuple[AnyTimelineItem, AnyTimelineItem]:
    if not item.timeline_range.contains(at) or at == item.timeline_range.start:
        raise _invalid("split point must be strictly inside the item", item_id=item.id)
    left = item.model_copy(deep=True, update={"id": left_id})
    right = item.model_copy(deep=True, update={"id": right_id})
    _trim_item(
        left,
        TimeRange.from_start_end(item.timeline_range.start, at),
        frame_rate,
    )
    _trim_item(
        right,
        TimeRange.from_start_end(at, item.timeline_range.end),
        frame_rate,
    )
    return left, right


def _unique_internal_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _sort_track(track: Track) -> None:
    _items(track).sort(key=lambda item: (item.timeline_range.start, item.id))


def _prune_transitions(track: Track) -> None:
    if not hasattr(track, "transitions"):
        return
    ids = {item.id for item in _items(track)}
    transitions = _transitions(track)
    transitions[:] = [
        transition
        for transition in transitions
        if transition.from_item_id in ids and transition.to_item_id in ids
    ]


def _cut_track_range(
    track: Track,
    cut: TimeRange,
    *,
    ripple: bool,
    frame_rate: FrameRate | None = None,
) -> None:
    result: list[AnyTimelineItem] = []
    for item in list(_items(track)):
        item_range = item.timeline_range
        if not item_range.overlaps(cut):
            if ripple and item_range.start >= cut.end:
                _shift_item(item, -cut.duration)
            result.append(item)
            continue
        keeps_left = item_range.start < cut.start
        keeps_right = item_range.end > cut.end
        if keeps_left and keeps_right:
            left, right = _split_item(
                item,
                cut.start,
                item.id,
                _unique_internal_id(f"{item.id}-right"),
                frame_rate,
            )
            _trim_item(
                right,
                TimeRange.from_start_end(cut.end, item_range.end),
                frame_rate,
            )
            if ripple:
                _shift_item(right, -cut.duration)
            result.extend([left, right])
        elif keeps_left:
            _trim_item(
                item,
                TimeRange.from_start_end(item_range.start, cut.start),
                frame_rate,
            )
            result.append(item)
        elif keeps_right:
            _trim_item(
                item,
                TimeRange.from_start_end(cut.end, item_range.end),
                frame_rate,
            )
            if ripple:
                _shift_item(item, -cut.duration)
            result.append(item)
    _items(track)[:] = result
    _sort_track(track)
    _prune_transitions(track)


def _track_end(track: Track) -> RationalTime:
    return max(
        (item.timeline_range.end for item in _items(track)),
        default=RationalTime.zero(),
    )


def _effect(timeline: Timeline, effect_id: str) -> tuple[AnyTimelineItem, Effect]:
    for track in timeline.tracks:
        for item in _items(track):
            for effect in item.effects:
                if effect.id == effect_id:
                    return item, effect
    raise _invalid("effect was not found", effect_id=effect_id)


def _marker_target(timeline: Timeline, target_type: str, target_id: str | None) -> list[Marker]:
    if target_type == "timeline":
        if target_id is not None:
            raise _invalid("timeline marker target_id must be null")
        return timeline.markers
    if target_id is None:
        raise _invalid("item marker requires target_id")
    return _find_item(timeline, target_id)[1].markers


class TimelineEditor:
    def __init__(self, project: Project) -> None:
        self.project = project.model_copy(deep=True)
        self.audit_log: list[AuditEntry] = []
        self._undo_stack: list[Project] = []
        self._redo_stack: list[Project] = []

    def apply_operation(
        self,
        operation: TimelineOperation,
        *,
        sequence_id: str | None = None,
        patch_id: str | None = None,
    ) -> OperationResult:
        result = self.apply_patch(
            TimelinePatch(
                patch_id=patch_id or f"operation-{uuid.uuid4().hex}",
                sequence_id=sequence_id,
                expected_project_revision=self.project.revision,
                operations=[operation],
            )
        )
        return OperationResult(
            project_revision=result.project_revision,
            sequence_id=result.sequence_id,
            audit_entry=result.audit_entries[0],
            inverse_patch=result.inverse_patch,
        )

    def apply_patch(self, patch: TimelinePatch) -> PatchResult:
        if (
            patch.expected_project_revision is not None
            and patch.expected_project_revision != self.project.revision
        ):
            raise _invalid(
                "project revision conflict",
                expected=patch.expected_project_revision,
                actual=self.project.revision,
            )
        before = self.project.model_copy(deep=True)
        candidate = before.model_copy(deep=True)
        sequence_id = patch.sequence_id or candidate.active_sequence_id
        before_revision = before.revision
        if any(
            operation.operation is OperationKind.RESTORE_PROJECT for operation in patch.operations
        ):
            if len(patch.operations) != 1 or not isinstance(
                patch.operations[0], RestoreProjectOperation
            ):
                raise _invalid("restore_project must be the only operation in a patch")
            candidate = patch.operations[0].project.model_copy(deep=True)
            if sequence_id not in {sequence.id for sequence in candidate.sequences}:
                sequence_id = candidate.active_sequence_id
        else:
            sequence = candidate.sequence(sequence_id)
            previous_sequence = sequence.model_copy(deep=True)
            for operation in patch.operations:
                self._apply(candidate, sequence, operation)
            snapshot_key = (previous_sequence.id, previous_sequence.revision)
            if snapshot_key not in {
                (snapshot.sequence_id, snapshot.revision)
                for snapshot in candidate.sequence_versions
            }:
                candidate.sequence_versions.append(
                    SequenceSnapshot.from_sequence(previous_sequence)
                )
            sequence.revision += 1
        candidate.revision = before_revision + 1
        try:
            validated = Project.model_validate(candidate.model_dump(mode="python"))
        except ValueError as exc:
            raise _invalid("operation produced an invalid project", detail=str(exc)) from exc
        report = validate_project(validated)
        if not report.valid:
            raise _invalid(
                "operation violated timeline invariants",
                issues=report.model_dump(mode="json")["issues"],
            )
        entries = [
            self._audit_entry(
                patch,
                sequence_id,
                operation,
                before_revision,
                validated.revision,
            )
            for operation in patch.operations
        ]
        inverse = TimelinePatch(
            patch_id=f"inverse-{patch.patch_id}-{uuid.uuid4().hex[:8]}",
            sequence_id=sequence_id,
            expected_project_revision=validated.revision,
            operations=[RestoreProjectOperation(project=before)],
            metadata={"engine:inverse_of": patch.patch_id},
        )
        self._undo_stack.append(before)
        self._redo_stack.clear()
        self.project = validated
        self.audit_log.extend(entries)
        return PatchResult(
            project_revision=validated.revision,
            sequence_id=sequence_id,
            audit_entries=entries,
            inverse_patch=inverse,
        )

    def undo(self, *, sequence_id: str | None = None) -> HistoryResult:
        if not self._undo_stack:
            raise _invalid("undo history is empty")
        current = self.project.model_copy(deep=True)
        restored = self._undo_stack.pop()
        self._redo_stack.append(current)
        restored.revision = current.revision + 1
        target = sequence_id or restored.active_sequence_id
        restored.sequence(target).revision = current.sequence(target).revision + 1
        self.project = Project.model_validate(restored.model_dump(mode="python"))
        entry = self._history_entry("undo", target, current.revision, self.project.revision)
        self.audit_log.append(entry)
        return HistoryResult(
            action="undo",
            project_revision=self.project.revision,
            sequence_id=target,
            audit_entry=entry,
        )

    def redo(self, *, sequence_id: str | None = None) -> HistoryResult:
        if not self._redo_stack:
            raise _invalid("redo history is empty")
        current = self.project.model_copy(deep=True)
        restored = self._redo_stack.pop()
        self._undo_stack.append(current)
        restored.revision = current.revision + 1
        target = sequence_id or restored.active_sequence_id
        restored.sequence(target).revision = current.sequence(target).revision + 1
        self.project = Project.model_validate(restored.model_dump(mode="python"))
        entry = self._history_entry("redo", target, current.revision, self.project.revision)
        self.audit_log.append(entry)
        return HistoryResult(
            action="redo",
            project_revision=self.project.revision,
            sequence_id=target,
            audit_entry=entry,
        )

    def _apply(
        self,
        project: Project,
        sequence: Sequence,
        operation: TimelineOperation,
    ) -> None:
        timeline = sequence.timeline
        frame_rate = sequence.settings_override.frame_rate or project.settings.frame_rate
        if isinstance(operation, AppendOperation):
            track = _find_track(timeline, operation.track_id)
            _assert_unlocked(track)
            item = operation.item.model_copy(deep=True)
            _assert_compatible(track, item)
            _shift_item(item, _track_end(track) - item.timeline_range.start)
            _items(track).append(item)
            _sort_track(track)
        elif isinstance(operation, InsertOperation):
            self._insert(timeline, operation, frame_rate)
        elif isinstance(operation, OverwriteOperation):
            self._overwrite(timeline, operation, frame_rate)
        elif isinstance(operation, ReplaceOperation):
            self._replace(timeline, operation, frame_rate)
        elif isinstance(operation, SplitOperation):
            track = _find_track(timeline, operation.track_id)
            item = _track_item(track, operation.item_id)
            _assert_unlocked(track, item)
            left, right = _split_item(
                item,
                operation.at,
                operation.left_id,
                operation.right_id,
                frame_rate,
            )
            items = _items(track)
            index = items.index(item)
            items[index : index + 1] = [left, right]
            _prune_transitions(track)
        elif isinstance(operation, TrimOperation):
            track = _find_track(timeline, operation.track_id)
            item = _track_item(track, operation.item_id)
            _assert_unlocked(track, item)
            _trim_item(item, operation.new_range, frame_rate)
            _sort_track(track)
        elif isinstance(operation, RippleTrimOperation):
            self._ripple_trim(timeline, operation, frame_rate)
        elif isinstance(operation, RollOperation):
            self._roll(timeline, operation, frame_rate)
        elif isinstance(operation, SlipOperation):
            self._slip(timeline, operation)
        elif isinstance(operation, SlideOperation):
            self._slide(timeline, operation, frame_rate)
        elif isinstance(operation, LiftOperation):
            track = _find_track(timeline, operation.track_id)
            item = _track_item(track, operation.item_id)
            _assert_unlocked(track, item)
            index = _items(track).index(item)
            _items(track)[index] = Gap(id=operation.gap_id, timeline_range=item.timeline_range)
            _prune_transitions(track)
        elif isinstance(operation, ExtractOperation):
            tracks = (
                [_find_track(timeline, track_id) for track_id in operation.track_ids]
                if operation.track_ids
                else timeline.tracks
            )
            for track in tracks:
                _assert_unlocked(track)
                _cut_track_range(
                    track,
                    operation.range,
                    ripple=True,
                    frame_rate=frame_rate,
                )
        elif isinstance(operation, RippleDeleteOperation):
            self._ripple_delete(timeline, operation)
        elif isinstance(operation, MoveOperation):
            self._move(timeline, operation, frame_rate)
        elif isinstance(operation, DuplicateOperation):
            self._duplicate(timeline, operation, frame_rate)
        elif isinstance(operation, (EnableOperation, DisableOperation)):
            self._toggle(timeline, operation, isinstance(operation, EnableOperation))
        elif isinstance(operation, LinkOperation):
            self._link(timeline, operation)
        elif isinstance(operation, UnlinkOperation):
            self._unlink(timeline, operation)
        elif isinstance(operation, GroupOperation):
            for item_id in operation.item_ids:
                _find_item(timeline, item_id)[1].group_id = operation.group_id
        elif isinstance(operation, UngroupOperation):
            for track in timeline.tracks:
                for item in _items(track):
                    if item.group_id == operation.group_id:
                        item.group_id = None
        elif isinstance(operation, NestOperation):
            self._nest(project, sequence, operation)
        elif isinstance(operation, UnnestOperation):
            self._unnest(project, sequence, operation)
        elif isinstance(operation, AddTransitionOperation):
            track = _find_track(timeline, operation.track_id)
            _assert_unlocked(track)
            transitions = _transitions(track)
            if any(item.id == operation.transition.id for item in transitions):
                raise _invalid(
                    "transition id already exists", transition_id=operation.transition.id
                )
            transitions.append(operation.transition.model_copy(deep=True))
        elif isinstance(operation, RemoveTransitionOperation):
            track = _find_track(timeline, operation.track_id)
            transitions = _transitions(track)
            before = len(transitions)
            transitions[:] = [item for item in transitions if item.id != operation.transition_id]
            if len(transitions) == before:
                raise _invalid("transition was not found", transition_id=operation.transition_id)
        elif isinstance(operation, AddEffectOperation):
            track, item = _find_item(timeline, operation.item_id)
            _assert_unlocked(track, item)
            if any(effect.id == operation.effect.id for effect in item.effects):
                raise _invalid("effect id already exists", effect_id=operation.effect.id)
            item.effects.append(operation.effect.model_copy(deep=True))
        elif isinstance(operation, RemoveEffectOperation):
            track, item = _find_item(timeline, operation.item_id)
            _assert_unlocked(track, item)
            before = len(item.effects)
            item.effects = [effect for effect in item.effects if effect.id != operation.effect_id]
            if len(item.effects) == before:
                raise _invalid("effect was not found", effect_id=operation.effect_id)
        elif isinstance(operation, AddKeyframeOperation):
            item, effect = _effect(timeline, operation.effect_id)
            track, _ = _find_item(timeline, item.id)
            _assert_unlocked(track, item)
            if operation.keyframe.time > item.timeline_range.duration:
                raise _invalid("keyframe falls outside item duration")
            if any(keyframe.id == operation.keyframe.id for keyframe in effect.keyframes):
                raise _invalid("keyframe id already exists", keyframe_id=operation.keyframe.id)
            effect.keyframes.append(operation.keyframe.model_copy(deep=True))
            effect.keyframes.sort(key=lambda keyframe: keyframe.time)
        elif isinstance(operation, RemoveKeyframeOperation):
            item, effect = _effect(timeline, operation.effect_id)
            track, _ = _find_item(timeline, item.id)
            _assert_unlocked(track, item)
            before = len(effect.keyframes)
            effect.keyframes = [
                keyframe for keyframe in effect.keyframes if keyframe.id != operation.keyframe_id
            ]
            if len(effect.keyframes) == before:
                raise _invalid("keyframe was not found", keyframe_id=operation.keyframe_id)
        elif isinstance(operation, AddMarkerOperation):
            markers = _marker_target(timeline, operation.target_type, operation.target_id)
            if any(marker.id == operation.marker.id for marker in markers):
                raise _invalid("marker id already exists", marker_id=operation.marker.id)
            markers.append(operation.marker.model_copy(deep=True))
        elif isinstance(operation, RemoveMarkerOperation):
            markers = _marker_target(timeline, operation.target_type, operation.target_id)
            before = len(markers)
            markers[:] = [marker for marker in markers if marker.id != operation.marker_id]
            if len(markers) == before:
                raise _invalid("marker was not found", marker_id=operation.marker_id)
        elif isinstance(operation, AddCaptionCollisionRegionOperation):
            track = _find_track(timeline, operation.track_id)
            if not isinstance(track, CaptionTrack):
                raise _invalid(
                    "caption collision regions require a caption track",
                    track_id=operation.track_id,
                )
            _assert_unlocked(track)
            if any(region.id == operation.region.id for region in track.collision_regions):
                raise _invalid(
                    "caption collision region id already exists",
                    region_id=operation.region.id,
                )
            track.collision_regions.append(operation.region.model_copy(deep=True))
            track.collision_regions.sort(
                key=lambda region: (region.timeline_range.start, region.id)
            )
        elif isinstance(operation, RemoveCaptionCollisionRegionOperation):
            track = _find_track(timeline, operation.track_id)
            if not isinstance(track, CaptionTrack):
                raise _invalid(
                    "caption collision regions require a caption track",
                    track_id=operation.track_id,
                )
            _assert_unlocked(track)
            before = len(track.collision_regions)
            track.collision_regions = [
                region for region in track.collision_regions if region.id != operation.region_id
            ]
            if len(track.collision_regions) == before:
                raise _invalid(
                    "caption collision region was not found",
                    region_id=operation.region_id,
                )
        elif isinstance(operation, JCutOperation):
            self._audio_extension(
                timeline,
                operation.audio_track_id,
                operation.audio_item_id,
                operation.extension,
                RationalTime.zero(),
            )
        elif isinstance(operation, LCutOperation):
            self._audio_extension(
                timeline,
                operation.audio_track_id,
                operation.audio_item_id,
                RationalTime.zero(),
                operation.extension,
            )
        elif isinstance(operation, AudioExtensionOperation):
            self._audio_extension(
                timeline,
                operation.track_id,
                operation.item_id,
                operation.start_extension,
                operation.end_extension,
            )
        elif isinstance(operation, AudioCrossfadeOperation):
            track = _find_track(timeline, operation.track_id)
            if not isinstance(track, AudioTrack):
                raise _invalid("audio crossfade requires an audio track")
            left = _track_item(track, operation.left_item_id)
            right = _track_item(track, operation.right_item_id)
            _assert_unlocked(track, left)
            _assert_unlocked(track, right)
            _transitions(track).append(
                Transition(
                    id=operation.transition_id,
                    kind=TransitionKind.AUDIO_CROSSFADE,
                    from_item_id=operation.left_item_id,
                    to_item_id=operation.right_item_id,
                    duration=operation.duration,
                )
            )
        elif isinstance(operation, RestoreProjectOperation):
            raise _invalid("restore_project is handled at patch scope")
        else:
            raise _invalid("unsupported operation", operation=operation.operation)

    def _insert(
        self,
        timeline: Timeline,
        operation: InsertOperation,
        frame_rate: FrameRate,
    ) -> None:
        track = _find_track(timeline, operation.track_id)
        _assert_unlocked(track)
        item = operation.item.model_copy(deep=True)
        _assert_compatible(track, item)
        items = _items(track)
        for existing in list(items):
            if existing.timeline_range.start < operation.at < existing.timeline_range.end:
                left, right = _split_item(
                    existing,
                    operation.at,
                    existing.id,
                    _unique_internal_id(f"{existing.id}-insert-right"),
                    frame_rate,
                )
                index = items.index(existing)
                items[index : index + 1] = [left, right]
                break
        for existing in items:
            if existing.timeline_range.start >= operation.at:
                _shift_item(existing, item.timeline_range.duration)
        _shift_item(item, operation.at - item.timeline_range.start)
        items.append(item)
        _sort_track(track)
        _prune_transitions(track)

    def _overwrite(
        self,
        timeline: Timeline,
        operation: OverwriteOperation,
        frame_rate: FrameRate,
    ) -> None:
        track = _find_track(timeline, operation.track_id)
        _assert_unlocked(track)
        item = operation.item.model_copy(deep=True)
        _assert_compatible(track, item)
        _shift_item(item, operation.at - item.timeline_range.start)
        _cut_track_range(
            track,
            item.timeline_range,
            ripple=False,
            frame_rate=frame_rate,
        )
        _items(track).append(item)
        _sort_track(track)

    def _replace(
        self,
        timeline: Timeline,
        operation: ReplaceOperation,
        frame_rate: FrameRate,
    ) -> None:
        track = _find_track(timeline, operation.track_id)
        old = _track_item(track, operation.item_id)
        _assert_unlocked(track, old)
        replacement = operation.item.model_copy(deep=True)
        _assert_compatible(track, replacement)
        if operation.preserve_timeline_range:
            source = _source_range(replacement)
            if source is not None:
                assert isinstance(replacement, (Clip, AudioClip, NestedSequenceClip))
                effects = (
                    _freeze_effects_for_trim(
                        replacement,
                        old.timeline_range.duration,
                        frame_rate,
                    )
                    if isinstance(replacement, Clip)
                    and any(
                        effect.enabled and effect.kind is EffectKind.FREEZE
                        for effect in replacement.effects
                    )
                    else None
                )
                replacement_retime = replacement.retime.window(
                    RationalTime.zero(), old.timeline_range.duration
                )
                source_duration = replacement_retime.source_offset_at(old.timeline_range.duration)
                _set_item_ranges(
                    replacement,
                    old.timeline_range,
                    TimeRange(
                        start=(
                            source.end - source_duration
                            if replacement_retime.reverse
                            else source.start
                        ),
                        duration=source_duration,
                    ),
                    retime=replacement_retime,
                    effects=effects,
                )
            else:
                replacement.timeline_range = old.timeline_range
        index = _items(track).index(old)
        _items(track)[index] = replacement
        _prune_transitions(track)

    def _ripple_trim(
        self,
        timeline: Timeline,
        operation: RippleTrimOperation,
        frame_rate: FrameRate,
    ) -> None:
        track = _find_track(timeline, operation.track_id)
        item = _track_item(track, operation.item_id)
        _assert_unlocked(track, item)
        old_end = item.timeline_range.end
        old_duration = item.timeline_range.duration
        _trim_item(item, operation.new_range, frame_rate)
        delta = operation.new_range.duration - old_duration
        for following in _items(track):
            if following is not item and following.timeline_range.start >= old_end:
                _shift_item(following, delta)
        _sort_track(track)

    def _roll(
        self,
        timeline: Timeline,
        operation: RollOperation,
        frame_rate: FrameRate,
    ) -> None:
        track = _find_track(timeline, operation.track_id)
        left = _track_item(track, operation.left_item_id)
        right = _track_item(track, operation.right_item_id)
        _assert_unlocked(track, left)
        _assert_unlocked(track, right)
        if left.timeline_range.end != right.timeline_range.start:
            raise _invalid("roll edit requires adjacent items")
        if not (left.timeline_range.start < operation.new_cut < right.timeline_range.end):
            raise _invalid("roll cut must remain inside the combined range")
        _trim_item(
            left,
            TimeRange.from_start_end(left.timeline_range.start, operation.new_cut),
            frame_rate,
        )
        _trim_item(
            right,
            TimeRange.from_start_end(operation.new_cut, right.timeline_range.end),
            frame_rate,
        )

    def _slip(self, timeline: Timeline, operation: SlipOperation) -> None:
        track = _find_track(timeline, operation.track_id)
        item = _track_item(track, operation.item_id)
        _assert_unlocked(track, item)
        source = _source_range(item)
        if source is None:
            raise _invalid("slip requires a source-backed item", item_id=item.id)
        new_start = source.start + operation.source_offset
        if new_start.value < 0:
            raise _invalid("slip would move before source zero", item_id=item.id)
        effects = None
        if isinstance(item, Clip):
            effects = []
            for effect in item.effects:
                if effect.kind is not EffectKind.FREEZE:
                    effects.append(effect.model_copy(deep=True))
                    continue
                parameters = dict(effect.parameters)
                materialized = parameters.get("source_range")
                if materialized is not None:
                    freeze_source = TimeRange.model_validate(materialized)
                    shifted = freeze_source.shifted(operation.source_offset)
                    if shifted.start.value < 0:
                        raise _invalid(
                            "slip would move a freeze source before zero",
                            item_id=item.id,
                            effect_id=effect.id,
                        )
                    parameters["source_range"] = shifted.model_dump(mode="json")
                effects.append(effect.model_copy(deep=True, update={"parameters": parameters}))
        _set_source_range(
            item,
            TimeRange(start=new_start, duration=source.duration),
            effects=effects,
        )

    def _slide(
        self,
        timeline: Timeline,
        operation: SlideOperation,
        frame_rate: FrameRate,
    ) -> None:
        track = _find_track(timeline, operation.track_id)
        ordered = sorted(_items(track), key=lambda item: item.timeline_range.start)
        item = _track_item(track, operation.item_id)
        index = ordered.index(item)
        if index == 0 or index == len(ordered) - 1:
            raise _invalid("slide requires both a previous and next item")
        previous, following = ordered[index - 1], ordered[index + 1]
        if (
            previous.timeline_range.end != item.timeline_range.start
            or item.timeline_range.end != following.timeline_range.start
        ):
            raise _invalid("slide requires three contiguous items")
        new_start = item.timeline_range.start + operation.offset
        new_end = item.timeline_range.end + operation.offset
        if new_start <= previous.timeline_range.start or new_end >= following.timeline_range.end:
            raise _invalid("slide would consume an adjacent item")
        _trim_item(
            previous,
            TimeRange.from_start_end(previous.timeline_range.start, new_start),
            frame_rate,
        )
        _shift_item(item, operation.offset)
        _trim_item(
            following,
            TimeRange.from_start_end(new_end, following.timeline_range.end),
            frame_rate,
        )
        _sort_track(track)

    def _ripple_delete(self, timeline: Timeline, operation: RippleDeleteOperation) -> None:
        track = _find_track(timeline, operation.track_id)
        item = _track_item(track, operation.item_id)
        _assert_unlocked(track, item)
        end = item.timeline_range.end
        duration = item.timeline_range.duration
        _items(track).remove(item)
        for following in _items(track):
            if following.timeline_range.start >= end:
                _shift_item(following, -duration)
        _prune_transitions(track)

    def _move(
        self,
        timeline: Timeline,
        operation: MoveOperation,
        frame_rate: FrameRate,
    ) -> None:
        source_track = _find_track(timeline, operation.source_track_id)
        target_track = _find_track(timeline, operation.target_track_id)
        item = _track_item(source_track, operation.item_id)
        _assert_unlocked(source_track, item)
        _assert_unlocked(target_track)
        _assert_compatible(target_track, item)
        _items(source_track).remove(item)
        _shift_item(item, operation.target_start - item.timeline_range.start)
        if operation.overwrite:
            _cut_track_range(
                target_track,
                item.timeline_range,
                ripple=False,
                frame_rate=frame_rate,
            )
        _items(target_track).append(item)
        _sort_track(source_track)
        _sort_track(target_track)
        _prune_transitions(source_track)
        _prune_transitions(target_track)

    def _duplicate(
        self,
        timeline: Timeline,
        operation: DuplicateOperation,
        frame_rate: FrameRate,
    ) -> None:
        source_track = _find_track(timeline, operation.source_track_id)
        target_track = _find_track(timeline, operation.target_track_id)
        source = _track_item(source_track, operation.item_id)
        duplicate = source.model_copy(deep=True, update={"id": operation.new_item_id})
        _assert_compatible(target_track, duplicate)
        _shift_item(duplicate, operation.target_start - duplicate.timeline_range.start)
        _cut_track_range(
            target_track,
            duplicate.timeline_range,
            ripple=False,
            frame_rate=frame_rate,
        )
        _items(target_track).append(duplicate)
        _sort_track(target_track)

    def _toggle(
        self,
        timeline: Timeline,
        operation: EnableOperation | DisableOperation,
        enabled: bool,
    ) -> None:
        if operation.target_type == "track":
            _find_track(timeline, operation.target_id).enabled = enabled
        elif operation.target_type == "item":
            _find_item(timeline, operation.target_id)[1].enabled = enabled
        else:
            _effect(timeline, operation.target_id)[1].enabled = enabled

    def _link(self, timeline: Timeline, operation: LinkOperation) -> None:
        ids = set(operation.item_ids)
        if len(ids) != len(operation.item_ids):
            raise _invalid("link item ids must be unique")
        for item_id in ids:
            _find_item(timeline, item_id)
        self._unlink(timeline, UnlinkOperation(item_ids=list(ids)))
        timeline.link_groups.append(
            LinkGroup(id=operation.group_id, item_ids=operation.item_ids, locked=operation.locked)
        )
        for item_id in ids:
            _find_item(timeline, item_id)[1].linked_group_id = operation.group_id

    def _unlink(self, timeline: Timeline, operation: UnlinkOperation) -> None:
        ids = set(operation.item_ids)
        for item_id in ids:
            _find_item(timeline, item_id)[1].linked_group_id = None
        retained: list[LinkGroup] = []
        for group in timeline.link_groups:
            remaining = [item_id for item_id in group.item_ids if item_id not in ids]
            if len(remaining) >= 2:
                group.item_ids = remaining
                retained.append(group)
            else:
                for item_id in remaining:
                    _find_item(timeline, item_id)[1].linked_group_id = None
        timeline.link_groups = retained

    def _nest(self, project: Project, parent: Sequence, operation: NestOperation) -> None:
        if any(sequence.id == operation.sequence_id for sequence in project.sequences):
            raise _invalid("nested sequence id already exists", sequence_id=operation.sequence_id)
        timeline = parent.timeline
        selected_ids = set(operation.item_ids)
        selected = [
            (track, item)
            for track in timeline.tracks
            for item in _items(track)
            if item.id in selected_ids
        ]
        if {item.id for _, item in selected} != selected_ids:
            raise _invalid("nest selection contains missing items")
        start = min(item.timeline_range.start for _, item in selected)
        end = max(item.timeline_range.end for _, item in selected)
        nested_tracks: list[Track] = []
        for track in timeline.tracks:
            nested_items = [
                item.model_copy(deep=True) for item in _items(track) if item.id in selected_ids
            ]
            if not nested_items:
                continue
            for item in nested_items:
                _shift_item(item, -start)
            transition_ids = {item.id for item in nested_items}
            updates: dict[str, object] = {"items": nested_items}
            if hasattr(track, "transitions"):
                updates["transitions"] = [
                    transition.model_copy(deep=True)
                    for transition in _transitions(track)
                    if transition.from_item_id in transition_ids
                    and transition.to_item_id in transition_ids
                ]
            nested_tracks.append(track.model_copy(deep=True, update=updates))
            _items(track)[:] = [item for item in _items(track) if item.id not in selected_ids]
            _prune_transitions(track)
        nested = Sequence(
            id=operation.sequence_id,
            name=operation.sequence_name,
            timeline=Timeline(tracks=nested_tracks),
        )
        project.sequences.append(nested)
        target_track = _find_track(timeline, operation.target_track_id)
        nested_clip = NestedSequenceClip(
            id=operation.nested_clip_id,
            name=operation.sequence_name,
            sequence_id=operation.sequence_id,
            timeline_range=TimeRange.from_start_end(start, end),
            source_range=TimeRange(start=RationalTime.zero(), duration=end - start),
            sequence_version=nested.revision,
        )
        _assert_compatible(target_track, nested_clip)
        _items(target_track).append(nested_clip)
        _sort_track(target_track)

    def _unnest(self, project: Project, parent: Sequence, operation: UnnestOperation) -> None:
        timeline = parent.timeline
        parent_track = _find_track(timeline, operation.track_id)
        nested_clip = _track_item(parent_track, operation.nested_clip_id)
        if not isinstance(nested_clip, NestedSequenceClip):
            raise _invalid("unnest target is not a nested sequence clip")
        nested = project.sequence(nested_clip.sequence_id)
        _items(parent_track).remove(nested_clip)
        for nested_track in nested.timeline.tracks:
            if nested_track.id in operation.track_mapping:
                target = _find_track(timeline, operation.track_mapping[nested_track.id])
            else:
                target_candidate = next(
                    (
                        track
                        for track in timeline.tracks
                        if track.track_type == nested_track.track_type
                    ),
                    None,
                )
                if target_candidate is None:
                    raise _invalid(
                        "no compatible parent track for nested track",
                        nested_track_id=nested_track.id,
                    )
                target = target_candidate
            for source_item in _items(nested_track):
                item = source_item.model_copy(deep=True)
                _shift_item(item, nested_clip.timeline_range.start)
                _assert_compatible(target, item)
                _items(target).append(item)
            _sort_track(target)
        if operation.remove_sequence:
            still_referenced = any(
                isinstance(item, NestedSequenceClip) and item.sequence_id == nested.id
                for sequence in project.sequences
                if sequence.id != nested.id
                for track in sequence.timeline.tracks
                for item in _items(track)
            )
            if still_referenced:
                raise _invalid("nested sequence is still referenced", sequence_id=nested.id)
            project.sequences = [
                sequence for sequence in project.sequences if sequence.id != nested.id
            ]

    def _audio_extension(
        self,
        timeline: Timeline,
        track_id: str,
        item_id: str,
        start_extension: RationalTime,
        end_extension: RationalTime,
    ) -> None:
        if start_extension.value < 0 or end_extension.value < 0:
            raise _invalid("audio extensions must be nonnegative")
        track = _find_track(timeline, track_id)
        item = _track_item(track, item_id)
        if not isinstance(track, AudioTrack) or not isinstance(item, AudioClip):
            raise _invalid("audio extension requires an audio clip")
        _assert_unlocked(track, item)
        new_start = item.timeline_range.start - start_extension
        offset_start = item.retime.source_offset_at(-start_extension)
        offset_end = item.retime.source_offset_at(item.timeline_range.duration + end_extension)
        source_start = (
            item.source_range.end - offset_end
            if item.retime.reverse
            else item.source_range.start + offset_start
        )
        if new_start.value < 0 or source_start.value < 0:
            raise _invalid("audio extension would move before zero", item_id=item.id)
        added = start_extension + end_extension
        new_timeline_range = TimeRange(
            start=new_start,
            duration=item.timeline_range.duration + added,
        )
        for other in list(_items(track)):
            if other is item or not other.timeline_range.overlaps(new_timeline_range):
                continue
            _assert_unlocked(track, other)
            if other.timeline_range.start < new_timeline_range.start:
                _trim_item(
                    other,
                    TimeRange.from_start_end(other.timeline_range.start, new_timeline_range.start),
                )
            elif other.timeline_range.end > new_timeline_range.end:
                _trim_item(
                    other,
                    TimeRange.from_start_end(new_timeline_range.end, other.timeline_range.end),
                )
            else:
                _items(track).remove(other)
        _set_item_ranges(
            item,
            new_timeline_range,
            TimeRange(
                start=source_start,
                duration=offset_end - offset_start,
            ),
            retime=item.retime.window(-start_extension, new_timeline_range.duration),
        )
        _sort_track(track)

    def _audit_entry(
        self,
        patch: TimelinePatch,
        sequence_id: str,
        operation: TimelineOperation,
        before: int,
        after: int,
    ) -> AuditEntry:
        payload = operation.model_dump(mode="json")
        return AuditEntry(
            id=f"audit-{uuid.uuid4().hex}",
            timestamp=datetime.now(UTC),
            patch_id=patch.patch_id,
            sequence_id=sequence_id,
            operation=operation.operation,
            operation_payload=payload,
            project_revision_before=before,
            project_revision_after=after,
            summary=f"{operation.operation.value} applied",
        )

    def _history_entry(
        self,
        action: str,
        sequence_id: str,
        before: int,
        after: int,
    ) -> AuditEntry:
        kind = OperationKind.RESTORE_PROJECT
        return AuditEntry(
            id=f"audit-{uuid.uuid4().hex}",
            timestamp=datetime.now(UTC),
            patch_id=f"{action}-{uuid.uuid4().hex}",
            sequence_id=sequence_id,
            operation=kind,
            operation_payload={"history_action": action},
            project_revision_before=before,
            project_revision_after=after,
            summary=f"{action} applied",
        )
