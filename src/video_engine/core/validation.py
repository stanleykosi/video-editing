"""Cross-object project and timeline invariant validation."""

from __future__ import annotations

from enum import StrEnum
from itertools import pairwise

from pydantic import BaseModel, ConfigDict

from video_engine.core.schema import (
    AudioClip,
    CaptionCue,
    Clip,
    EffectKind,
    GeneratorClip,
    GraphicsTrack,
    NestedSequenceClip,
    Project,
    Sequence,
    StillImageClip,
    Track,
    VideoTrack,
)
from video_engine.core.time import FrameRate, RationalTime, RoundingMode, TimeRange


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    severity: Severity
    message: str
    path: str


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[ValidationIssue]

    @property
    def valid(self) -> bool:
        return not any(issue.severity is Severity.ERROR for issue in self.issues)


def _validate_track(track: Track, path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    ordered = sorted(track.items, key=lambda item: item.timeline_range.start)
    for previous, current in pairwise(ordered):
        if previous.timeline_range.end > current.timeline_range.start:
            issues.append(
                ValidationIssue(
                    code="timeline.track_overlap",
                    severity=Severity.ERROR,
                    message=f"items {previous.id!r} and {current.id!r} overlap",
                    path=path,
                )
            )
    item_by_id = {item.id: item for item in track.items}
    ordered_ids = [item.id for item in ordered]
    transition_pairs: set[tuple[str, str]] = set()
    for transition_index, transition in enumerate(getattr(track, "transitions", [])):
        transition_path = f"{path}.transitions[{transition_index}]"
        left = item_by_id.get(transition.from_item_id)
        right = item_by_id.get(transition.to_item_id)
        if left is None or right is None:
            issues.append(
                ValidationIssue(
                    code="timeline.transition_endpoint_missing",
                    severity=Severity.ERROR,
                    message="transition endpoint is missing from its track",
                    path=transition_path,
                )
            )
        elif not left.enabled or not right.enabled:
            issues.append(
                ValidationIssue(
                    code="timeline.transition_endpoint_disabled",
                    severity=Severity.ERROR,
                    message="transition endpoints must both be enabled",
                    path=transition_path,
                )
            )
        elif ordered_ids.index(right.id) != ordered_ids.index(left.id) + 1:
            issues.append(
                ValidationIssue(
                    code="timeline.transition_endpoints_not_adjacent",
                    severity=Severity.ERROR,
                    message="transition endpoints must be adjacent in timeline order",
                    path=transition_path,
                )
            )
        elif left.timeline_range.end != right.timeline_range.start:
            issues.append(
                ValidationIssue(
                    code="timeline.transition_cut_mismatch",
                    severity=Severity.ERROR,
                    message="transition endpoints must meet at one cut boundary",
                    path=transition_path,
                )
            )
        elif (
            transition.duration > left.timeline_range.duration
            or transition.duration > right.timeline_range.duration
        ):
            issues.append(
                ValidationIssue(
                    code="timeline.transition_handle_too_long",
                    severity=Severity.ERROR,
                    message="transition duration exceeds an endpoint item",
                    path=transition_path,
                )
            )
        pair = (transition.from_item_id, transition.to_item_id)
        if pair in transition_pairs:
            issues.append(
                ValidationIssue(
                    code="timeline.duplicate_transition",
                    severity=Severity.ERROR,
                    message="only one transition may occupy a cut",
                    path=transition_path,
                )
            )
        transition_pairs.add(pair)
    for item_index, item in enumerate(track.items):
        item_path = f"{path}.items[{item_index}]"
        source_range = None
        if isinstance(item, (Clip, AudioClip, NestedSequenceClip)):
            source_range = item.source_range
        if source_range is not None and source_range.duration.value <= 0:
            issues.append(
                ValidationIssue(
                    code="timeline.invalid_source_range",
                    severity=Severity.ERROR,
                    message="source range duration must be positive",
                    path=item_path,
                )
            )
        for effect_index, effect in enumerate(item.effects):
            for keyframe_index, keyframe in enumerate(effect.keyframes):
                if keyframe.time.value < 0 or keyframe.time > item.timeline_range.duration:
                    issues.append(
                        ValidationIssue(
                            code="timeline.keyframe_outside_item",
                            severity=Severity.ERROR,
                            message="keyframe time must be relative to and inside its item",
                            path=(
                                f"{item_path}.effects[{effect_index}].keyframes[{keyframe_index}]"
                            ),
                        )
                    )
        if isinstance(item, CaptionCue) and len(item.text.strip()) == 0 and not item.suppressed:
            issues.append(
                ValidationIssue(
                    code="timeline.empty_caption",
                    severity=Severity.WARNING,
                    message="enabled caption cue has no text",
                    path=item_path,
                )
            )
    return issues


def _nested_cycles(project: Project) -> list[ValidationIssue]:
    graph: dict[str, set[str]] = {sequence.id: set() for sequence in project.sequences}
    for sequence in project.sequences:
        for track in sequence.timeline.tracks:
            graph[sequence.id].update(
                item.sequence_id for item in track.items if isinstance(item, NestedSequenceClip)
            )
    issues: list[ValidationIssue] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in visiting:
            cycle = [*stack[stack.index(node) :], node]
            issues.append(
                ValidationIssue(
                    code="project.nested_sequence_cycle",
                    severity=Severity.ERROR,
                    message="nested sequence cycle: " + " -> ".join(cycle),
                    path="sequences",
                )
            )
            return
        if node in visited:
            return
        visiting.add(node)
        for child in graph[node]:
            visit(child, [*stack, child])
        visiting.remove(node)
        visited.add(node)

    for sequence_id in graph:
        visit(sequence_id, [sequence_id])
    return issues


def _track_matte_issues(
    sequence: Sequence, sequence_path: str, frame_rate: FrameRate
) -> list[ValidationIssue]:
    from video_engine.render.effects import TrackMatteParameters, parse_visual_parameters

    visual_types = (Clip, GeneratorClip, NestedSequenceClip, StillImageClip)
    item_matches: dict[str, list[tuple[Track, object, str]]] = {}
    track_matches: dict[str, list[tuple[Track, str]]] = {}
    for track_index, track in enumerate(sequence.timeline.tracks):
        track_path = f"{sequence_path}.timeline.tracks[{track_index}]"
        track_matches.setdefault(track.id, []).append((track, track_path))
        for item_index, item in enumerate(track.items):
            item_matches.setdefault(item.id, []).append(
                (track, item, f"{track_path}.items[{item_index}]")
            )

    issues: list[ValidationIssue] = []
    graph: dict[str, set[str]] = {}
    owner_paths: dict[str, str] = {}
    transition_windows: dict[str, list[TimeRange]] = {}

    for track in sequence.timeline.tracks:
        if not isinstance(track, (VideoTrack, GraphicsTrack)):
            continue
        item_by_id = {item.id: item for item in track.items}
        for transition in track.transitions:
            left = item_by_id.get(transition.from_item_id)
            right = item_by_id.get(transition.to_item_id)
            if left is None or right is None:
                continue
            try:
                frames = frame_rate.time_to_frames(transition.duration, RoundingMode.EXACT)
            except ValueError:
                continue
            if transition.alignment == "start_at_cut":
                before_frames = 0
            elif transition.alignment == "end_at_cut":
                before_frames = frames
            else:
                before_frames = frames // 2
            before = frame_rate.frames_to_time(before_frames)
            cut = left.timeline_range.end
            window = TimeRange(start=cut - before, duration=transition.duration)
            transition_windows.setdefault(left.id, []).append(window)
            transition_windows.setdefault(right.id, []).append(window)

    def issue(code: str, message: str, path: str) -> None:
        issues.append(
            ValidationIssue(code=code, severity=Severity.ERROR, message=message, path=path)
        )

    for owner_id, matches in item_matches.items():
        for _owner_track, owner_object, owner_path in matches:
            if not isinstance(owner_object, visual_types):
                continue
            owner = owner_object
            graph.setdefault(owner_id, set())
            for effect_index, effect in enumerate(owner.effects):
                if not effect.enabled or effect.kind is not EffectKind.TRACK_MATTE:
                    continue
                effect_path = f"{owner_path}.effects[{effect_index}]"
                owner_paths[owner_id] = effect_path
                parsed = parse_visual_parameters(effect)
                assert isinstance(parsed, TrackMatteParameters)
                if parsed.item_id is not None:
                    item_targets = item_matches.get(parsed.item_id, [])
                    if not item_targets:
                        issue(
                            "timeline.track_matte_item_missing",
                            f"track matte item {parsed.item_id!r} is missing from the sequence",
                            effect_path,
                        )
                        continue
                    if len(item_targets) != 1:
                        issue(
                            "timeline.track_matte_item_ambiguous",
                            f"track matte item id {parsed.item_id!r} is not unique",
                            effect_path,
                        )
                        continue
                    _, target_object, _ = item_targets[0]
                    if not isinstance(target_object, visual_types):
                        issue(
                            "timeline.track_matte_item_nonvisual",
                            "track matte item must be a visual timeline item",
                            effect_path,
                        )
                        continue
                    target_item = target_object
                    if not target_item.enabled:
                        issue(
                            "timeline.track_matte_item_disabled",
                            "an item-referenced track matte must be enabled",
                            effect_path,
                        )
                        continue
                    if target_item.id == owner.id:
                        issue(
                            "timeline.track_matte_self_reference",
                            "a visual item cannot use itself as a track matte",
                            effect_path,
                        )
                        continue
                    required_ranges = [
                        owner.timeline_range,
                        *transition_windows.get(owner.id, []),
                    ]
                    if any(
                        target_item.timeline_range.intersection(required) != required
                        for required in required_ranges
                    ):
                        issue(
                            "timeline.track_matte_range_uncovered",
                            "an item-referenced matte must cover the owner item range",
                            effect_path,
                        )
                        continue
                    graph[owner.id].add(target_item.id)
                elif parsed.track_id is not None:
                    track_targets = track_matches.get(parsed.track_id, [])
                    if not track_targets:
                        issue(
                            "timeline.track_matte_track_missing",
                            f"track matte track {parsed.track_id!r} is missing",
                            effect_path,
                        )
                        continue
                    if len(track_targets) != 1:
                        issue(
                            "timeline.track_matte_track_ambiguous",
                            f"track matte track id {parsed.track_id!r} is not unique",
                            effect_path,
                        )
                        continue
                    target_track = track_targets[0][0]
                    if not isinstance(target_track, (VideoTrack, GraphicsTrack)):
                        issue(
                            "timeline.track_matte_track_nonvisual",
                            "track matte track must be a video or graphics track",
                            effect_path,
                        )
                        continue
                    for track_item in target_track.items:
                        if (
                            isinstance(track_item, visual_types)
                            and track_item.enabled
                            and track_item.timeline_range.overlaps(owner.timeline_range)
                        ):
                            graph[owner.id].add(track_item.id)

    visiting: list[str] = []
    visited: set[str] = set()
    reported: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        if node in visiting:
            cycle = tuple([*visiting[visiting.index(node) :], node])
            if cycle not in reported:
                reported.add(cycle)
                issue(
                    "timeline.track_matte_cycle",
                    "track matte dependencies contain a cycle: " + " -> ".join(cycle),
                    owner_paths.get(node, f"{sequence_path}.timeline"),
                )
            return
        if node in visited:
            return
        visiting.append(node)
        for dependency in sorted(graph.get(node, set())):
            visit(dependency)
        visiting.pop()
        visited.add(node)

    for owner_id in sorted(graph):
        visit(owner_id)
    return issues


def validate_project(project: Project) -> ValidationReport:
    issues: list[ValidationIssue] = []
    media_by_id = {media.id: media for media in project.media}
    for sequence_index, sequence in enumerate(project.sequences):
        for track_index, track in enumerate(sequence.timeline.tracks):
            track_path = f"sequences[{sequence_index}].timeline.tracks[{track_index}]"
            issues.extend(_validate_track(track, track_path))
            for item_index, item in enumerate(track.items):
                available = None
                source_range = None
                if isinstance(item, (Clip, AudioClip)):
                    available = media_by_id[item.media_reference_id].available_range
                    source_range = item.source_range
                elif isinstance(item, NestedSequenceClip):
                    try:
                        nested_duration = project.resolve_sequence(
                            item.sequence_id, item.sequence_version
                        ).timeline.duration
                    except StopIteration:
                        issues.append(
                            ValidationIssue(
                                code="timeline.missing_nested_sequence_revision",
                                severity=Severity.ERROR,
                                message="nested sequence revision is unavailable",
                                path=f"{track_path}.items[{item_index}].sequence_version",
                            )
                        )
                        continue
                    available = TimeRange(start=RationalTime.zero(), duration=nested_duration)
                    source_range = item.source_range
                if (
                    available is not None
                    and source_range is not None
                    and (source_range.start < available.start or source_range.end > available.end)
                ):
                    issues.append(
                        ValidationIssue(
                            code="timeline.source_range_outside_media",
                            severity=Severity.ERROR,
                            message="source range exceeds available media or nested sequence",
                            path=f"{track_path}.items[{item_index}].source_range",
                        )
                    )
        frame_rate = sequence.settings_override.frame_rate or project.settings.frame_rate
        issues.extend(_track_matte_issues(sequence, f"sequences[{sequence_index}]", frame_rate))
        item_ids = {item.id for track in sequence.timeline.tracks for item in track.items}
        for group_index, group in enumerate(sequence.timeline.link_groups):
            missing = sorted(set(group.item_ids) - item_ids)
            if missing:
                issues.append(
                    ValidationIssue(
                        code="timeline.broken_link_group",
                        severity=Severity.ERROR,
                        message="link group references missing items: " + ", ".join(missing),
                        path=(f"sequences[{sequence_index}].timeline.link_groups[{group_index}]"),
                    )
                )
    for snapshot_index, snapshot in enumerate(project.sequence_versions):
        sequence = snapshot.to_sequence()
        frame_rate = sequence.settings_override.frame_rate or project.settings.frame_rate
        issues.extend(
            _track_matte_issues(
                sequence,
                f"sequence_versions[{snapshot_index}]",
                frame_rate,
            )
        )
    issues.extend(_nested_cycles(project))
    return ValidationReport(issues=issues)
