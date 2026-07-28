"""Native CMX 3600 import with exact timecode and explicit loss accounting."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from video_engine.config import EngineConfig
from video_engine.core.schema import (
    AudioClip,
    AudioRole,
    AudioTrack,
    Clip,
    DeliveryProfile,
    Gap,
    JsonValue,
    MediaReference,
    Project,
    ProjectSettings,
    Retime,
    Sequence,
    Timeline,
    Transition,
    TransitionKind,
    VideoTrack,
)
from video_engine.core.time import (
    FrameRate,
    RationalRate,
    RationalTime,
    Timecode,
    TimeRange,
)
from video_engine.core.validation import validate_project
from video_engine.errors import EngineError, ErrorCode
from video_engine.media.service import MediaService
from video_engine.render.cache import sha256_file

from .models import (
    AdapterKind,
    MigrationDisposition,
    MigrationIssue,
    MigrationReport,
    MigrationResult,
    MigrationSeverity,
)

_EVENT = re.compile(
    r"^\s*(?P<number>\d{3,6})\s+"
    r"(?P<reel>\S+)\s+(?P<track>\S+)\s+(?P<transition>\S+)\s+"
    r"(?:(?P<transition_frames>\d+)\s+)?"
    r"(?P<source_in>\d{2}:[0-5]\d:[0-5]\d[:;]\d{2})\s+"
    r"(?P<source_out>\d{2}:[0-5]\d:[0-5]\d[:;]\d{2})\s+"
    r"(?P<record_in>\d{2}:[0-5]\d:[0-5]\d[:;]\d{2})\s+"
    r"(?P<record_out>\d{2}:[0-5]\d:[0-5]\d[:;]\d{2})\s*$"
)
_SOURCE_COMMENT = re.compile(
    r"^\*\s*(?:FROM CLIP NAME|SOURCE FILE)\s*:\s*(?P<value>.+?)\s*$",
    flags=re.IGNORECASE,
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "cmx"


def _tc(
    value: str,
    rate: FrameRate,
    *,
    drop_frame: bool | None = None,
    line_number: int | None = None,
) -> Timecode:
    try:
        return Timecode.parse(value, rate, drop_frame=drop_frame)
    except ValueError as exc:
        raise EngineError(
            ErrorCode.MIGRATION,
            "CMX timecode is invalid",
            context={"timecode": value, "line": line_number, "detail": str(exc)},
        ) from exc


@dataclass(slots=True)
class _CMXEvent:
    line_number: int
    number: str
    reel: str
    track: str
    transition: str
    transition_frames: int | None
    source_in: str
    source_out: str
    record_in: str
    record_out: str
    comments: list[str] = field(default_factory=list)

    @property
    def source_comment(self) -> str | None:
        for comment in self.comments:
            if match := _SOURCE_COMMENT.match(comment):
                return match.group("value")
        return None


class CMXAdapterService:
    def __init__(self, project_root: Path, config: EngineConfig) -> None:
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)
        self.media_service = MediaService(self.project_root, self.config)

    def import_file(
        self,
        path: Path,
        *,
        frame_rate: FrameRate | None = None,
        name: str | None = None,
        media_paths: dict[str, Path] | None = None,
        source_timecodes: dict[str, str] | None = None,
    ) -> MigrationResult:
        source = path.resolve()
        try:
            text = source.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise EngineError(
                ErrorCode.MIGRATION,
                "failed to read CMX EDL",
                context={"path": str(source), "detail": str(exc)},
            ) from exc
        title, drop_frame, events, header_lines = self._parse(text)
        if not events:
            raise EngineError(ErrorCode.MIGRATION, "CMX EDL contains no events")
        rate = self._rate(frame_rate, drop_frame)
        self._validate_separators(events, drop_frame)
        issues: list[MigrationIssue] = []
        references, resolved, offline = self._references(
            source.parent,
            events,
            media_paths or {},
            issues,
        )
        source_bases = self._source_bases(
            events,
            references,
            rate,
            drop_frame,
            source_timecodes or {},
            issues,
        )
        record_times = [
            _tc(
                event.record_in,
                rate,
                drop_frame=drop_frame,
                line_number=event.line_number,
            ).time
            for event in events
        ]
        record_base = min(record_times)
        width, height = self._dimensions(references)
        digest = sha256_file(source)
        project = self._project(
            name or title or source.stem,
            digest[:12],
            width,
            height,
            rate,
        )
        project.media = list(references.values())
        project.extensions["cmx:header_lines"] = header_lines
        project.extensions["cmx:record_timecode_start"] = str(
            Timecode(time=record_base, rate=rate, drop_frame=drop_frame)
        )
        video_tracks: list[VideoTrack] = []
        audio_tracks: list[AudioTrack] = []
        for event in sorted(
            events,
            key=lambda item: (self._record_start(item, rate), item.line_number),
        ):
            timeline_range = self._timeline_range(event, rate, drop_frame, record_base)
            if event.reel.upper() in {"BL", "BLACK", "BLK"}:
                self._append_gap(event, timeline_range, video_tracks, audio_tracks)
                continue
            reference = references[event.reel]
            source_range, retime = self._source_range(
                event,
                rate,
                drop_frame,
                source_bases[event.reel],
                timeline_range.duration,
                issues,
            )
            channels = self._channels(event.track)
            if "video" in channels:
                video_item = Clip(
                    id=f"cmx-{event.number}-v-l{event.line_number}",
                    name=event.source_comment or event.reel,
                    media_reference_id=reference.id,
                    timeline_range=timeline_range,
                    source_range=source_range,
                    source_audio_enabled=False,
                    retime=retime,
                    extensions=self._event_extensions(event),
                )
                video_track, previous_video = self._place_video(video_tracks, video_item)
                self._transition(event, rate, video_track, previous_video, video_item.id, issues)
            if "audio" in channels:
                audio_item = AudioClip(
                    id=f"cmx-{event.number}-a-l{event.line_number}",
                    name=event.source_comment or event.reel,
                    media_reference_id=reference.id,
                    timeline_range=timeline_range,
                    source_range=source_range,
                    role=AudioRole.SOURCE,
                    retime=retime,
                    extensions=self._event_extensions(event),
                )
                audio_track, previous_audio = self._place_audio(audio_tracks, audio_item)
                self._transition(event, rate, audio_track, previous_audio, audio_item.id, issues)
            if channels == set():
                issues.append(
                    self._issue(
                        "cmx.unsupported_track_designator",
                        "event track designator is preserved but was not placed",
                        MigrationDisposition.PRESERVED,
                        event,
                        details={"track": event.track},
                    )
                )
        project.sequence().timeline.tracks.extend([*video_tracks, *audio_tracks])
        self._unsupported_lines(events, issues)
        self._validation_issues(project, issues)
        return MigrationResult(
            project=project,
            report=MigrationReport(
                adapter=AdapterKind.CMX_EDL,
                source_path=source,
                source_sha256=digest,
                source_schema="cmx-3600",
                project_id=project.id,
                project_schema_version=project.schema_version,
                issues=tuple(issues),
                preserved_metadata={
                    "title": title,
                    "fcm": "DROP FRAME" if drop_frame else "NON-DROP FRAME",
                    "event_count": len(events),
                    "header_lines": header_lines,
                },
                resolved_assets=tuple(sorted(resolved)),
                offline_assets=tuple(sorted(offline)),
            ),
        )

    @staticmethod
    def _parse(text: str) -> tuple[str | None, bool, list[_CMXEvent], list[str]]:
        title: str | None = None
        drop_frame: bool | None = None
        events: list[_CMXEvent] = []
        header_lines: list[str] = []
        current: _CMXEvent | None = None
        for line_number, raw in enumerate(text.splitlines(), start=1):
            line = raw.rstrip()
            upper = line.upper().strip()
            if upper.startswith("TITLE:"):
                title = line.split(":", 1)[1].strip() or None
                header_lines.append(line)
                continue
            if upper.startswith("FCM:"):
                mode = upper.split(":", 1)[1].strip()
                if mode not in {"DROP FRAME", "NON-DROP FRAME"}:
                    raise EngineError(
                        ErrorCode.MIGRATION,
                        "CMX FCM must be DROP FRAME or NON-DROP FRAME",
                        context={"line": line_number, "value": mode},
                    )
                drop_frame = mode == "DROP FRAME"
                header_lines.append(line)
                continue
            if match := _EVENT.match(line):
                data = match.groupdict()
                current = _CMXEvent(
                    line_number=line_number,
                    number=data["number"],
                    reel=data["reel"],
                    track=data["track"],
                    transition=data["transition"].upper(),
                    transition_frames=(
                        int(data["transition_frames"])
                        if data["transition_frames"] is not None
                        else None
                    ),
                    source_in=data["source_in"],
                    source_out=data["source_out"],
                    record_in=data["record_in"],
                    record_out=data["record_out"],
                )
                events.append(current)
                continue
            if line.lstrip().startswith(("*", "M2")) and current is not None:
                current.comments.append(line)
            elif line.strip():
                header_lines.append(line)
        if drop_frame is None:
            separators = {
                ";" in value
                for event in events
                for value in (
                    event.source_in,
                    event.source_out,
                    event.record_in,
                    event.record_out,
                )
            }
            if len(separators) != 1:
                raise EngineError(
                    ErrorCode.MIGRATION,
                    "CMX EDL mixes drop and non-drop separators without an FCM header",
                )
            drop_frame = separators.pop()
        return title, drop_frame, events, header_lines

    @staticmethod
    def _rate(frame_rate: FrameRate | None, drop_frame: bool) -> FrameRate:
        if frame_rate is not None:
            if drop_frame and (frame_rate.numerator, frame_rate.denominator) not in {
                (30_000, 1_001),
                (60_000, 1_001),
            }:
                raise EngineError(
                    ErrorCode.MIGRATION,
                    "drop-frame CMX requires 30000/1001 or 60000/1001",
                )
            return frame_rate
        if drop_frame:
            return FrameRate.fps_29_97()
        raise EngineError(
            ErrorCode.MIGRATION,
            "non-drop CMX import requires an explicit frame rate",
            context={"hint": "pass frame_rate or --fps-num/--fps-den"},
        )

    @staticmethod
    def _validate_separators(events: list[_CMXEvent], drop_frame: bool) -> None:
        expected = ";" if drop_frame else ":"
        for event in events:
            for value in (event.source_in, event.source_out, event.record_in, event.record_out):
                if value[-3] != expected:
                    raise EngineError(
                        ErrorCode.MIGRATION,
                        "CMX timecode separator disagrees with FCM mode",
                        context={"line": event.line_number, "timecode": value},
                    )

    def _references(
        self,
        base: Path,
        events: list[_CMXEvent],
        media_paths: dict[str, Path],
        issues: list[MigrationIssue],
    ) -> tuple[dict[str, MediaReference], list[str], list[str]]:
        references: dict[str, MediaReference] = {}
        resolved: list[str] = []
        offline: list[str] = []
        for reel in sorted(
            {event.reel for event in events if event.reel.upper() not in {"BL", "BLACK", "BLK"}}
        ):
            event = next(item for item in events if item.reel == reel)
            candidate = media_paths.get(reel)
            if candidate is None and event.source_comment:
                comment_path = Path(event.source_comment)
                candidate = comment_path if comment_path.is_absolute() else base / comment_path
            if candidate is not None and candidate.resolve().is_file():
                record = self.media_service.import_media(candidate.resolve(), deep_vfr=False)
                reference = self.media_service.to_media_reference(record)
                reference.extensions["cmx:reel"] = reel
                reference.extensions.update(record.probe.extensions)
                references[reel] = reference
                resolved.append(str(candidate.resolve()))
                continue
            identity = hashlib.sha256(f"cmx-offline:{reel}".encode()).hexdigest()[:16]
            uri = str(candidate.resolve()) if candidate is not None else f"offline://{reel}"
            references[reel] = MediaReference(
                id=f"offline-{identity}",
                uri=uri,
                offline=True,
                extensions={"cmx:reel": reel, "cmx:source_comment": event.source_comment},
            )
            offline.append(uri)
            issues.append(
                self._issue(
                    "cmx.media_offline",
                    "reel has no resolved media and remains relinkable",
                    MigrationDisposition.PRESERVED,
                    event,
                    details={"reel": reel, "uri": uri},
                )
            )
        return references, resolved, offline

    def _source_bases(
        self,
        events: list[_CMXEvent],
        references: dict[str, MediaReference],
        rate: FrameRate,
        drop_frame: bool,
        declared: dict[str, str],
        issues: list[MigrationIssue],
    ) -> dict[str, RationalTime]:
        bases: dict[str, RationalTime] = {}
        for reel, reference in references.items():
            label = declared.get(reel)
            if label is None:
                tags = reference.extensions.get("ffprobe:format_tags")
                if isinstance(tags, dict) and isinstance(tags.get("timecode"), str):
                    label = tags["timecode"]
            if label is not None:
                bases[reel] = _tc(label, rate, drop_frame=drop_frame).time
                reference.extensions["cmx:source_timecode_start"] = label
                continue
            reel_events = [event for event in events if event.reel == reel]
            base = min(
                _tc(
                    event.source_in,
                    rate,
                    drop_frame=drop_frame,
                    line_number=event.line_number,
                ).time
                for event in reel_events
            )
            bases[reel] = base
            inferred = str(Timecode(time=base, rate=rate, drop_frame=drop_frame))
            reference.extensions["cmx:inferred_source_timecode_start"] = inferred
            issues.append(
                self._issue(
                    "cmx.source_timecode_inferred",
                    "source timecode origin was inferred from the earliest reel event",
                    MigrationDisposition.APPROXIMATED,
                    reel_events[0],
                    details={"reel": reel, "inferred": inferred},
                )
            )
        return bases

    @staticmethod
    def _record_start(event: _CMXEvent, rate: FrameRate) -> RationalTime:
        return _tc(event.record_in, rate, line_number=event.line_number).time

    @staticmethod
    def _timeline_range(
        event: _CMXEvent,
        rate: FrameRate,
        drop_frame: bool,
        record_base: RationalTime,
    ) -> TimeRange:
        start = _tc(
            event.record_in,
            rate,
            drop_frame=drop_frame,
            line_number=event.line_number,
        ).time
        end = _tc(
            event.record_out,
            rate,
            drop_frame=drop_frame,
            line_number=event.line_number,
        ).time
        if end <= start:
            raise EngineError(
                ErrorCode.MIGRATION,
                "CMX record range must be positive",
                context={"line": event.line_number},
            )
        return TimeRange(start=start - record_base, duration=end - start)

    @staticmethod
    def _source_range(
        event: _CMXEvent,
        rate: FrameRate,
        drop_frame: bool,
        source_base: RationalTime,
        timeline_duration: RationalTime,
        issues: list[MigrationIssue],
    ) -> tuple[TimeRange, Retime]:
        source_in = _tc(
            event.source_in,
            rate,
            drop_frame=drop_frame,
            line_number=event.line_number,
        ).time
        source_out = _tc(
            event.source_out,
            rate,
            drop_frame=drop_frame,
            line_number=event.line_number,
        ).time
        if source_out <= source_in or source_in < source_base:
            raise EngineError(
                ErrorCode.MIGRATION,
                "CMX source range is invalid after timecode rebasing",
                context={"line": event.line_number},
            )
        source_duration = source_out - source_in
        ratio = source_duration.fraction / timeline_duration.fraction
        retime = Retime(rate=RationalRate(numerator=ratio.numerator, denominator=ratio.denominator))
        if ratio != 1:
            issues.append(
                CMXAdapterService._issue(
                    "cmx.constant_retime_inferred",
                    "source and record durations imply a constant playback rate",
                    MigrationDisposition.EXECUTED,
                    event,
                    details={"rate": str(ratio)},
                    severity=MigrationSeverity.INFO,
                )
            )
        return (
            TimeRange(start=source_in - source_base, duration=source_duration),
            retime,
        )

    @staticmethod
    def _channels(value: str) -> set[Literal["video", "audio"]]:
        upper = value.upper()
        channels: set[Literal["video", "audio"]] = set()
        if "V" in upper or upper == "B":
            channels.add("video")
        if "A" in upper or upper == "B":
            channels.add("audio")
        return channels

    @staticmethod
    def _place_video(
        tracks: list[VideoTrack], item: Clip | Gap
    ) -> tuple[VideoTrack, Clip | Gap | None]:
        for track in tracks:
            previous = max(track.items, key=lambda value: value.timeline_range.end, default=None)
            if previous is not None and not isinstance(previous, (Clip, Gap)):
                raise AssertionError("CMX video lane contains an unsupported item")
            if previous is None or previous.timeline_range.end <= item.timeline_range.start:
                track.items.append(item)
                return track, previous
        index = len(tracks) + 1
        track = VideoTrack(id=f"cmx-video-{index}", name=f"CMX video lane {index}")
        track.items.append(item)
        tracks.append(track)
        return track, None

    @staticmethod
    def _place_audio(
        tracks: list[AudioTrack], item: AudioClip | Gap
    ) -> tuple[AudioTrack, AudioClip | Gap | None]:
        for track in tracks:
            previous = max(track.items, key=lambda value: value.timeline_range.end, default=None)
            if previous is not None and not isinstance(previous, (AudioClip, Gap)):
                raise AssertionError("CMX audio lane contains an unsupported item")
            if previous is None or previous.timeline_range.end <= item.timeline_range.start:
                track.items.append(item)
                return track, previous
        index = len(tracks) + 1
        track = AudioTrack(
            id=f"cmx-audio-{index}",
            name=f"CMX audio lane {index}",
            role=AudioRole.SOURCE,
        )
        track.items.append(item)
        tracks.append(track)
        return track, None

    @staticmethod
    def _append_gap(
        event: _CMXEvent,
        timeline_range: TimeRange,
        video_tracks: list[VideoTrack],
        audio_tracks: list[AudioTrack],
    ) -> None:
        channels = CMXAdapterService._channels(event.track)
        if "video" in channels:
            item = Gap(
                id=f"cmx-{event.number}-gap-v-l{event.line_number}",
                timeline_range=timeline_range,
                extensions=CMXAdapterService._event_extensions(event),
            )
            CMXAdapterService._place_video(video_tracks, item)
        if "audio" in channels:
            item = Gap(
                id=f"cmx-{event.number}-gap-a-l{event.line_number}",
                timeline_range=timeline_range,
                extensions=CMXAdapterService._event_extensions(event),
            )
            CMXAdapterService._place_audio(audio_tracks, item)

    @staticmethod
    def _transition(
        event: _CMXEvent,
        rate: FrameRate,
        track: VideoTrack | AudioTrack,
        previous: Clip | AudioClip | Gap | None,
        item_id: str,
        issues: list[MigrationIssue],
    ) -> None:
        if event.transition == "C":
            return
        if event.transition == "D" and event.transition_frames and previous is not None:
            current = next(item for item in track.items if item.id == item_id)
            if previous.timeline_range.end == current.timeline_range.start:
                track.transitions.append(
                    Transition(
                        id=f"cmx-transition-{event.line_number}-{track.id}",
                        from_item_id=previous.id,
                        to_item_id=item_id,
                        duration=rate.frames_to_time(event.transition_frames),
                        kind=TransitionKind.DISSOLVE,
                        extensions={"cmx:transition": event.transition},
                    )
                )
                return
        issues.append(
            CMXAdapterService._issue(
                "cmx.transition_preserved",
                "unsupported or non-adjacent CMX transition was preserved",
                MigrationDisposition.PRESERVED,
                event,
                details={
                    "transition": event.transition,
                    "duration_frames": event.transition_frames,
                },
            )
        )

    @staticmethod
    def _event_extensions(event: _CMXEvent) -> dict[str, JsonValue]:
        return {
            "cmx:event_number": event.number,
            "cmx:line_number": event.line_number,
            "cmx:reel": event.reel,
            "cmx:track": event.track,
            "cmx:transition": event.transition,
            "cmx:comments": event.comments,
            "cmx:source_timecodes": {"in": event.source_in, "out": event.source_out},
            "cmx:record_timecodes": {"in": event.record_in, "out": event.record_out},
        }

    @staticmethod
    def _unsupported_lines(events: list[_CMXEvent], issues: list[MigrationIssue]) -> None:
        for event in events:
            for comment in event.comments:
                if comment.lstrip().startswith("M2"):
                    issues.append(
                        CMXAdapterService._issue(
                            "cmx.m2_preserved",
                            "CMX M2 motion metadata was preserved; source/record duration "
                            "still drives retime",
                            MigrationDisposition.PRESERVED,
                            event,
                            details={"line": comment},
                        )
                    )

    @staticmethod
    def _dimensions(references: dict[str, MediaReference]) -> tuple[int, int]:
        dimensions = [
            (stream.width, stream.height)
            for reference in references.values()
            for stream in reference.streams
            if stream.codec_type == "video" and stream.width and stream.height
        ]
        if not dimensions:
            return 1920, 1080
        width, height = max(dimensions, key=lambda value: value[0] * value[1])
        return width - width % 2, height - height % 2

    @staticmethod
    def _project(
        name: str,
        identity: str,
        width: int,
        height: int,
        rate: FrameRate,
    ) -> Project:
        profiles = [
            DeliveryProfile(
                id=profile_id,
                name=profile_name,
                width=width,
                height=height,
                frame_rate=rate,
                crf=crf,
                preset=preset,
            )
            for profile_id, profile_name, crf, preset in (
                ("preview", "Preview", 22, "veryfast"),
                ("final", "Final", 18, "medium"),
            )
        ]
        return Project(
            id=f"project-{_slug(name)}-{identity}",
            name=name,
            settings=ProjectSettings(width=width, height=height, frame_rate=rate),
            sequences=[Sequence(id="sequence-main", name="Main", timeline=Timeline())],
            active_sequence_id="sequence-main",
            delivery_profiles=profiles,
        )

    @staticmethod
    def _validation_issues(project: Project, issues: list[MigrationIssue]) -> None:
        for item in validate_project(project).issues:
            issues.append(
                MigrationIssue(
                    code=f"canonical.{item.code}",
                    severity=(
                        MigrationSeverity.ERROR
                        if item.severity.value == "error"
                        else MigrationSeverity.WARNING
                    ),
                    disposition=MigrationDisposition.PRESERVED,
                    message=item.message,
                    canonical_path=item.path,
                )
            )

    @staticmethod
    def _issue(
        code: str,
        message: str,
        disposition: MigrationDisposition,
        event: _CMXEvent,
        *,
        details: dict[str, JsonValue] | None = None,
        severity: MigrationSeverity = MigrationSeverity.WARNING,
    ) -> MigrationIssue:
        return MigrationIssue(
            code=code,
            severity=severity,
            disposition=disposition,
            message=message,
            source_path=f"line:{event.line_number}",
            details=details or {},
        )
