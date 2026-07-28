"""Canonical project, caption, and interchange export service."""

from __future__ import annotations

import importlib
import re
import xml.etree.ElementTree as ET
from enum import StrEnum
from fractions import Fraction
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from video_engine.captions.service import CaptionService
from video_engine.config import EngineConfig
from video_engine.core.schema import (
    AudioClip,
    AudioItem,
    AudioTrack,
    CaptionTrack,
    Clip,
    Gap,
    GeneratorClip,
    GraphicsTrack,
    JsonValue,
    MediaReference,
    NestedSequenceClip,
    Project,
    Sequence,
    StillImageClip,
    Transition,
    VideoTrack,
    VisualItem,
)
from video_engine.core.time import FrameRate, RationalTime, RoundingMode, Timecode
from video_engine.errors import EngineError, ErrorCode
from video_engine.storage.atomic import atomic_write_text


class ExportFormat(StrEnum):
    PROJECT_JSON = "project-json"
    ASS = "ass"
    SRT = "srt"
    WEBVTT = "webvtt"
    CMX = "cmx"
    FCPXML = "fcpxml"
    OTIO = "otio"


class ExportDisposition(StrEnum):
    PRESERVED = "preserved"
    APPROXIMATED = "approximated"
    OMITTED = "omitted"


class ExportIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    disposition: ExportDisposition
    message: str = Field(min_length=1)
    canonical_path: str | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)


class ExportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    format: ExportFormat
    issues: tuple[ExportIssue, ...] = ()
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


def _time(value: RationalTime) -> str:
    normalized = value.fraction
    return (
        f"{normalized.numerator}s"
        if normalized.denominator == 1
        else f"{normalized.numerator}/{normalized.denominator}s"
    )


def _reel(reference: MediaReference) -> str:
    source = str(reference.extensions.get("cmx:reel") or reference.id)
    return re.sub(r"[^A-Za-z0-9]", "", source).upper()[:8] or "AX"


class ExportService:
    def __init__(self, project_root: Path, config: EngineConfig) -> None:
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)
        self.caption_service = CaptionService(self.config)

    def export(
        self,
        project: Project,
        path: Path,
        *,
        format: ExportFormat | str | None = None,
        sequence_id: str | None = None,
        caption_track_id: str | None = None,
    ) -> ExportResult:
        destination = path.resolve()
        export_format = self._format(destination, format)
        if export_format is ExportFormat.PROJECT_JSON:
            atomic_write_text(destination, project.model_dump_json(indent=2) + "\n")
            return ExportResult(path=destination, format=export_format)
        if export_format in {ExportFormat.ASS, ExportFormat.SRT, ExportFormat.WEBVTT}:
            return self._captions(
                project,
                destination,
                export_format,
                sequence_id,
                caption_track_id,
            )
        sequence = project.sequence(sequence_id)
        if export_format is ExportFormat.CMX:
            return self._cmx(project, sequence, destination)
        if export_format is ExportFormat.FCPXML:
            return self._fcpxml(project, sequence, destination)
        return self._otio(project, sequence, destination)

    @staticmethod
    def _format(path: Path, value: ExportFormat | str | None) -> ExportFormat:
        if value is not None:
            try:
                return ExportFormat(value)
            except ValueError as exc:
                raise EngineError(
                    ErrorCode.CONFIGURATION,
                    "export format is unsupported",
                    context={"format": str(value)},
                ) from exc
        suffix = path.suffix.lower()
        inferred = {
            ".json": ExportFormat.PROJECT_JSON,
            ".ass": ExportFormat.ASS,
            ".srt": ExportFormat.SRT,
            ".vtt": ExportFormat.WEBVTT,
            ".edl": ExportFormat.CMX,
            ".fcpxml": ExportFormat.FCPXML,
            ".otio": ExportFormat.OTIO,
        }.get(suffix)
        if inferred is None:
            raise EngineError(
                ErrorCode.CONFIGURATION,
                "export format cannot be inferred from the destination suffix",
                context={"path": str(path)},
            )
        return inferred

    def _captions(
        self,
        project: Project,
        destination: Path,
        export_format: ExportFormat,
        sequence_id: str | None,
        caption_track_id: str | None,
    ) -> ExportResult:
        required_suffix = {
            ExportFormat.ASS: ".ass",
            ExportFormat.SRT: ".srt",
            ExportFormat.WEBVTT: ".vtt",
        }[export_format]
        if destination.suffix.lower() != required_suffix:
            raise EngineError(
                ErrorCode.CONFIGURATION,
                "caption export path suffix does not match the requested format",
                context={
                    "format": export_format.value,
                    "path": str(destination),
                    "required_suffix": required_suffix,
                },
            )
        sequence = project.sequence(sequence_id)
        tracks = [
            track
            for track in sequence.timeline.tracks
            if isinstance(track, CaptionTrack) and track.enabled
        ]
        if caption_track_id is not None:
            tracks = [track for track in tracks if track.id == caption_track_id]
        if len(tracks) != 1:
            raise EngineError(
                ErrorCode.CONFIGURATION,
                "caption export requires exactly one selected caption track",
                context={"available": [track.id for track in tracks]},
            )
        result = self.caption_service.export(
            tracks[0],
            project.caption_styles,
            destination,
        )
        issues = tuple(
            ExportIssue(
                code=f"caption.{loss.feature}",
                disposition=ExportDisposition.OMITTED,
                message=loss.disposition,
                canonical_path=(
                    f"caption_item:{loss.item_id}" if loss.item_id is not None else None
                ),
            )
            for loss in result.losses
        )
        return ExportResult(
            path=result.path,
            format=export_format,
            issues=issues,
            metadata={"caption_track_id": tracks[0].id},
        )

    def _cmx(
        self,
        project: Project,
        sequence: Sequence,
        destination: Path,
    ) -> ExportResult:
        rate = sequence.settings_override.frame_rate or project.settings.frame_rate
        drop_frame = (rate.numerator, rate.denominator) in {
            (30_000, 1_001),
            (60_000, 1_001),
        }
        record_origin = self._timecode_origin(
            project.extensions.get("cmx:record_timecode_start"),
            rate,
            drop_frame,
        )
        media = {reference.id: reference for reference in project.media}
        issues: list[ExportIssue] = []
        events: list[tuple[RationalTime, str]] = []
        event_number = 0
        for track_index, track in enumerate(sequence.timeline.tracks):
            if not isinstance(track, (VideoTrack, AudioTrack)):
                if track.items:
                    issues.append(
                        ExportIssue(
                            code="cmx.track_omitted",
                            disposition=ExportDisposition.OMITTED,
                            message="CMX cannot represent this canonical track type",
                            canonical_path=f"tracks[{track_index}]",
                            details={"track_type": track.track_type.value},
                        )
                    )
                continue
            transitions = {item.to_item_id: item for item in track.transitions}
            designator = "V" if isinstance(track, VideoTrack) else "A"
            for item_index, item in enumerate(
                sorted(track.items, key=lambda value: value.timeline_range.start)
            ):
                event_number += 1
                record_in = record_origin + item.timeline_range.start
                record_out = record_origin + item.timeline_range.end
                transition = transitions.get(item.id)
                transition_code = "C"
                transition_field = ""
                if transition is not None:
                    transition_code = "D"
                    transition_frames = rate.time_to_frames(
                        transition.duration,
                        RoundingMode.NEAREST,
                    )
                    transition_field = f" {transition_frames:03d}"
                if isinstance(item, Gap):
                    reel = "BL"
                    source_in = RationalTime.zero()
                    source_out = item.timeline_range.duration
                    name = item.name
                elif isinstance(item, (Clip, AudioClip)):
                    reference = media[item.media_reference_id]
                    reel = _reel(reference)
                    source_origin = self._timecode_origin(
                        reference.extensions.get("cmx:source_timecode_start"),
                        rate,
                        drop_frame,
                    )
                    source_in = source_origin + item.source_range.start
                    source_out = source_origin + item.source_range.end
                    name = item.name or Path(reference.uri).name
                    if item.retime.rate.fraction != 1 or item.retime.reverse:
                        issues.append(
                            ExportIssue(
                                code="cmx.retime_approximated",
                                disposition=ExportDisposition.APPROXIMATED,
                                message=(
                                    "CMX event ranges preserve retime endpoints; "
                                    "reverse/pitch policy is not native"
                                ),
                                canonical_path=f"tracks[{track_index}].items[{item_index}]",
                            )
                        )
                else:
                    issues.append(
                        ExportIssue(
                            code="cmx.item_omitted",
                            disposition=ExportDisposition.OMITTED,
                            message="CMX cannot represent this timeline item",
                            canonical_path=f"tracks[{track_index}].items[{item_index}]",
                            details={"item_type": item.item_type},
                        )
                    )
                    continue
                line = (
                    f"{event_number:03d}  {reel:<8} {designator:<5} "
                    f"{transition_code}{transition_field:<4} "
                    f"{self._timecode(source_in, rate, drop_frame)} "
                    f"{self._timecode(source_out, rate, drop_frame)} "
                    f"{self._timecode(record_in, rate, drop_frame)} "
                    f"{self._timecode(record_out, rate, drop_frame)}"
                )
                comment = f"\n* FROM CLIP NAME: {name}" if name else ""
                events.append((item.timeline_range.start, line + comment))
        header = [
            f"TITLE: {project.name}",
            f"FCM: {'DROP FRAME' if drop_frame else 'NON-DROP FRAME'}",
            "",
        ]
        body = "\n".join([*header, *(line for _, line in sorted(events)), ""])
        atomic_write_text(destination, body)
        return ExportResult(
            path=destination,
            format=ExportFormat.CMX,
            issues=tuple(issues),
            metadata={"event_count": len(events), "frame_rate": str(rate.fraction)},
        )

    def _fcpxml(
        self,
        project: Project,
        sequence: Sequence,
        destination: Path,
    ) -> ExportResult:
        width = sequence.settings_override.width or project.settings.width
        height = sequence.settings_override.height or project.settings.height
        frame_rate = sequence.settings_override.frame_rate or project.settings.frame_rate
        root = ET.Element("fcpxml", {"version": "1.10"})
        resources = ET.SubElement(root, "resources")
        format_ids: dict[str, str] = {}
        for candidate in project.sequences:
            candidate_width = candidate.settings_override.width or project.settings.width
            candidate_height = candidate.settings_override.height or project.settings.height
            candidate_rate = candidate.settings_override.frame_rate or project.settings.frame_rate
            format_id = f"r-format-{len(format_ids) + 1}"
            format_ids[candidate.id] = format_id
            ET.SubElement(
                resources,
                "format",
                {
                    "id": format_id,
                    "frameDuration": _time(candidate_rate.frame_duration),
                    "width": str(candidate_width),
                    "height": str(candidate_height),
                },
            )
        resource_ids: dict[str, str] = {}
        video_media = {
            item.media_reference_id
            for candidate in project.sequences
            for track in candidate.timeline.tracks
            if isinstance(track, (VideoTrack, GraphicsTrack))
            for item in track.items
            if isinstance(item, (Clip, StillImageClip))
        }
        audio_media = {
            item.media_reference_id
            for candidate in project.sequences
            for track in candidate.timeline.tracks
            for item in track.items
            if isinstance(item, AudioClip) or (isinstance(item, Clip) and item.source_audio_enabled)
        }
        for index, reference in enumerate(project.media, start=1):
            resource_id = f"r-asset-{index}"
            resource_ids[reference.id] = resource_id
            asset = ET.SubElement(
                resources,
                "asset",
                {
                    "id": resource_id,
                    "name": Path(reference.uri).name or reference.id,
                    "start": "0s",
                    "hasVideo": (
                        "1"
                        if any(stream.codec_type == "video" for stream in reference.streams)
                        or reference.id in video_media
                        else "0"
                    ),
                    "hasAudio": (
                        "1"
                        if any(stream.codec_type == "audio" for stream in reference.streams)
                        or reference.id in audio_media
                        else "0"
                    ),
                },
            )
            ET.SubElement(
                asset,
                "media-rep",
                {"kind": "original-media", "src": self._media_uri(reference.uri)},
            )
        nested_resource_ids = {
            candidate.id: f"r-sequence-{index}"
            for index, candidate in enumerate(
                (item for item in project.sequences if item.id != sequence.id),
                start=1,
            )
        }
        issues: list[ExportIssue] = []
        for candidate in project.sequences:
            if candidate.id == sequence.id:
                continue
            media_resource = ET.SubElement(
                resources,
                "media",
                {
                    "id": nested_resource_ids[candidate.id],
                    "name": candidate.name,
                },
            )
            nested_element = ET.SubElement(
                media_resource,
                "sequence",
                {
                    "format": format_ids[candidate.id],
                    "duration": _time(candidate.timeline.duration),
                    "tcStart": "0s",
                },
            )
            self._fcpxml_spine(
                nested_element,
                candidate,
                resource_ids,
                nested_resource_ids,
                issues,
                path=f"sequences[{candidate.id}]",
            )
        library = ET.SubElement(root, "library")
        event = ET.SubElement(library, "event", {"name": project.name})
        project_element = ET.SubElement(event, "project", {"name": project.name})
        sequence_element = ET.SubElement(
            project_element,
            "sequence",
            {
                "format": format_ids[sequence.id],
                "duration": _time(sequence.timeline.duration),
                "tcStart": "0s",
            },
        )
        self._fcpxml_spine(
            sequence_element,
            sequence,
            resource_ids,
            nested_resource_ids,
            issues,
            path=f"sequences[{sequence.id}]",
        )
        if width != project.settings.width or height != project.settings.height:
            issues.append(
                ExportIssue(
                    code="fcpxml.sequence_settings_preserved",
                    disposition=ExportDisposition.PRESERVED,
                    message="sequence-specific dimensions were emitted as an FCP format",
                    canonical_path=f"sequences[{sequence.id}].settings_override",
                )
            )
        if frame_rate != project.settings.frame_rate:
            issues.append(
                ExportIssue(
                    code="fcpxml.sequence_rate_preserved",
                    disposition=ExportDisposition.PRESERVED,
                    message="sequence-specific frame rate was emitted as an FCP format",
                    canonical_path=f"sequences[{sequence.id}].settings_override",
                )
            )
        ET.indent(root, space="  ")
        content = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            root,
            encoding="unicode",
        )
        atomic_write_text(destination, content + "\n")
        return ExportResult(
            path=destination,
            format=ExportFormat.FCPXML,
            issues=tuple(issues),
            metadata={"sequence_id": sequence.id},
        )

    def _fcpxml_spine(
        self,
        sequence_element: ET.Element,
        sequence: Sequence,
        resource_ids: dict[str, str],
        nested_resource_ids: dict[str, str],
        issues: list[ExportIssue],
        *,
        path: str,
    ) -> None:
        spine = ET.SubElement(sequence_element, "spine")
        for track_index, track in enumerate(sequence.timeline.tracks):
            if isinstance(track, VideoTrack):
                lane = 0 if track_index == 0 else track_index
                self._fcpxml_items(
                    spine,
                    track.items,
                    resource_ids,
                    nested_resource_ids,
                    lane,
                    issues,
                    f"{path}.tracks[{track_index}]",
                )
                self._fcpxml_transitions(spine, track.transitions, track.items)
            elif isinstance(track, AudioTrack):
                self._fcpxml_items(
                    spine,
                    track.items,
                    resource_ids,
                    nested_resource_ids,
                    -(track_index + 1),
                    issues,
                    f"{path}.tracks[{track_index}]",
                )
            elif isinstance(track, CaptionTrack):
                for item in track.items:
                    if isinstance(item, Gap) or item.suppressed:
                        continue
                    ET.SubElement(
                        spine,
                        "caption",
                        {
                            "offset": _time(item.timeline_range.start),
                            "duration": _time(item.timeline_range.duration),
                            "value": item.text,
                            "role": item.speaker or "caption",
                        },
                    )
            elif isinstance(track, GraphicsTrack):
                issues.append(
                    ExportIssue(
                        code="fcpxml.graphics_omitted",
                        disposition=ExportDisposition.OMITTED,
                        message="registered graphics have no portable FCP title-template resource",
                        canonical_path=f"{path}.tracks[{track_index}]",
                    )
                )
        if sequence.timeline.markers:
            issues.append(
                ExportIssue(
                    code="fcpxml.markers_omitted",
                    disposition=ExportDisposition.OMITTED,
                    message=(
                        "standalone canonical markers require item-relative placement in "
                        "FCPXML and remain in the canonical project"
                    ),
                    canonical_path=f"{path}.timeline.markers",
                    details={"count": len(sequence.timeline.markers)},
                )
            )

    @staticmethod
    def _fcpxml_items(
        spine: ET.Element,
        items: list[VisualItem] | list[AudioItem],
        resource_ids: dict[str, str],
        nested_resource_ids: dict[str, str],
        lane: int,
        issues: list[ExportIssue],
        path: str,
    ) -> None:
        for index, item in enumerate(items):
            attributes = {
                "offset": _time(item.timeline_range.start),
                "duration": _time(item.timeline_range.duration),
            }
            if lane:
                attributes["lane"] = str(lane)
            if isinstance(item, Gap):
                ET.SubElement(spine, "gap", attributes)
            elif isinstance(item, (Clip, AudioClip)):
                attributes.update(
                    {
                        "ref": resource_ids[item.media_reference_id],
                        "name": item.name or item.id,
                        "start": _time(item.source_range.start),
                    }
                )
                ET.SubElement(spine, "asset-clip", attributes)
            elif isinstance(item, StillImageClip):
                attributes.update(
                    {
                        "ref": resource_ids[item.media_reference_id],
                        "name": item.name or item.id,
                        "start": "0s",
                    }
                )
                ET.SubElement(spine, "asset-clip", attributes)
            elif isinstance(item, NestedSequenceClip):
                nested_resource_id = nested_resource_ids.get(item.sequence_id)
                if nested_resource_id is None:
                    issues.append(
                        ExportIssue(
                            code="fcpxml.nested_omitted",
                            disposition=ExportDisposition.OMITTED,
                            message=(
                                "a nested reference to the selected project sequence cannot "
                                "be represented without a recursive media resource"
                            ),
                            canonical_path=f"{path}.items[{index}]",
                        )
                    )
                    continue
                attributes.update(
                    {
                        "ref": nested_resource_id,
                        "name": item.name or item.id,
                        "start": _time(item.source_range.start),
                    }
                )
                ET.SubElement(spine, "ref-clip", attributes)
            elif isinstance(item, GeneratorClip):
                issues.append(
                    ExportIssue(
                        code="fcpxml.generator_omitted",
                        disposition=ExportDisposition.OMITTED,
                        message="registered generator has no portable FCP effect resource",
                        canonical_path=f"{path}.items[{index}]",
                    )
                )

    @staticmethod
    def _fcpxml_transitions(
        spine: ET.Element,
        transitions: list[Transition],
        items: list[Any],
    ) -> None:
        items_by_id = {item.id: item for item in items}
        for transition in transitions:
            right = items_by_id.get(transition.to_item_id)
            if right is None:
                continue
            ET.SubElement(
                spine,
                "transition",
                {
                    "name": "Cross Dissolve",
                    "offset": _time(right.timeline_range.start),
                    "duration": _time(transition.duration),
                },
            )

    def _otio(
        self,
        project: Project,
        sequence: Sequence,
        destination: Path,
    ) -> ExportResult:
        try:
            otio = importlib.import_module("opentimelineio")
        except ModuleNotFoundError as exc:
            raise EngineError(
                ErrorCode.DEPENDENCY_MISSING,
                "OpenTimelineIO export requires the interchange dependency group",
                context={"install": "uv sync --extra interchange"},
            ) from exc
        timeline = otio.schema.Timeline(name=project.name)
        media = {reference.id: reference for reference in project.media}
        issues: list[ExportIssue] = []
        for track_index, source_track in enumerate(sequence.timeline.tracks):
            if not isinstance(source_track, (VideoTrack, AudioTrack)):
                if source_track.items:
                    issues.append(
                        ExportIssue(
                            code="otio.track_omitted",
                            disposition=ExportDisposition.OMITTED,
                            message="track type is not represented by this OTIO exporter",
                            canonical_path=f"tracks[{track_index}]",
                        )
                    )
                continue
            kind = (
                otio.schema.TrackKind.Video
                if isinstance(source_track, VideoTrack)
                else otio.schema.TrackKind.Audio
            )
            track = otio.schema.Track(name=source_track.name, kind=kind)
            transitions = {item.to_item_id: item for item in source_track.transitions}
            for item in sorted(source_track.items, key=lambda value: value.timeline_range.start):
                transition = transitions.get(item.id)
                if transition is not None:
                    half = transition.duration * Fraction(1, 2)
                    track.append(
                        otio.schema.Transition(
                            transition_type=otio.schema.TransitionTypes.SMPTE_Dissolve,
                            in_offset=self._otio_time(otio, half),
                            out_offset=self._otio_time(otio, transition.duration - half),
                        )
                    )
                if isinstance(item, Gap):
                    track.append(
                        otio.schema.Gap(
                            source_range=otio.opentime.TimeRange(
                                self._otio_time(otio, RationalTime.zero()),
                                self._otio_time(otio, item.timeline_range.duration),
                            )
                        )
                    )
                elif isinstance(item, (Clip, AudioClip)):
                    reference = media[item.media_reference_id]
                    track.append(
                        otio.schema.Clip(
                            name=item.name or item.id,
                            media_reference=otio.schema.ExternalReference(
                                target_url=self._media_uri(reference.uri)
                            ),
                            source_range=otio.opentime.TimeRange(
                                self._otio_time(otio, item.source_range.start),
                                self._otio_time(otio, item.source_range.duration),
                            ),
                        )
                    )
                else:
                    issues.append(
                        ExportIssue(
                            code="otio.item_omitted",
                            disposition=ExportDisposition.OMITTED,
                            message="timeline item is not represented by this OTIO exporter",
                            canonical_path=f"tracks[{track_index}].items[{item.id}]",
                        )
                    )
            timeline.tracks.append(track)
        try:
            content = otio.adapters.write_to_string(timeline, adapter_name="otio_json")
        except Exception as exc:
            raise EngineError(
                ErrorCode.STORAGE,
                "OpenTimelineIO export failed",
                context={"detail": str(exc)},
            ) from exc
        atomic_write_text(destination, str(content))
        return ExportResult(
            path=destination,
            format=ExportFormat.OTIO,
            issues=tuple(issues),
            metadata={"sequence_id": sequence.id},
        )

    @staticmethod
    def _otio_time(otio: Any, value: RationalTime) -> Any:
        return otio.opentime.RationalTime(value.value, value.timescale)

    @staticmethod
    def _timecode_origin(
        value: JsonValue,
        rate: FrameRate,
        drop_frame: bool,
    ) -> RationalTime:
        if isinstance(value, str):
            try:
                return Timecode.parse(value, rate, drop_frame=drop_frame).time
            except ValueError:
                pass
        return RationalTime.zero()

    @staticmethod
    def _timecode(value: RationalTime, rate: FrameRate, drop_frame: bool) -> str:
        return str(Timecode(time=value, rate=rate, drop_frame=drop_frame))

    @staticmethod
    def _media_uri(value: str) -> str:
        if "://" in value:
            return value
        path = Path(value)
        return path.resolve().as_uri()
