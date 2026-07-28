"""Optional OpenTimelineIO bridge with canonical loss reporting."""

from __future__ import annotations

import hashlib
import importlib
import re
from fractions import Fraction
from pathlib import Path
from typing import Any

from video_engine.config import EngineConfig
from video_engine.core.schema import (
    AudioClip,
    AudioRole,
    AudioTrack,
    Clip,
    DeliveryProfile,
    Gap,
    JsonValue,
    Marker,
    MediaReference,
    Project,
    ProjectSettings,
    Sequence,
    Timeline,
    Transition,
    TransitionKind,
    VideoTrack,
)
from video_engine.core.time import FrameRate, RationalTime, TimeRange
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


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "otio"


def _time(value: Any) -> RationalTime:
    try:
        fraction = Fraction(str(value.value)) / Fraction(str(value.rate))
    except (AttributeError, ValueError, ZeroDivisionError) as exc:
        raise EngineError(
            ErrorCode.MIGRATION,
            "OTIO rational time is invalid",
            context={"value": repr(value)},
        ) from exc
    return RationalTime.from_fraction(fraction)


class OTIOAdapterService:
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
        width: int = 1920,
        height: int = 1080,
    ) -> MigrationResult:
        otio = self._module()
        source = path.resolve()
        if not source.is_file():
            raise EngineError(
                ErrorCode.MIGRATION,
                "OTIO source does not exist",
                context={"path": str(source)},
            )
        try:
            timeline = otio.adapters.read_from_file(str(source))
        except Exception as exc:
            raise EngineError(
                ErrorCode.MIGRATION,
                "OpenTimelineIO could not read the source",
                context={"path": str(source), "detail": str(exc)},
            ) from exc
        rate = frame_rate or self._infer_rate(timeline)
        digest = sha256_file(source)
        project_name = name or str(getattr(timeline, "name", "") or source.stem)
        project = self._project(project_name, digest[:12], width, height, rate)
        issues: list[MigrationIssue] = []
        references: dict[str, MediaReference] = {}
        resolved: list[str] = []
        offline: list[str] = []
        tracks = list(getattr(timeline, "tracks", []))
        for track_index, source_track in enumerate(tracks):
            kind = str(getattr(source_track, "kind", "Video")).lower()
            if "audio" in kind:
                track: VideoTrack | AudioTrack = AudioTrack(
                    id=f"otio-audio-{track_index + 1}",
                    name=str(getattr(source_track, "name", "") or "OTIO Audio"),
                    role=AudioRole.SOURCE,
                )
            else:
                track = VideoTrack(
                    id=f"otio-video-{track_index + 1}",
                    name=str(getattr(source_track, "name", "") or "OTIO Video"),
                )
            cursor = RationalTime.zero()
            pending_transition: tuple[Any, str | None] | None = None
            previous_id: str | None = None
            for child_index, child in enumerate(source_track):
                schema_name = str(child.schema_name())
                item_path = f"tracks[{track_index}][{child_index}]"
                if schema_name == "Transition":
                    pending_transition = (child, previous_id)
                    continue
                source_range = self._available_range(child)
                duration = source_range.duration
                item_id = f"otio-{track_index + 1}-{child_index + 1}"
                timeline_range = TimeRange(start=cursor, duration=duration)
                if schema_name == "Gap":
                    gap_item = Gap(
                        id=item_id,
                        name=str(getattr(child, "name", "") or "Gap"),
                        timeline_range=timeline_range,
                        extensions={"otio:metadata": self._metadata(child)},
                    )
                    track.items.append(gap_item)
                elif schema_name == "Clip":
                    reference = self._reference(
                        child,
                        source.parent,
                        references,
                        resolved,
                        offline,
                        issues,
                        item_path,
                    )
                    if isinstance(track, VideoTrack):
                        video_item = Clip(
                            id=item_id,
                            name=str(getattr(child, "name", "") or reference.id),
                            media_reference_id=reference.id,
                            timeline_range=timeline_range,
                            source_range=source_range,
                            source_audio_enabled=False,
                            extensions={"otio:metadata": self._metadata(child)},
                        )
                        track.items.append(video_item)
                    else:
                        audio_item = AudioClip(
                            id=item_id,
                            name=str(getattr(child, "name", "") or reference.id),
                            media_reference_id=reference.id,
                            timeline_range=timeline_range,
                            source_range=source_range,
                            role=AudioRole.SOURCE,
                            extensions={"otio:metadata": self._metadata(child)},
                        )
                        track.items.append(audio_item)
                    self._unsupported_clip_features(child, issues, item_path)
                else:
                    issues.append(
                        self._issue(
                            "otio.unsupported_item_preserved",
                            "unsupported OTIO composable was preserved in the report",
                            MigrationDisposition.PRESERVED,
                            item_path,
                            details={
                                "schema_name": schema_name,
                                "metadata": self._metadata(child),
                            },
                        )
                    )
                    cursor = cursor + duration
                    continue
                if pending_transition is not None:
                    transition_source, from_id = pending_transition
                    if from_id is not None:
                        transition_duration = _time(transition_source.in_offset) + _time(
                            transition_source.out_offset
                        )
                        track.transitions.append(
                            Transition(
                                id=f"otio-transition-{track_index + 1}-{child_index + 1}",
                                from_item_id=from_id,
                                to_item_id=item_id,
                                duration=transition_duration,
                                kind=TransitionKind.DISSOLVE,
                                extensions={
                                    "otio:transition_type": str(
                                        getattr(transition_source, "transition_type", "")
                                    ),
                                    "otio:metadata": self._metadata(transition_source),
                                },
                            )
                        )
                        issues.append(
                            self._issue(
                                "otio.transition_timing_approximated",
                                "OTIO overlap transition was placed at the canonical cut boundary",
                                MigrationDisposition.APPROXIMATED,
                                item_path,
                            )
                        )
                    pending_transition = None
                self._markers(project, child, cursor, item_id)
                previous_id = item_id
                cursor = cursor + duration
            project.sequence().timeline.tracks.append(track)
        project.media = list(references.values())
        project.extensions["otio:metadata"] = self._metadata(timeline)
        self._validation_issues(project, issues)
        return MigrationResult(
            project=project,
            report=MigrationReport(
                adapter=AdapterKind.OTIO,
                source_path=source,
                source_sha256=digest,
                source_schema=f"opentimelineio/{getattr(otio, '__version__', 'unknown')}",
                project_id=project.id,
                project_schema_version=project.schema_version,
                issues=tuple(issues),
                preserved_metadata={
                    "timeline_name": getattr(timeline, "name", ""),
                    "track_count": len(tracks),
                },
                resolved_assets=tuple(sorted(resolved)),
                offline_assets=tuple(sorted(offline)),
            ),
        )

    @staticmethod
    def _module() -> Any:
        try:
            return importlib.import_module("opentimelineio")
        except ModuleNotFoundError as exc:
            raise EngineError(
                ErrorCode.DEPENDENCY_MISSING,
                "OpenTimelineIO support requires the interchange dependency group",
                context={"install": "uv sync --extra interchange"},
            ) from exc

    @staticmethod
    def _infer_rate(timeline: Any) -> FrameRate:
        rates: set[Fraction] = set()
        for track in getattr(timeline, "tracks", []):
            for child in track:
                try:
                    value = Fraction(str(child.trimmed_range().duration.rate))
                except (AttributeError, ValueError, ZeroDivisionError):
                    continue
                if value > 0:
                    rates.add(value)
        if len(rates) != 1:
            raise EngineError(
                ErrorCode.MIGRATION,
                "OTIO import requires an explicit frame rate when item rates differ or are absent",
            )
        rate = rates.pop()
        return FrameRate(numerator=rate.numerator, denominator=rate.denominator)

    @staticmethod
    def _available_range(item: Any) -> TimeRange:
        try:
            source = item.trimmed_range()
            start = _time(source.start_time)
            duration = _time(source.duration)
        except Exception as exc:
            raise EngineError(
                ErrorCode.MIGRATION,
                "OTIO item does not expose a valid trimmed range",
                context={"schema": str(item.schema_name()), "detail": str(exc)},
            ) from exc
        if duration.value <= 0:
            raise EngineError(ErrorCode.MIGRATION, "OTIO item duration must be positive")
        return TimeRange(start=start, duration=duration)

    def _reference(
        self,
        clip: Any,
        base: Path,
        references: dict[str, MediaReference],
        resolved: list[str],
        offline: list[str],
        issues: list[MigrationIssue],
        source_path: str,
    ) -> MediaReference:
        media_reference = getattr(clip, "media_reference", None)
        target_url = str(getattr(media_reference, "target_url", "") or "")
        candidate = self._target_path(target_url, base)
        identity = target_url or str(getattr(clip, "name", "") or source_path)
        key = hashlib.sha256(identity.encode()).hexdigest()[:16]
        if key in references:
            return references[key]
        if candidate is not None and candidate.is_file():
            record = self.media_service.import_media(candidate, deep_vfr=False)
            reference = self.media_service.to_media_reference(record)
            reference.extensions["otio:target_url"] = target_url
            references[key] = reference
            resolved.append(str(candidate))
            return reference
        offline_uri = str(candidate) if candidate is not None else target_url or f"offline://{key}"
        reference = MediaReference(
            id=f"offline-{key}",
            uri=offline_uri,
            offline=True,
            extensions={
                "otio:target_url": target_url,
                "otio:metadata": self._metadata(media_reference),
            },
        )
        references[key] = reference
        offline.append(offline_uri)
        issues.append(
            self._issue(
                "otio.media_offline",
                "OTIO media reference is unresolved and remains relinkable",
                MigrationDisposition.PRESERVED,
                source_path,
                details={"uri": offline_uri},
            )
        )
        return reference

    @staticmethod
    def _target_path(target_url: str, base: Path) -> Path | None:
        if not target_url:
            return None
        if target_url.startswith("file://"):
            return Path(target_url[7:]).resolve()
        if "://" in target_url:
            return None
        path = Path(target_url)
        return (path if path.is_absolute() else base / path).resolve()

    @staticmethod
    def _metadata(value: Any) -> dict[str, JsonValue]:
        metadata = getattr(value, "metadata", {})
        return metadata if isinstance(metadata, dict) else {"value": str(metadata)}

    @staticmethod
    def _unsupported_clip_features(
        clip: Any,
        issues: list[MigrationIssue],
        source_path: str,
    ) -> None:
        effects = list(getattr(clip, "effects", []))
        if effects:
            issues.append(
                OTIOAdapterService._issue(
                    "otio.effects_preserved",
                    "OTIO effects were preserved in metadata without backend-specific execution",
                    MigrationDisposition.PRESERVED,
                    source_path,
                    details={"effect_count": len(effects)},
                )
            )

    @staticmethod
    def _markers(project: Project, item: Any, start: RationalTime, item_id: str) -> None:
        for index, marker in enumerate(getattr(item, "markers", [])):
            marked_range = getattr(marker, "marked_range", None)
            relative = (
                _time(marked_range.start_time) if marked_range is not None else RationalTime.zero()
            )
            project.sequence().timeline.markers.append(
                Marker(
                    id=f"otio-marker-{item_id}-{index + 1}",
                    time=start + relative,
                    name=str(getattr(marker, "name", "") or "Marker"),
                    extensions={"otio:metadata": OTIOAdapterService._metadata(marker)},
                )
            )

    @staticmethod
    def _project(
        name: str,
        identity: str,
        width: int,
        height: int,
        rate: FrameRate,
    ) -> Project:
        return Project(
            id=f"project-{_slug(name)}-{identity}",
            name=name,
            settings=ProjectSettings(width=width, height=height, frame_rate=rate),
            sequences=[Sequence(id="sequence-main", name="Main", timeline=Timeline())],
            active_sequence_id="sequence-main",
            delivery_profiles=[
                DeliveryProfile(
                    id="preview",
                    name="Preview",
                    width=width,
                    height=height,
                    frame_rate=rate,
                    crf=22,
                    preset="veryfast",
                ),
                DeliveryProfile(
                    id="final",
                    name="Final",
                    width=width,
                    height=height,
                    frame_rate=rate,
                    crf=18,
                    preset="medium",
                ),
            ],
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
        source_path: str,
        *,
        details: dict[str, JsonValue] | None = None,
    ) -> MigrationIssue:
        return MigrationIssue(
            code=code,
            severity=MigrationSeverity.WARNING,
            disposition=disposition,
            message=message,
            source_path=source_path,
            details=details or {},
        )
