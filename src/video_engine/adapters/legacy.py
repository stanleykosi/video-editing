"""Adapters for current existing-footage and faceless JSON timelines."""

from __future__ import annotations

import json
import math
import re
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError

from video_engine.captions.service import CaptionService
from video_engine.color.service import ColorService
from video_engine.config import EngineConfig
from video_engine.core.schema import (
    AudioClip,
    AudioRole,
    AudioTrack,
    Clip,
    DeliveryProfile,
    Effect,
    EffectKind,
    GraphicsTrack,
    LoudnessProfile,
    MediaReference,
    Project,
    ProjectSettings,
    Sequence,
    StillImageClip,
    Timeline,
    VideoTrack,
)
from video_engine.core.time import FrameRate, RationalTime, RoundingMode, TimeRange
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

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "legacy"


def _time(value: object) -> RationalTime:
    try:
        return RationalTime.from_fraction(Fraction(str(value)))
    except (ValueError, ZeroDivisionError) as exc:
        raise EngineError(
            ErrorCode.MIGRATION,
            "legacy time is invalid",
            context={"value": value},
        ) from exc


def _even_dimension(value: int) -> int:
    return max(2, value - value % 2)


def _resolution(payload: dict[str, Any]) -> tuple[int, int] | None:
    values: list[object] = [
        payload.get("resolution"),
        payload.get("output_resolution"),
        payload.get("target_resolution"),
    ]
    for container_name in ("render", "output", "export"):
        container = payload.get(container_name)
        if isinstance(container, dict):
            values.extend(
                [
                    container.get("resolution"),
                    container.get("output_resolution"),
                    container.get("target_resolution"),
                ]
            )
    for value in values:
        if isinstance(value, str):
            match = re.fullmatch(r"\s*(\d+)\s*[xX]\s*(\d+)\s*", value)
            if match:
                return _even_dimension(int(match.group(1))), _even_dimension(int(match.group(2)))
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return _even_dimension(int(value[0])), _even_dimension(int(value[1]))
        if isinstance(value, dict):
            width = value.get("width", value.get("w"))
            height = value.get("height", value.get("h"))
            if width is not None and height is not None:
                return _even_dimension(int(width)), _even_dimension(int(height))
    return None


def _legacy_containers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    containers = [payload]
    for name in ("render", "output", "export"):
        value = payload.get(name)
        if isinstance(value, dict):
            containers.append(value)
    return containers


def _legacy_setting(payload: dict[str, Any], *names: str) -> object | None:
    for container in _legacy_containers(payload):
        for name in names:
            if name in container and container[name] is not None:
                return cast(object, container[name])
    return None


class LegacyAdapterService:
    def __init__(self, project_root: Path, config: EngineConfig) -> None:
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)
        self.media_service = MediaService(self.project_root, self.config)
        self.caption_service = CaptionService(self.config)
        self.color_service = ColorService(self.project_root, self.config)

    def import_existing_edl(self, path: Path, *, name: str | None = None) -> MigrationResult:
        source_path, payload = self._json(path)
        issues: list[MigrationIssue] = []
        sources = payload.get("sources")
        ranges = payload.get("ranges")
        if not isinstance(sources, dict) or not isinstance(ranges, list) or not ranges:
            raise EngineError(
                ErrorCode.MIGRATION,
                "existing-footage EDL requires non-empty sources and ranges",
                context={"path": str(source_path)},
            )
        # The historical renderer always encoded 24 fps and 48 kHz, irrespective
        # of undocumented payload hints. Preserve the executable contract.
        frame_rate = FrameRate(numerator=24)
        fit = str(_legacy_setting(payload, "output_fit", "fit") or "cover").lower()
        if fit not in {"cover", "contain", "stretch"}:
            issues.append(
                self._issue(
                    "legacy.invalid_fit",
                    "unknown fit mode was replaced with cover",
                    MigrationDisposition.APPROXIMATED,
                    "output_fit",
                )
            )
            fit = "cover"
        media_by_alias: dict[str, MediaReference] = {}
        source_paths_by_alias: dict[str, Path] = {}
        for alias, raw_path in sources.items():
            resolved = self._resolve(source_path.parent, raw_path)
            reference = self._import_media(resolved)
            media_by_alias[str(alias)] = reference
            source_paths_by_alias[str(alias)] = resolved
        requested_resolution = _resolution(payload)
        width, height = requested_resolution or self._derived_resolution(media_by_alias, ranges)
        project = self._project(
            name or str(payload.get("title") or source_path.stem),
            width,
            height,
            frame_rate,
            48_000,
            identity=sha256_file(source_path)[:12],
            legacy_loudness=True,
        )
        project.extensions["legacy:existing_edl"] = payload
        for reference in media_by_alias.values():
            self._append_media(project, reference)
        if requested_resolution is None:
            issues.append(
                self._issue(
                    "legacy.resolution_derived",
                    "output resolution was derived using the legacy 1080p-class rule",
                    MigrationDisposition.EXECUTED,
                    "resolution",
                    canonical_path="settings",
                    details={"width": width, "height": height},
                    severity=MigrationSeverity.INFO,
                )
            )
        declared_fps = payload.get("fps")
        declared_sample_rate = payload.get("audio_sample_rate")
        if declared_fps is not None and Fraction(str(declared_fps)) != Fraction(24, 1):
            issues.append(
                self._issue(
                    "legacy.ignored_frame_rate_hint",
                    "the historical renderer ignored this frame-rate hint and emitted 24 fps",
                    MigrationDisposition.EXECUTED,
                    "fps",
                    canonical_path="settings.frame_rate",
                    details={"declared": declared_fps, "executed": "24/1"},
                    severity=MigrationSeverity.INFO,
                )
            )
        if declared_sample_rate is not None and int(declared_sample_rate) != 48_000:
            issues.append(
                self._issue(
                    "legacy.ignored_sample_rate_hint",
                    "the historical renderer ignored this sample-rate hint and emitted 48 kHz",
                    MigrationDisposition.EXECUTED,
                    "audio_sample_rate",
                    canonical_path="settings.audio_sample_rate",
                    details={"declared": declared_sample_rate, "executed": 48_000},
                    severity=MigrationSeverity.INFO,
                )
            )
        raw_grade = payload.get("grade")
        measured_auto_grade = str(raw_grade) == "auto"
        grade_effect = None if measured_auto_grade else self._grade_effect(raw_grade, issues)
        video_track = VideoTrack(id="video-main", name="Legacy ordered ranges")
        cursor = RationalTime.zero()
        for index, raw_range in enumerate(ranges):
            if not isinstance(raw_range, dict):
                raise EngineError(
                    ErrorCode.MIGRATION,
                    "legacy range must be an object",
                    context={"index": index},
                )
            alias = str(raw_range.get("source", ""))
            if alias not in media_by_alias:
                raise EngineError(
                    ErrorCode.MIGRATION,
                    "legacy range references an unknown source",
                    context={"index": index, "source": alias},
                )
            raw_start = _time(raw_range.get("start", 0))
            raw_end = _time(raw_range.get("end", raw_start.fraction))
            if raw_end <= raw_start:
                raise EngineError(
                    ErrorCode.MIGRATION,
                    "legacy range duration must be positive",
                    context={"index": index},
                )
            duration = self._frame_duration(
                raw_end - raw_start,
                frame_rate,
                issues,
                f"ranges[{index}]",
            )
            reference = media_by_alias[alias]
            if reference.available_range is not None:
                available = reference.available_range
                if raw_start < available.start or raw_start >= available.end:
                    raise EngineError(
                        ErrorCode.MIGRATION,
                        "legacy source range starts outside available media",
                        context={"index": index, "source": alias},
                    )
                maximum = available.end - raw_start
                if duration > maximum:
                    frames = frame_rate.time_to_frames(maximum, RoundingMode.FLOOR)
                    if frames < 1:
                        raise EngineError(
                            ErrorCode.MIGRATION,
                            "legacy source range has less than one available frame",
                            context={"index": index, "source": alias},
                        )
                    clamped = frame_rate.frames_to_time(frames)
                    issues.append(
                        self._issue(
                            "legacy.source_range_clamped",
                            "source range exceeded available media and was clamped to whole frames",
                            MigrationDisposition.IMPROVED,
                            f"ranges[{index}].end",
                            details={
                                "requested_duration": duration.model_dump(mode="json"),
                                "available_duration": maximum.model_dump(mode="json"),
                                "canonical_duration": clamped.model_dump(mode="json"),
                            },
                        )
                    )
                    duration = clamped
            focus_x, focus_y, corrected_zero = self._focus_pair(raw_range, payload)
            if corrected_zero:
                issues.append(
                    self._issue(
                        "legacy.focus_zero_corrected",
                        "an authored zero focus coordinate is now honored instead of "
                        "falling back to center",
                        MigrationDisposition.IMPROVED,
                        f"ranges[{index}]",
                        canonical_path=f"sequences[0].timeline.tracks[0].items[{index}].effects",
                    )
                )
            effects = [
                Effect(
                    id=f"range-{index + 1}-reframe",
                    kind=EffectKind.REFRAME,
                    parameters={
                        "fit": fit,
                        "focus_x": focus_x,
                        "focus_y": focus_y,
                    },
                )
            ]
            crop = raw_range.get("crop")
            if isinstance(crop, dict):
                width_value = crop.get("w", crop.get("width"))
                height_value = crop.get("h", crop.get("height"))
                if width_value is not None and height_value is not None:
                    effects.insert(
                        0,
                        Effect(
                            id=f"range-{index + 1}-crop",
                            kind=EffectKind.CROP,
                            parameters={
                                "width": round(float(width_value)),
                                "height": round(float(height_value)),
                                "x": round(float(crop.get("x", crop.get("left")) or 0)),
                                "y": round(float(crop.get("y", crop.get("top")) or 0)),
                                "space": "source",
                            },
                        ),
                    )
            if grade_effect is not None:
                effects.append(grade_effect.model_copy(update={"id": f"range-{index + 1}-grade"}))
            elif measured_auto_grade:
                measured = self.color_service.auto_grade(
                    source_paths_by_alias[alias],
                    source_range=TimeRange(start=raw_start, duration=duration),
                    effect_id=f"range-{index + 1}-grade",
                )
                effects.append(
                    measured.effect.model_copy(
                        update={
                            "extensions": {
                                **measured.effect.extensions,
                                "legacy:grade": "auto",
                            }
                        }
                    )
                )
                semantic_measurements = measured.measurements.model_copy(
                    update={"cache_hit": False}
                )
                issues.append(
                    self._issue(
                        "legacy.auto_grade_measured",
                        "legacy auto grade was measured for this exact source range",
                        MigrationDisposition.IMPROVED,
                        f"ranges[{index}]",
                        canonical_path=(f"sequences[0].timeline.tracks[0].items[{index}].effects"),
                        details={
                            "policy": measured.policy.model_dump(mode="json"),
                            "parameters": measured.grade.model_dump(mode="json"),
                            "measurements": semantic_measurements.model_dump(mode="json"),
                            "improvement": (
                                "storage pixel depth replaces legacy effective-signal-bit "
                                "normalization; failed analysis now blocks instead of "
                                "inventing neutral measurements"
                            ),
                        },
                        severity=MigrationSeverity.WARNING,
                    )
                )
            video_track.items.append(
                Clip(
                    id=f"range-{index + 1}",
                    name=str(raw_range.get("note") or raw_range.get("beat") or alias),
                    media_reference_id=media_by_alias[alias].id,
                    timeline_range=TimeRange(start=cursor, duration=duration),
                    source_range=TimeRange(start=raw_start, duration=duration),
                    source_audio_enabled=any(
                        stream.codec_type == "audio" for stream in media_by_alias[alias].streams
                    ),
                    effects=effects,
                    extensions={"legacy:range": raw_range},
                )
            )
            cursor = cursor + duration
        project.sequence().timeline.tracks.append(video_track)
        self._existing_overlays(project, payload, source_path.parent, frame_rate, cursor, issues)
        self._existing_sfx(project, payload, source_path.parent, cursor, issues)
        self._existing_captions(project, payload, source_path.parent, cursor, issues)
        declared = payload.get("total_duration_s")
        if declared is not None and _time(declared) != cursor:
            issues.append(
                self._issue(
                    "legacy.duration_corrected",
                    "declared duration disagreed with frame-quantized ordered ranges",
                    MigrationDisposition.IMPROVED,
                    "total_duration_s",
                    canonical_path="sequences[0].timeline.duration",
                    details={
                        "declared": declared,
                        "canonical": cursor.model_dump(mode="json"),
                    },
                )
            )
        return self._result(
            AdapterKind.LEGACY_EDL,
            source_path,
            payload,
            project,
            issues,
            source_schema=f"video-use-existing-edl/v{payload.get('version', 1)}",
        )

    def _existing_overlays(
        self,
        project: Project,
        payload: dict[str, Any],
        base: Path,
        rate: FrameRate,
        timeline_duration: RationalTime,
        issues: list[MigrationIssue],
    ) -> None:
        overlays = payload.get("overlays", [])
        if not isinstance(overlays, list) or not overlays:
            return
        for index, overlay in enumerate(overlays):
            if not isinstance(overlay, dict) or not overlay.get("file"):
                issues.append(
                    self._issue(
                        "legacy.invalid_overlay_preserved",
                        "malformed overlay entry could not be executed and remains in "
                        "extension metadata",
                        MigrationDisposition.PRESERVED,
                        f"overlays[{index}]",
                    )
                )
                continue
            reference = self._import_media(self._resolve(base, overlay["file"]))
            self._append_media(project, reference)
            start = self._frame_time(
                _time(overlay.get("start_in_output", 0)),
                rate,
                issues,
                f"overlays[{index}].start_in_output",
            )
            duration_value = overlay.get("duration")
            duration = (
                self._frame_duration(
                    _time(duration_value), rate, issues, f"overlays[{index}].duration"
                )
                if duration_value is not None
                else (
                    reference.available_range.duration
                    if reference.available_range is not None
                    else rate.frame_duration
                )
            )
            visible = TimeRange(start=start, duration=duration).intersection(
                TimeRange(start=RationalTime.zero(), duration=timeline_duration)
            )
            if visible is None:
                issues.append(
                    self._issue(
                        "legacy.auxiliary_outside_program",
                        "overlay outside the base program duration was preserved only in metadata",
                        MigrationDisposition.PRESERVED,
                        f"overlays[{index}]",
                    )
                )
                continue
            if reference.available_range is not None:
                visible = TimeRange(
                    start=visible.start,
                    duration=min(visible.duration, reference.available_range.duration),
                )
            item = (
                StillImageClip(
                    id=f"overlay-{index + 1}",
                    media_reference_id=reference.id,
                    timeline_range=visible,
                    extensions={"legacy:overlay": overlay},
                )
                if Path(reference.uri).suffix.lower() in IMAGE_SUFFIXES
                else Clip(
                    id=f"overlay-{index + 1}",
                    media_reference_id=reference.id,
                    timeline_range=visible,
                    source_range=TimeRange(start=RationalTime.zero(), duration=visible.duration),
                    source_audio_enabled=False,
                    extensions={"legacy:overlay": overlay},
                )
            )
            project.sequence().timeline.tracks.append(
                GraphicsTrack(
                    id=f"graphics-overlay-{index + 1}",
                    name=f"Legacy overlay {index + 1}",
                    items=[item],
                )
            )

    def _existing_sfx(
        self,
        project: Project,
        payload: dict[str, Any],
        base: Path,
        timeline_duration: RationalTime,
        issues: list[MigrationIssue],
    ) -> None:
        events = payload.get("sound_effects") or payload.get("sfx") or []
        if not isinstance(events, list) or not events:
            return
        sample_rate = project.settings.audio_sample_rate
        for index, event in enumerate(events):
            if not isinstance(event, dict) or not event.get("file"):
                issues.append(
                    self._issue(
                        "legacy.invalid_sfx_preserved",
                        "malformed SFX entry could not be executed and remains in "
                        "extension metadata",
                        MigrationDisposition.PRESERVED,
                        f"sound_effects[{index}]",
                    )
                )
                continue
            reference = self._import_media(self._resolve(base, event["file"]))
            self._append_media(project, reference)
            start = _time(event.get("start_in_output", event.get("start", 0))).rescaled_to(
                sample_rate, RoundingMode.NEAREST
            )
            duration = (
                _time(event["duration"]).rescaled_to(sample_rate, RoundingMode.NEAREST)
                if event.get("duration") is not None
                else (
                    reference.available_range.duration
                    if reference.available_range is not None
                    else RationalTime(value=1, timescale=sample_rate)
                )
            )
            visible = TimeRange(start=start, duration=duration).intersection(
                TimeRange(start=RationalTime.zero(), duration=timeline_duration)
            )
            if visible is None:
                issues.append(
                    self._issue(
                        "legacy.auxiliary_outside_program",
                        "SFX outside the base program duration was preserved only in metadata",
                        MigrationDisposition.PRESERVED,
                        f"sound_effects[{index}]",
                    )
                )
                continue
            if reference.available_range is not None:
                visible = TimeRange(
                    start=visible.start,
                    duration=min(visible.duration, reference.available_range.duration),
                )
            gain_value = event.get("gain", event.get("volume", 1))
            gain = float(cast(str | int | float, gain_value))
            effects = (
                [
                    Effect(
                        id=f"sfx-{index + 1}-gain",
                        kind=EffectKind.GAIN,
                        parameters={"db": 20 * math.log10(max(gain, 1e-9))},
                    )
                ]
                if gain != 1
                else []
            )
            project.sequence().timeline.tracks.append(
                AudioTrack(
                    id=f"audio-sfx-{index + 1}",
                    name=f"Legacy SFX {index + 1}",
                    role=AudioRole.SFX,
                    items=[
                        AudioClip(
                            id=f"sfx-{index + 1}",
                            media_reference_id=reference.id,
                            timeline_range=visible,
                            source_range=TimeRange(
                                start=RationalTime.zero(), duration=visible.duration
                            ),
                            role=AudioRole.SFX,
                            effects=effects,
                            extensions={"legacy:sfx": event},
                        )
                    ],
                )
            )

    def _existing_captions(
        self,
        project: Project,
        payload: dict[str, Any],
        base: Path,
        timeline_duration: RationalTime,
        issues: list[MigrationIssue],
    ) -> None:
        value = payload.get("subtitles")
        if not value:
            return
        path = self._resolve(base, value)
        if not path.is_file():
            issues.append(
                self._issue(
                    "legacy.subtitle_missing",
                    "missing optional subtitle sidecar was skipped as the historical renderer did",
                    MigrationDisposition.PRESERVED,
                    "subtitles",
                    details={"path": str(path)},
                )
            )
            return
        imported = self.caption_service.import_file(path, track_id="captions")
        project.caption_styles = list(imported.styles)
        program = TimeRange(start=RationalTime.zero(), duration=timeline_duration)
        imported.track.items = [
            cue.model_copy(
                update={
                    "timeline_range": cue.timeline_range.intersection(program),
                }
            )
            for cue in imported.track.items
            if cue.timeline_range.intersection(program) is not None
        ]
        if imported.track.items:
            project.sequence().timeline.tracks.append(imported.track)
        for loss in imported.losses:
            issues.append(
                self._issue(
                    "caption.import_loss",
                    loss.disposition,
                    MigrationDisposition.PRESERVED,
                    f"subtitles:{loss.item_id or ''}",
                    details={"feature": loss.feature},
                )
            )

    def _project(
        self,
        name: str,
        width: int,
        height: int,
        frame_rate: FrameRate,
        sample_rate: int,
        identity: str,
        *,
        legacy_loudness: bool,
    ) -> Project:
        project_id = f"project-{_slug(name)}-{identity}"
        loudness = (
            LoudnessProfile(
                integrated_lufs=-14,
                true_peak_dbtp=-1,
                loudness_range_lu=11,
            )
            if legacy_loudness
            else None
        )
        return Project(
            id=project_id,
            name=name,
            settings=ProjectSettings(
                width=width,
                height=height,
                frame_rate=frame_rate,
                audio_sample_rate=sample_rate,
                audio_boundary_fade=RationalTime(value=30, timescale=1000),
            ),
            sequences=[Sequence(id="sequence-main", name="Main", timeline=Timeline())],
            active_sequence_id="sequence-main",
            delivery_profiles=[
                DeliveryProfile(
                    id="preview",
                    name="Preview",
                    width=width,
                    height=height,
                    frame_rate=frame_rate,
                    crf=22,
                    preset="veryfast",
                    audio_sample_rate=sample_rate,
                    loudness=loudness,
                ),
                DeliveryProfile(
                    id="final",
                    name="Final",
                    width=width,
                    height=height,
                    frame_rate=frame_rate,
                    crf=18,
                    preset="medium",
                    audio_sample_rate=sample_rate,
                    loudness=loudness,
                ),
            ],
        )

    def _json(self, path: Path) -> tuple[Path, dict[str, Any]]:
        source = path.resolve()
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EngineError(
                ErrorCode.MIGRATION,
                "failed to read legacy JSON",
                context={"path": str(source), "detail": str(exc)},
            ) from exc
        if not isinstance(payload, dict):
            raise EngineError(ErrorCode.MIGRATION, "legacy JSON root must be an object")
        return source, payload

    def _import_media(self, path: Path) -> MediaReference:
        try:
            return self.media_service.to_media_reference(
                self.media_service.import_media(path, deep_vfr=False)
            )
        except (EngineError, ValidationError) as exc:
            raise EngineError(
                ErrorCode.MIGRATION,
                "legacy media could not be imported",
                context={"path": str(path), "detail": str(exc)},
            ) from exc

    @staticmethod
    def _append_media(project: Project, reference: MediaReference) -> None:
        if not any(media.id == reference.id for media in project.media):
            project.media.append(reference)

    @staticmethod
    def _resolve(base: Path, value: object) -> Path:
        path = Path(str(value))
        return (path if path.is_absolute() else base / path).resolve()

    @staticmethod
    def _focus_value(item: dict[str, Any], root: dict[str, Any], axis: str) -> object | None:
        names = (f"focus_{axis}", f"crop_focus_{axis}", f"output_focus_{axis}")
        raw_reframe = item.get("reframe")
        sources: list[dict[str, Any]] = [item]
        if isinstance(raw_reframe, dict):
            sources.append(raw_reframe)
        for container in _legacy_containers(root):
            nested = container.get("reframe")
            if isinstance(nested, dict):
                sources.append(nested)
            sources.append(container)
        for source in sources:
            for name in names:
                if name in source and source[name] is not None:
                    return cast(object, source[name])
        return None

    @classmethod
    def _focus_pair(cls, item: dict[str, Any], root: dict[str, Any]) -> tuple[float, float, bool]:
        raw_x = cls._focus_value(item, root, "x")
        raw_y = cls._focus_value(item, root, "y")

        def clamp(value: object | None) -> float:
            if value is None:
                return 0.5
            try:
                return max(0.0, min(1.0, float(cast(str | int | float, value))))
            except (TypeError, ValueError):
                return 0.5

        def is_zero(value: object | None) -> bool:
            try:
                return value is not None and float(cast(str | int | float, value)) == 0
            except (TypeError, ValueError):
                return False

        corrected_zero = any(is_zero(value) for value in (raw_x, raw_y))
        return clamp(raw_x), clamp(raw_y), corrected_zero

    @staticmethod
    def _frame_time(
        value: RationalTime,
        rate: FrameRate,
        issues: list[MigrationIssue],
        source_path: str,
    ) -> RationalTime:
        frame = rate.time_to_frames(value, RoundingMode.NEAREST)
        converted = rate.frames_to_time(frame)
        if converted != value:
            issues.append(
                LegacyAdapterService._issue(
                    "legacy.time_quantized",
                    "legacy floating-point boundary was quantized to the nearest frame",
                    MigrationDisposition.APPROXIMATED,
                    source_path,
                    details={
                        "source": value.model_dump(mode="json"),
                        "canonical": converted.model_dump(mode="json"),
                    },
                )
            )
        return converted

    @staticmethod
    def _frame_duration(
        value: RationalTime,
        rate: FrameRate,
        issues: list[MigrationIssue],
        source_path: str,
    ) -> RationalTime:
        converted = LegacyAdapterService._frame_time(value, rate, issues, source_path)
        if converted.value > 0:
            return converted
        issues.append(
            LegacyAdapterService._issue(
                "legacy.duration_clamped_to_frame",
                "positive sub-frame duration was clamped to one output frame",
                MigrationDisposition.IMPROVED,
                source_path,
                details={
                    "source": value.model_dump(mode="json"),
                    "canonical": rate.frame_duration.model_dump(mode="json"),
                },
            )
        )
        return rate.frame_duration

    @staticmethod
    def _derived_resolution(
        media_by_alias: dict[str, MediaReference], ranges: list[Any]
    ) -> tuple[int, int]:
        aliases = [
            str(item.get("source"))
            for item in ranges
            if isinstance(item, dict) and str(item.get("source")) in media_by_alias
        ] or list(media_by_alias)
        dimensions = [
            (stream.width, stream.height)
            for alias in aliases
            for stream in media_by_alias[alias].streams
            if stream.codec_type == "video"
            and stream.width is not None
            and stream.height is not None
        ]
        if not dimensions:
            return 1920, 1080
        width, height = max(
            dimensions,
            key=lambda value: value[0] * value[1],
        )
        short_edge = min(width, height)
        scale = max(1.0, 1080 / short_edge)
        return _even_dimension(round(width * scale)), _even_dimension(round(height * scale))

    @staticmethod
    def _grade_effect(value: object, issues: list[MigrationIssue]) -> Effect | None:
        if value in (None, "", "none"):
            return None
        grade = str(value)
        parameters: dict[str, Any]
        disposition = MigrationDisposition.EXECUTED
        message = "legacy grade preset was translated to typed canonical controls"
        if grade == "subtle":
            parameters = {"contrast": 1.03, "saturation": 0.98}
        elif grade == "neutral_punch":
            parameters = {"contrast": 1.06, "saturation": 1.0}
            disposition = MigrationDisposition.APPROXIMATED
            message = (
                "neutral_punch was translated to typed controls; its custom curve is preserved"
            )
        elif grade == "warm_cinematic":
            parameters = {
                "exposure_stops": -0.03,
                "temperature": 0.08,
                "contrast": 1.12,
                "saturation": 0.88,
                "highlights": -0.05,
                "shadows": -0.03,
            }
            disposition = MigrationDisposition.APPROXIMATED
            message = (
                "warm_cinematic was translated to typed controls; split-tone and curve "
                "details are preserved"
            )
        else:
            issues.append(
                LegacyAdapterService._issue(
                    "legacy.raw_grade_preserved",
                    "raw or unknown backend grade syntax cannot become a canonical effect",
                    MigrationDisposition.PRESERVED,
                    "grade",
                    details={"value": grade},
                )
            )
            return None
        issues.append(
            LegacyAdapterService._issue(
                "legacy.grade_migrated",
                message,
                disposition,
                "grade",
                canonical_path="sequences[0].timeline.tracks[0].items[*].effects",
                details={"value": grade, "parameters": parameters},
                severity=(
                    MigrationSeverity.INFO
                    if disposition is MigrationDisposition.EXECUTED
                    else MigrationSeverity.WARNING
                ),
            )
        )
        return Effect(
            id="legacy-grade",
            kind=EffectKind.COLOR_GRADE,
            parameters=parameters,
            extensions={"legacy:grade": grade},
        )

    @staticmethod
    def _issue(
        code: str,
        message: str,
        disposition: MigrationDisposition,
        source_path: str,
        *,
        canonical_path: str | None = None,
        details: dict[str, Any] | None = None,
        severity: MigrationSeverity = MigrationSeverity.WARNING,
    ) -> MigrationIssue:
        return MigrationIssue(
            code=code,
            severity=severity,
            disposition=disposition,
            message=message,
            source_path=source_path,
            canonical_path=canonical_path,
            details=details or {},
        )

    @staticmethod
    def _result(
        adapter: AdapterKind,
        source_path: Path,
        payload: dict[str, Any],
        project: Project,
        issues: list[MigrationIssue],
        *,
        source_schema: str,
    ) -> MigrationResult:
        validation = validate_project(project)
        for item in validation.issues:
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
        report = MigrationReport(
            adapter=adapter,
            source_path=source_path,
            source_sha256=sha256_file(source_path),
            source_schema=source_schema,
            project_id=project.id,
            project_schema_version=project.schema_version,
            issues=tuple(issues),
            preserved_metadata={"legacy_root_keys": sorted(payload)},
        )
        return MigrationResult(project=project, report=report)
