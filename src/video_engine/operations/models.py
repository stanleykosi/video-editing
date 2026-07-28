"""Strict operation requests, patches, results, and audit records."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.core.schema import (
    CaptionCollisionRegion,
    Effect,
    JsonValue,
    Keyframe,
    Marker,
    Project,
    TimelineItem,
    Transition,
)
from video_engine.core.time import RationalTime, TimeRange


class OperationKind(StrEnum):
    APPEND = "append"
    INSERT = "insert"
    OVERWRITE = "overwrite"
    REPLACE = "replace"
    SPLIT = "split"
    TRIM = "trim"
    RIPPLE_TRIM = "ripple_trim"
    ROLL = "roll"
    SLIP = "slip"
    SLIDE = "slide"
    LIFT = "lift"
    EXTRACT = "extract"
    RIPPLE_DELETE = "ripple_delete"
    MOVE = "move"
    DUPLICATE = "duplicate"
    ENABLE = "enable"
    DISABLE = "disable"
    LINK = "link"
    UNLINK = "unlink"
    GROUP = "group"
    UNGROUP = "ungroup"
    NEST = "nest"
    UNNEST = "unnest"
    ADD_TRANSITION = "add_transition"
    REMOVE_TRANSITION = "remove_transition"
    ADD_EFFECT = "add_effect"
    REMOVE_EFFECT = "remove_effect"
    ADD_KEYFRAME = "add_keyframe"
    REMOVE_KEYFRAME = "remove_keyframe"
    ADD_MARKER = "add_marker"
    REMOVE_MARKER = "remove_marker"
    ADD_CAPTION_COLLISION_REGION = "add_caption_collision_region"
    REMOVE_CAPTION_COLLISION_REGION = "remove_caption_collision_region"
    J_CUT = "j_cut"
    L_CUT = "l_cut"
    AUDIO_CROSSFADE = "audio_crossfade"
    AUDIO_EXTENSION = "audio_extension"
    RESTORE_PROJECT = "restore_project"


class OperationBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AppendOperation(OperationBase):
    operation: Literal[OperationKind.APPEND] = OperationKind.APPEND
    track_id: str
    item: TimelineItem


class InsertOperation(OperationBase):
    operation: Literal[OperationKind.INSERT] = OperationKind.INSERT
    track_id: str
    at: RationalTime
    item: TimelineItem


class OverwriteOperation(OperationBase):
    operation: Literal[OperationKind.OVERWRITE] = OperationKind.OVERWRITE
    track_id: str
    at: RationalTime
    item: TimelineItem


class ReplaceOperation(OperationBase):
    operation: Literal[OperationKind.REPLACE] = OperationKind.REPLACE
    track_id: str
    item_id: str
    item: TimelineItem
    preserve_timeline_range: bool = True


class SplitOperation(OperationBase):
    operation: Literal[OperationKind.SPLIT] = OperationKind.SPLIT
    track_id: str
    item_id: str
    at: RationalTime
    left_id: str
    right_id: str


class TrimOperation(OperationBase):
    operation: Literal[OperationKind.TRIM] = OperationKind.TRIM
    track_id: str
    item_id: str
    new_range: TimeRange


class RippleTrimOperation(OperationBase):
    operation: Literal[OperationKind.RIPPLE_TRIM] = OperationKind.RIPPLE_TRIM
    track_id: str
    item_id: str
    new_range: TimeRange


class RollOperation(OperationBase):
    operation: Literal[OperationKind.ROLL] = OperationKind.ROLL
    track_id: str
    left_item_id: str
    right_item_id: str
    new_cut: RationalTime


class SlipOperation(OperationBase):
    operation: Literal[OperationKind.SLIP] = OperationKind.SLIP
    track_id: str
    item_id: str
    source_offset: RationalTime


class SlideOperation(OperationBase):
    operation: Literal[OperationKind.SLIDE] = OperationKind.SLIDE
    track_id: str
    item_id: str
    offset: RationalTime


class LiftOperation(OperationBase):
    operation: Literal[OperationKind.LIFT] = OperationKind.LIFT
    track_id: str
    item_id: str
    gap_id: str


class ExtractOperation(OperationBase):
    operation: Literal[OperationKind.EXTRACT] = OperationKind.EXTRACT
    range: TimeRange
    track_ids: list[str] | None = None


class RippleDeleteOperation(OperationBase):
    operation: Literal[OperationKind.RIPPLE_DELETE] = OperationKind.RIPPLE_DELETE
    track_id: str
    item_id: str


class MoveOperation(OperationBase):
    operation: Literal[OperationKind.MOVE] = OperationKind.MOVE
    source_track_id: str
    item_id: str
    target_track_id: str
    target_start: RationalTime
    overwrite: bool = True


class DuplicateOperation(OperationBase):
    operation: Literal[OperationKind.DUPLICATE] = OperationKind.DUPLICATE
    source_track_id: str
    item_id: str
    target_track_id: str
    target_start: RationalTime
    new_item_id: str


class ToggleOperation(OperationBase):
    target_type: Literal["track", "item", "effect"]
    target_id: str


class EnableOperation(ToggleOperation):
    operation: Literal[OperationKind.ENABLE] = OperationKind.ENABLE


class DisableOperation(ToggleOperation):
    operation: Literal[OperationKind.DISABLE] = OperationKind.DISABLE


class LinkOperation(OperationBase):
    operation: Literal[OperationKind.LINK] = OperationKind.LINK
    group_id: str
    item_ids: list[str] = Field(min_length=2)
    locked: bool = False


class UnlinkOperation(OperationBase):
    operation: Literal[OperationKind.UNLINK] = OperationKind.UNLINK
    item_ids: list[str] = Field(min_length=1)


class GroupOperation(OperationBase):
    operation: Literal[OperationKind.GROUP] = OperationKind.GROUP
    group_id: str
    item_ids: list[str] = Field(min_length=1)


class UngroupOperation(OperationBase):
    operation: Literal[OperationKind.UNGROUP] = OperationKind.UNGROUP
    group_id: str


class NestOperation(OperationBase):
    operation: Literal[OperationKind.NEST] = OperationKind.NEST
    item_ids: list[str] = Field(min_length=1)
    target_track_id: str
    sequence_id: str
    sequence_name: str
    nested_clip_id: str


class UnnestOperation(OperationBase):
    operation: Literal[OperationKind.UNNEST] = OperationKind.UNNEST
    track_id: str
    nested_clip_id: str
    track_mapping: dict[str, str] = Field(default_factory=dict)
    remove_sequence: bool = False


class AddTransitionOperation(OperationBase):
    operation: Literal[OperationKind.ADD_TRANSITION] = OperationKind.ADD_TRANSITION
    track_id: str
    transition: Transition


class RemoveTransitionOperation(OperationBase):
    operation: Literal[OperationKind.REMOVE_TRANSITION] = OperationKind.REMOVE_TRANSITION
    track_id: str
    transition_id: str


class AddEffectOperation(OperationBase):
    operation: Literal[OperationKind.ADD_EFFECT] = OperationKind.ADD_EFFECT
    item_id: str
    effect: Effect


class RemoveEffectOperation(OperationBase):
    operation: Literal[OperationKind.REMOVE_EFFECT] = OperationKind.REMOVE_EFFECT
    item_id: str
    effect_id: str


class AddKeyframeOperation(OperationBase):
    operation: Literal[OperationKind.ADD_KEYFRAME] = OperationKind.ADD_KEYFRAME
    effect_id: str
    keyframe: Keyframe


class RemoveKeyframeOperation(OperationBase):
    operation: Literal[OperationKind.REMOVE_KEYFRAME] = OperationKind.REMOVE_KEYFRAME
    effect_id: str
    keyframe_id: str


class AddMarkerOperation(OperationBase):
    operation: Literal[OperationKind.ADD_MARKER] = OperationKind.ADD_MARKER
    target_type: Literal["timeline", "item"]
    target_id: str | None = None
    marker: Marker


class RemoveMarkerOperation(OperationBase):
    operation: Literal[OperationKind.REMOVE_MARKER] = OperationKind.REMOVE_MARKER
    target_type: Literal["timeline", "item"]
    marker_id: str
    target_id: str | None = None


class AddCaptionCollisionRegionOperation(OperationBase):
    operation: Literal[OperationKind.ADD_CAPTION_COLLISION_REGION] = (
        OperationKind.ADD_CAPTION_COLLISION_REGION
    )
    track_id: str
    region: CaptionCollisionRegion


class RemoveCaptionCollisionRegionOperation(OperationBase):
    operation: Literal[OperationKind.REMOVE_CAPTION_COLLISION_REGION] = (
        OperationKind.REMOVE_CAPTION_COLLISION_REGION
    )
    track_id: str
    region_id: str


class JCutOperation(OperationBase):
    operation: Literal[OperationKind.J_CUT] = OperationKind.J_CUT
    audio_track_id: str
    audio_item_id: str
    extension: RationalTime


class LCutOperation(OperationBase):
    operation: Literal[OperationKind.L_CUT] = OperationKind.L_CUT
    audio_track_id: str
    audio_item_id: str
    extension: RationalTime


class AudioCrossfadeOperation(OperationBase):
    operation: Literal[OperationKind.AUDIO_CROSSFADE] = OperationKind.AUDIO_CROSSFADE
    track_id: str
    left_item_id: str
    right_item_id: str
    duration: RationalTime
    transition_id: str


class AudioExtensionOperation(OperationBase):
    operation: Literal[OperationKind.AUDIO_EXTENSION] = OperationKind.AUDIO_EXTENSION
    track_id: str
    item_id: str
    start_extension: RationalTime = Field(default_factory=RationalTime.zero)
    end_extension: RationalTime = Field(default_factory=RationalTime.zero)


class RestoreProjectOperation(OperationBase):
    operation: Literal[OperationKind.RESTORE_PROJECT] = OperationKind.RESTORE_PROJECT
    project: Project


TimelineOperation = Annotated[
    AppendOperation
    | InsertOperation
    | OverwriteOperation
    | ReplaceOperation
    | SplitOperation
    | TrimOperation
    | RippleTrimOperation
    | RollOperation
    | SlipOperation
    | SlideOperation
    | LiftOperation
    | ExtractOperation
    | RippleDeleteOperation
    | MoveOperation
    | DuplicateOperation
    | EnableOperation
    | DisableOperation
    | LinkOperation
    | UnlinkOperation
    | GroupOperation
    | UngroupOperation
    | NestOperation
    | UnnestOperation
    | AddTransitionOperation
    | RemoveTransitionOperation
    | AddEffectOperation
    | RemoveEffectOperation
    | AddKeyframeOperation
    | RemoveKeyframeOperation
    | AddMarkerOperation
    | RemoveMarkerOperation
    | AddCaptionCollisionRegionOperation
    | RemoveCaptionCollisionRegionOperation
    | JCutOperation
    | LCutOperation
    | AudioCrossfadeOperation
    | AudioExtensionOperation
    | RestoreProjectOperation,
    Field(discriminator="operation"),
]


class TimelinePatch(OperationBase):
    patch_id: str = Field(min_length=1)
    sequence_id: str | None = None
    expected_project_revision: int | None = Field(default=None, ge=1)
    operations: list[TimelineOperation] = Field(min_length=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class AuditEntry(OperationBase):
    id: str
    timestamp: datetime
    patch_id: str
    sequence_id: str
    operation: OperationKind
    operation_payload: dict[str, JsonValue]
    project_revision_before: int
    project_revision_after: int
    summary: str


class OperationResult(OperationBase):
    project_revision: int
    sequence_id: str
    audit_entry: AuditEntry
    inverse_patch: TimelinePatch


class PatchResult(OperationBase):
    project_revision: int
    sequence_id: str
    audit_entries: list[AuditEntry]
    inverse_patch: TimelinePatch


class HistoryResult(OperationBase):
    action: Literal["undo", "redo"]
    project_revision: int
    sequence_id: str
    audit_entry: AuditEntry


class PatchEnvelope(OperationBase):
    patch: TimelinePatch

    @model_validator(mode="after")
    def no_public_restore(self) -> PatchEnvelope:
        if any(
            operation.operation is OperationKind.RESTORE_PROJECT
            for operation in self.patch.operations
        ):
            raise ValueError("restore_project is reserved for engine-generated inverse patches")
        return self
