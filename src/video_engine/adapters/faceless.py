"""Migration of the historical from-scratch timeline into canonical tracks."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import ValidationError

from video_engine.audio import (
    SynthEffectEvent,
    SynthEffectKind,
    SynthesisRequest,
    synthesize_effects,
)
from video_engine.captions.service import CaptionService
from video_engine.config import EngineConfig
from video_engine.core.schema import (
    AudioClip,
    AudioRole,
    AudioTrack,
    CaptionCue,
    CaptionStyle,
    CaptionTrack,
    Clip,
    DeliveryProfile,
    Effect,
    EffectKind,
    Gap,
    GeneratorClip,
    GraphicsTrack,
    Keyframe,
    Marker,
    MediaReference,
    Project,
    ProjectSettings,
    Sequence,
    StillImageClip,
    Timeline,
    Transition,
    TransitionKind,
    VideoTrack,
)
from video_engine.core.time import (
    AudioSampleTime,
    FrameRate,
    RationalTime,
    RoundingMode,
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

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}
LEGACY_SFX_SAMPLE_RATE = 48_000


@dataclass(frozen=True, slots=True)
class _LegacySFX:
    beat_id: str
    time: float
    kind: SynthEffectKind
    level: str
    description: str


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "faceless"


def _time(value: object) -> RationalTime:
    try:
        return RationalTime.from_fraction(Fraction(str(value)))
    except (ValueError, ZeroDivisionError) as exc:
        raise EngineError(
            ErrorCode.MIGRATION,
            "faceless timeline contains an invalid time",
            context={"value": value},
        ) from exc


def _dict(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


class FacelessAdapterService:
    """Materialize every legacy execution decision as canonical timeline data."""

    def __init__(self, project_root: Path, config: EngineConfig) -> None:
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)
        self.media_service = MediaService(self.project_root, self.config)
        self.caption_service = CaptionService(self.config)

    def import_project(
        self,
        path: Path,
        *,
        name: str | None = None,
        voiceover: Path | None = None,
        captions: Path | None = None,
        rich_captions: Path | None = None,
    ) -> MigrationResult:
        source_path = self._timeline_path(path)
        payload = self._read_json(source_path)
        project_dir = source_path.parent
        issues: list[MigrationIssue] = []
        sidecars: dict[str, str] = {}
        directive_path = project_dir / "creative_directive.json"
        manifest_path = project_dir / "asset_manifest.json"
        directive = self._optional_json(directive_path, sidecars, issues)
        manifest = self._optional_json(manifest_path, sidecars, issues)
        project_data = _dict(payload.get("project"))
        width, height = self._resolution(project_data)
        frame_rate = self._frame_rate(project_data.get("fps", 30))
        sample_rate = int(project_data.get("audio_sample_rate", 48_000))
        if sample_rate <= 0:
            raise EngineError(ErrorCode.MIGRATION, "audio sample rate must be positive")
        source_digest = sha256_file(source_path)
        project_name = name or str(project_data.get("title") or source_path.parent.name)
        project = self._project(
            project_name,
            source_digest[:12],
            width,
            height,
            frame_rate,
            sample_rate,
        )
        project.extensions["legacy:faceless"] = payload
        project.extensions["legacy:creative_directive"] = directive
        project.extensions["legacy:asset_manifest"] = manifest
        beats = _list(payload.get("beats"))
        if not beats:
            raise EngineError(ErrorCode.MIGRATION, "faceless timeline requires at least one beat")
        manifest_lookup = self._manifest_lookup(manifest)
        stock_mode = bool(
            project_data.get("stock_montage_only")
            or project_data.get("transition_style") == "stock_crossfade"
        )
        transition_duration = self._transition_duration(project_data, frame_rate, stock_mode)
        base_track, beat_records, resolved_assets = self._base_track(
            project,
            beats,
            manifest_lookup,
            project_dir,
            frame_rate,
            transition_duration,
            issues,
        )
        project.sequence().timeline.tracks.append(base_track)
        program_duration = base_track.items[-1].timeline_range.end
        self._add_transitions(
            base_track,
            transition_duration,
            project_data,
            issues,
        )
        colors = self._colors(directive)
        self._graphics_tracks(
            project,
            beat_records,
            program_duration,
            frame_rate,
            colors,
            stock_mode,
            issues,
        )
        rich_path = rich_captions or project_dir / "captions" / "captions.json"
        caption_path = captions or self._caption_sidecar(project_dir)
        if rich_path.is_file():
            rich_payload = self._read_json(rich_path)
            sidecars[str(rich_path.resolve())] = sha256_file(rich_path.resolve())
            self._rich_captions(
                project,
                rich_payload,
                beat_records,
                program_duration,
                frame_rate,
                colors,
                stock_mode,
                issues,
            )
        elif caption_path is not None and caption_path.is_file():
            sidecars[str(caption_path.resolve())] = sha256_file(caption_path.resolve())
            self._sidecar_captions(project, caption_path, program_duration, issues)
        voiceover_path = self._voiceover_path(project_dir, payload, voiceover)
        has_voiceover = False
        if voiceover_path is not None and voiceover_path.is_file():
            sidecars[str(voiceover_path.resolve())] = sha256_file(voiceover_path.resolve())
            has_voiceover = self._voiceover(project, voiceover_path, program_duration, issues)
            resolved_assets.append(str(voiceover_path.resolve()))
        events = self._collect_sfx(beats)
        if events:
            self._sfx(project, events, program_duration, source_digest, has_voiceover, issues)
        self._preserve_unexecuted(payload, beats, issues)
        validation = validate_project(project)
        for validation_issue in validation.issues:
            issues.append(
                MigrationIssue(
                    code=f"canonical.{validation_issue.code}",
                    severity=(
                        MigrationSeverity.ERROR
                        if validation_issue.severity.value == "error"
                        else MigrationSeverity.WARNING
                    ),
                    disposition=MigrationDisposition.PRESERVED,
                    message=validation_issue.message,
                    canonical_path=validation_issue.path,
                )
            )
        report = MigrationReport(
            adapter=AdapterKind.FACELESS,
            source_path=source_path,
            source_sha256=source_digest,
            sidecar_sha256=sidecars,
            source_schema=f"video-use-faceless/v{payload.get('schema_version', 1)}",
            project_id=project.id,
            project_schema_version=project.schema_version,
            issues=tuple(issues),
            preserved_metadata={
                "legacy_root_keys": sorted(payload),
                "sidecar_paths": sorted(sidecars),
            },
            resolved_assets=tuple(sorted(set(resolved_assets))),
        )
        return MigrationResult(project=project, report=report)

    def _base_track(
        self,
        project: Project,
        beats: list[Any],
        manifest: dict[str, dict[str, Any]],
        project_dir: Path,
        rate: FrameRate,
        transition_duration: RationalTime | None,
        issues: list[MigrationIssue],
    ) -> tuple[VideoTrack, list[tuple[dict[str, Any], TimeRange]], list[str]]:
        track = VideoTrack(id="video-primary", name="Primary visuals")
        records: list[tuple[dict[str, Any], TimeRange]] = []
        resolved_assets: list[str] = []
        cursor = RationalTime.zero()
        for index, raw in enumerate(beats):
            if not isinstance(raw, dict):
                raise EngineError(
                    ErrorCode.MIGRATION,
                    "faceless beat must be an object",
                    context={"index": index},
                )
            beat = cast(dict[str, Any], raw)
            beat_id = str(beat.get("beat_id") or f"B{index + 1:02d}")
            declared_start = _time(beat.get("start", cursor.fraction))
            declared_end = _time(beat.get("end", declared_start.fraction + 1))
            raw_duration = max(
                declared_end - declared_start,
                RationalTime(value=1, timescale=5),
            )
            start = rate.frames_to_time(rate.time_to_frames(declared_start, RoundingMode.NEAREST))
            duration = rate.frames_to_time(
                max(1, rate.time_to_frames(raw_duration, RoundingMode.NEAREST))
            )
            if start < cursor:
                raise EngineError(
                    ErrorCode.MIGRATION,
                    "faceless primary beats overlap after frame quantization",
                    context={"beat_id": beat_id, "start": start.model_dump(mode="json")},
                )
            if start > cursor:
                track.items.append(
                    Gap(
                        id=f"gap-before-{_slug(beat_id)}",
                        name="Authored gap",
                        timeline_range=TimeRange(start=cursor, duration=start - cursor),
                        extensions={"legacy:gap_preserved": True},
                    )
                )
                issues.append(
                    self._issue(
                        "faceless.absolute_gap_preserved",
                        (
                            "declared beat gap is now explicit instead of being removed "
                            "by concatenation"
                        ),
                        MigrationDisposition.IMPROVED,
                        f"beats[{index}].start",
                    )
                )
            item_range = TimeRange(start=start, duration=duration)
            asset = self._resolve_beat_asset(project_dir, beat, manifest)
            effects = self._beat_effects(
                beat,
                item_range,
                rate,
                issues,
                index,
                still_asset=asset is not None and asset.suffix.lower() in IMAGE_SUFFIXES,
            )
            if asset is None:
                title = str(
                    beat.get("visual_job") or beat.get("script_text") or f"Beat {index + 1}"
                ).strip()
                track.items.append(
                    GeneratorClip(
                        id=f"beat-{_slug(beat_id)}",
                        name=beat_id,
                        timeline_range=item_range,
                        generator_id="title_card",
                        transparent=False,
                        properties={
                            "title": title[:180] or f"Beat {index + 1}",
                            "alignment": "center",
                        },
                        extensions={"legacy:beat": beat, "legacy:missing_asset": True},
                    )
                )
                issues.append(
                    self._issue(
                        "faceless.missing_asset_placeholder",
                        "missing legacy asset was replaced with a cacheable Remotion placeholder",
                        MigrationDisposition.IMPROVED,
                        f"beats[{index}]",
                    )
                )
            else:
                reference = self._import_media(asset)
                required = duration + (
                    transition_duration
                    if transition_duration is not None and index < len(beats) - 1
                    else RationalTime.zero()
                )
                if asset.suffix.lower() in VIDEO_SUFFIXES:
                    if (
                        reference.available_range is None
                        or reference.available_range.duration < required
                    ):
                        derivative = self.media_service.looped_conform(
                            reference.id,
                            duration=required,
                            frame_rate_numerator=rate.numerator,
                            frame_rate_denominator=rate.denominator,
                        )
                        reference = self._import_media(derivative.paths[0])
                        issues.append(
                            self._issue(
                                "faceless.video_loop_materialized",
                                "legacy infinite source loop was materialized as a cached conform",
                                MigrationDisposition.EXECUTED,
                                f"beats[{index}].primary_asset_path",
                            )
                        )
                    item: Clip | StillImageClip = Clip(
                        id=f"beat-{_slug(beat_id)}",
                        name=beat_id,
                        media_reference_id=reference.id,
                        timeline_range=item_range,
                        source_range=TimeRange(start=RationalTime.zero(), duration=duration),
                        source_audio_enabled=False,
                        effects=effects,
                        extensions={"legacy:beat": beat},
                    )
                elif asset.suffix.lower() in IMAGE_SUFFIXES:
                    item = StillImageClip(
                        id=f"beat-{_slug(beat_id)}",
                        name=beat_id,
                        media_reference_id=reference.id,
                        timeline_range=item_range,
                        effects=effects,
                        extensions={"legacy:beat": beat},
                    )
                else:
                    raise EngineError(
                        ErrorCode.MIGRATION,
                        "faceless primary asset type is unsupported",
                        context={"path": str(asset), "beat_id": beat_id},
                    )
                self._append_media(project, reference)
                track.items.append(item)
                resolved_assets.append(str(asset.resolve()))
            records.append((beat, item_range))
            cursor = item_range.end
        return track, records, resolved_assets

    def _beat_effects(
        self,
        beat: dict[str, Any],
        item_range: TimeRange,
        rate: FrameRate,
        issues: list[MigrationIssue],
        beat_index: int,
        *,
        still_asset: bool,
    ) -> list[Effect]:
        effects = [
            Effect(
                id=f"beat-{beat_index + 1}-reframe",
                kind=EffectKind.REFRAME,
                parameters={"fit": "cover", "focus_x": 0.5, "focus_y": 0.5},
            )
        ]
        layers = [layer for layer in _list(beat.get("layers")) if isinstance(layer, dict)]
        grades = [
            cast(dict[str, Any], layer) for layer in layers if layer.get("type") == "color_grade"
        ]
        filters = _dict(grades[0].get("filters")) if grades else {}
        contrast = float(filters.get("contrast", 1.05))
        saturation = float(filters.get("saturation", 1.06))
        brightness = float(filters.get("brightness", 0))
        grade_parameters: dict[str, Any] = {
            "contrast": max(0, min(4, contrast)),
            "saturation": max(0, min(4, saturation)),
        }
        if brightness:
            grade_parameters["exposure_stops"] = max(
                -10, min(10, math.log2(max(0.001, 1 + brightness)))
            )
            issues.append(
                self._issue(
                    "faceless.brightness_approximated",
                    "legacy additive brightness was approximated with exposure stops",
                    MigrationDisposition.APPROXIMATED,
                    f"beats[{beat_index}].layers.color_grade.filters.brightness",
                )
            )
        effects.append(
            Effect(
                id=f"beat-{beat_index + 1}-grade",
                kind=EffectKind.COLOR_GRADE,
                parameters=grade_parameters,
            )
        )
        issues.append(
            self._issue(
                "faceless.sharpen_preserved",
                "legacy implicit unsharp filtering is preserved in migration metadata",
                MigrationDisposition.PRESERVED,
                f"beats[{beat_index}]",
                severity=MigrationSeverity.INFO,
            )
        )
        camera = next(
            (
                cast(dict[str, Any], layer)
                for layer in layers
                if layer.get("type") == "camera_motion"
            ),
            None,
        )
        static = bool(beat.get("static_frame") or beat.get("stock_montage_static"))
        if camera is not None and _list(camera.get("keyframes")):
            scale_keys: list[Keyframe] = []
            position_keys: list[Keyframe] = []
            for key_index, raw_key in enumerate(_list(camera.get("keyframes"))):
                if not isinstance(raw_key, dict):
                    continue
                key = cast(dict[str, Any], raw_key)
                relative = _time(key.get("time", item_range.start.fraction)) - item_range.start
                relative = max(RationalTime.zero(), min(item_range.duration, relative))
                scale = float(key.get("scale", 1))
                for axis in ("x", "y"):
                    scale_keys.append(
                        Keyframe(
                            id=f"camera-scale-{axis}-{key_index + 1}",
                            property_path=axis,
                            time=relative,
                            value=scale,
                        )
                    )
                for axis in ("x", "y"):
                    position_keys.append(
                        Keyframe(
                            id=f"camera-position-{axis}-{key_index + 1}",
                            property_path=axis,
                            time=relative,
                            value=float(key.get(axis, 0)),
                        )
                    )
            effects.extend(
                [
                    Effect(
                        id=f"beat-{beat_index + 1}-camera-scale",
                        kind=EffectKind.SCALE,
                        parameters={"x": 1, "y": 1},
                        keyframes=scale_keys,
                    ),
                    Effect(
                        id=f"beat-{beat_index + 1}-camera-position",
                        kind=EffectKind.POSITION,
                        parameters={"x": 0, "y": 0},
                        keyframes=position_keys,
                    ),
                ]
            )
            issues.append(
                self._issue(
                    "faceless.camera_motion_activated",
                    "previously ignored camera keyframes are now executed canonically",
                    MigrationDisposition.IMPROVED,
                    f"beats[{beat_index}].layers.camera_motion",
                    severity=MigrationSeverity.INFO,
                )
            )
        elif not static and still_asset:
            end_scale = min(
                1.075,
                1 + 0.0012 * rate.time_to_frames(item_range.duration, RoundingMode.NEAREST),
            )
            keyframes = []
            for axis in ("x", "y"):
                keyframes.extend(
                    [
                        Keyframe(
                            id=f"still-scale-{axis}-start",
                            property_path=axis,
                            time=RationalTime.zero(),
                            value=1,
                        ),
                        Keyframe(
                            id=f"still-scale-{axis}-end",
                            property_path=axis,
                            time=item_range.duration,
                            value=end_scale,
                        ),
                    ]
                )
            effects.append(
                Effect(
                    id=f"beat-{beat_index + 1}-implicit-push",
                    kind=EffectKind.SCALE,
                    parameters={"x": 1, "y": 1},
                    keyframes=keyframes,
                )
            )
        return effects

    def _graphics_tracks(
        self,
        project: Project,
        records: list[tuple[dict[str, Any], TimeRange]],
        duration: RationalTime,
        rate: FrameRate,
        colors: dict[str, str],
        stock_mode: bool,
        issues: list[MigrationIssue],
    ) -> None:
        families: dict[str, list[GraphicsTrack]] = {
            "progress": [],
            "diagram": [],
            "emphasis": [],
        }
        total_frames = max(1, rate.time_to_frames(duration, RoundingMode.CEIL))
        for index, (beat, beat_range) in enumerate(records):
            layers = [layer for layer in _list(beat.get("layers")) if isinstance(layer, dict)]
            if not stock_mode:
                self._place_graphic(
                    families["progress"],
                    "progress",
                    GeneratorClip(
                        id=f"progress-{index + 1}",
                        timeline_range=beat_range,
                        generator_id="progress_accent",
                        properties={
                            "global_start_frame": rate.time_to_frames(
                                beat_range.start, RoundingMode.EXACT
                            ),
                            "total_frames": total_frames,
                            "accent_color": colors["accent_color"],
                            "text_color": colors["text_color"],
                            "background_color": colors["background_color"],
                        },
                    ),
                )
            diagrams = [
                cast(dict[str, Any], layer)
                for layer in layers
                if layer.get("type") == "visual_motion_overlay"
            ]
            if diagrams:
                layer = diagrams[0]
                layer_range = self._layer_range(layer, beat_range, rate)
                if layer_range is not None:
                    raw_variant = str(layer.get("effect", "label_pop"))
                    variant: Literal[
                        "corner_pulse", "arrow_trace", "outline_trace", "label_pop"
                    ] = (
                        cast(
                            Literal["corner_pulse", "arrow_trace", "outline_trace"],
                            raw_variant,
                        )
                        if raw_variant in {"corner_pulse", "arrow_trace", "outline_trace"}
                        else "label_pop"
                    )
                    self._place_graphic(
                        families["diagram"],
                        "diagram",
                        GeneratorClip(
                            id=f"diagram-{index + 1}",
                            timeline_range=layer_range,
                            generator_id="diagram_overlay",
                            properties={
                                "variant": variant,
                                "label": str(layer.get("label") or "") or None,
                                "layout_variant": (
                                    "payoff"
                                    if str(beat.get("purpose", "")).lower() == "payoff"
                                    else "default"
                                ),
                                "accent_color": colors["accent_color"],
                                "text_color": colors["text_color"],
                                "background_color": colors["background_color"],
                            },
                            extensions={"legacy:layer": layer},
                        ),
                    )
            emphases = [
                cast(dict[str, Any], layer)
                for layer in layers
                if layer.get("type") == "emphasis_text"
            ]
            if emphases:
                layer = emphases[0]
                text = str(layer.get("text") or "").strip()
                layer_range = self._layer_range(layer, beat_range, rate)
                if text and not layer.get("suppressed") and layer_range is not None:
                    self._place_graphic(
                        families["emphasis"],
                        "emphasis",
                        GeneratorClip(
                            id=f"emphasis-{index + 1}",
                            timeline_range=layer_range,
                            generator_id="emphasis_text",
                            properties={
                                "text": text,
                                "variant": self._emphasis_variant(str(layer.get("effect", ""))),
                                "secondary_accent": colors["secondary_accent"],
                                "danger_accent": colors["danger_accent"],
                                "accent_color": str(
                                    layer.get("accent_color") or colors["accent_color"]
                                ),
                                "text_color": colors["text_color"],
                                "background_color": colors["background_color"],
                            },
                            extensions={"legacy:layer": layer},
                        ),
                    )
            if len(diagrams) > 1 or len(emphases) > 1:
                issues.append(
                    self._issue(
                        "faceless.first_visual_layer_only",
                        (
                            "additional same-type visual layers were preserved because the "
                            "legacy renderer executed only the first"
                        ),
                        MigrationDisposition.PRESERVED,
                        f"beats[{index}].layers",
                    )
                )
        for family in ("progress", "diagram", "emphasis"):
            project.sequence().timeline.tracks.extend(families[family])

    def _rich_captions(
        self,
        project: Project,
        payload: dict[str, Any],
        records: list[tuple[dict[str, Any], TimeRange]],
        program_duration: RationalTime,
        rate: FrameRate,
        colors: dict[str, str],
        stock_mode: bool,
        issues: list[MigrationIssue],
    ) -> None:
        cues: list[CaptionCue] = []
        designed_tracks: list[GraphicsTrack] = []
        occupied_until = RationalTime.zero()
        program = TimeRange(start=RationalTime.zero(), duration=program_duration)
        for index, raw in enumerate(_list(payload.get("cues"))):
            if not isinstance(raw, dict):
                continue
            cue = cast(dict[str, Any], raw)
            start_frames = rate.time_to_frames(_time(cue.get("start", 0)), RoundingMode.CEIL)
            end_frames = rate.time_to_frames(_time(cue.get("end", 0)), RoundingMode.CEIL)
            start = rate.frames_to_time(start_frames)
            end = rate.frames_to_time(end_frames)
            if start < occupied_until:
                start = occupied_until
                issues.append(
                    self._issue(
                        "faceless.caption_overlap_trimmed",
                        (
                            "overlapping rich caption was trimmed to preserve legacy "
                            "first-cue precedence"
                        ),
                        MigrationDisposition.EXECUTED,
                        f"captions.cues[{index}]",
                    )
                )
            visible = TimeRange.from_start_end(start, max(start, end)).intersection(program)
            text = str(cue.get("text") or "").strip()
            if visible is None or visible.is_empty or not text:
                continue
            occupied_until = visible.end
            beat = next(
                (item for item, item_range in records if item_range.contains(visible.start)),
                {},
            )
            kinetic = next(
                (
                    cast(dict[str, Any], layer)
                    for layer in _list(beat.get("layers"))
                    if isinstance(layer, dict) and layer.get("type") == "caption_kinetic"
                ),
                {},
            )
            effect = str(kinetic.get("effect") or cue.get("style_id") or "")
            suppressed = "caption_suppressed" in effect
            emphasis_terms = [str(value) for value in _list(cue.get("emphasis_terms"))]
            cues.append(
                CaptionCue(
                    id=f"caption-{index + 1}",
                    text=text,
                    timeline_range=visible,
                    style_id="legacy-faceless",
                    suppressed=suppressed or True,
                    extensions={
                        "legacy:cue": cue,
                        "legacy:designed_burn_in": not suppressed,
                        "emphasis_terms": emphasis_terms,
                    },
                )
            )
            if not suppressed:
                self._place_graphic(
                    designed_tracks,
                    "designed-caption",
                    GeneratorClip(
                        id=f"designed-caption-{index + 1}",
                        timeline_range=visible,
                        generator_id="kinetic_caption",
                        properties={
                            "text": text,
                            "variant": self._caption_variant(effect, stock_mode),
                            "emphasis_terms": emphasis_terms,
                            "secondary_accent": colors["secondary_accent"],
                            "accent_color": colors["accent_color"],
                            "text_color": colors["text_color"],
                            "background_color": colors["background_color"],
                        },
                        extensions={"legacy:cue": cue},
                    ),
                )
        if cues:
            project.caption_styles = [
                CaptionStyle(
                    id="legacy-faceless",
                    name="Legacy Faceless Data",
                    primary_color=colors["text_color"],
                    highlight_color=colors["accent_color"],
                )
            ]
            project.sequence().timeline.tracks.extend(designed_tracks)
            project.sequence().timeline.tracks.append(
                CaptionTrack(
                    id="captions-native",
                    name="Native rich captions (designed burn-in selected)",
                    default_style_id="legacy-faceless",
                    items=cast(list[CaptionCue | Gap], cues),
                    extensions={"burn_in_mode": "designed_graphics"},
                )
            )
            issues.append(
                self._issue(
                    "faceless.rich_captions_remotion",
                    "Pillow caption overlays were migrated to full-resolution Remotion typography",
                    MigrationDisposition.IMPROVED,
                    "captions/captions.json",
                    severity=MigrationSeverity.INFO,
                )
            )

    def _sidecar_captions(
        self,
        project: Project,
        path: Path,
        program_duration: RationalTime,
        issues: list[MigrationIssue],
    ) -> None:
        imported = self.caption_service.import_file(path, track_id="captions-native")
        program = TimeRange(start=RationalTime.zero(), duration=program_duration)
        imported.track.items = [
            cue.model_copy(update={"timeline_range": visible})
            for cue in imported.track.items
            if (visible := cue.timeline_range.intersection(program)) is not None
        ]
        if imported.track.items:
            project.caption_styles = list(imported.styles)
            project.sequence().timeline.tracks.append(imported.track)
        for loss in imported.losses:
            issues.append(
                self._issue(
                    "faceless.caption_import_loss",
                    loss.disposition,
                    MigrationDisposition.PRESERVED,
                    f"captions:{loss.item_id or ''}",
                    details={"feature": loss.feature},
                )
            )

    def _voiceover(
        self,
        project: Project,
        path: Path,
        program_duration: RationalTime,
        issues: list[MigrationIssue],
    ) -> bool:
        reference = self._import_media(path)
        self._append_media(project, reference)
        available = (
            reference.available_range.duration if reference.available_range else program_duration
        )
        duration = min(program_duration, available)
        effects: list[Effect] = []
        track = AudioTrack(id="audio-voiceover", name="Voice-over", role=AudioRole.VOICE_OVER)
        track.items.append(
            AudioClip(
                id="voiceover-main",
                media_reference_id=reference.id,
                timeline_range=TimeRange(start=RationalTime.zero(), duration=duration),
                source_range=TimeRange(start=RationalTime.zero(), duration=duration),
                role=AudioRole.VOICE_OVER,
                effects=effects,
            )
        )
        project.sequence().timeline.tracks.append(track)
        if duration < program_duration:
            issues.append(
                self._issue(
                    "faceless.voiceover_no_longer_truncates_picture",
                    "short voice-over ends without truncating the authored picture duration",
                    MigrationDisposition.IMPROVED,
                    str(path),
                )
            )
        return True

    def _sfx(
        self,
        project: Project,
        events: list[_LegacySFX],
        program_duration: RationalTime,
        source_digest: str,
        has_voiceover: bool,
        issues: list[MigrationIssue],
    ) -> None:
        normalized = [
            {
                "beat_id": event.beat_id,
                "time": event.time,
                "kind": event.kind.value,
                "level": event.level,
                "description": event.description,
            }
            for event in events
        ]
        key = hashlib.sha256(
            json.dumps(
                {"source": source_digest, "events": normalized, "recipe": "legacy-video-use-v1"},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        output = (
            self.project_root / ".video-engine" / "migrations" / "faceless" / key / "legacy-sfx.wav"
        )
        total_samples = int((program_duration.fraction + Fraction(1, 2)) * LEGACY_SFX_SAMPLE_RATE)
        synth_events = tuple(
            SynthEffectEvent(
                id=f"legacy-sfx-{index + 1}",
                start=AudioSampleTime(
                    samples=max(0, int(event.time * LEGACY_SFX_SAMPLE_RATE)),
                    sample_rate=LEGACY_SFX_SAMPLE_RATE,
                ),
                kind=event.kind,
                gain=self._sfx_gain(event.kind, event.level),
                seed_key=f"{event.beat_id}-{event.time}-{event.kind.value}-{index}",
            )
            for index, event in enumerate(events)
        )
        result = synthesize_effects(
            SynthesisRequest(
                output_path=output,
                duration=AudioSampleTime(
                    samples=total_samples,
                    sample_rate=LEGACY_SFX_SAMPLE_RATE,
                ),
                events=synth_events,
                recipe_version="legacy-video-use-v1",
            )
        )
        reference = self._import_media(result.output_path)
        self._append_media(project, reference)
        effects = (
            [
                Effect(
                    id="legacy-amix-normalization",
                    kind=EffectKind.GAIN,
                    parameters={"db": -6.020599913279624},
                )
            ]
            if has_voiceover
            else []
        )
        if has_voiceover:
            voice_track = next(
                track
                for track in project.sequence().timeline.tracks
                if isinstance(track, AudioTrack) and track.role is AudioRole.VOICE_OVER
            )
            assert isinstance(voice_track.items[0], AudioClip)
            voice_track.items[0].effects.append(
                Effect(
                    id="legacy-amix-normalization-voiceover",
                    kind=EffectKind.GAIN,
                    parameters={"db": -6.020599913279624},
                )
            )
            master = next(
                bus
                for bus in project.sequence().timeline.audio_buses
                if bus.id == project.sequence().timeline.master_bus_id
            )
            master.effects.append(
                Effect(
                    id="legacy-sfx-master-limiter",
                    kind=EffectKind.LIMITER,
                    parameters={"linear_peak": 0.93},
                )
            )
        track = AudioTrack(
            id="audio-sfx",
            name="Materialized legacy SFX",
            role=AudioRole.SFX,
            extensions={
                "recipe": "legacy-video-use-v1",
                "events": normalized,
                "sha256": result.sha256,
            },
            items=[
                AudioClip(
                    id="legacy-sfx-stem",
                    media_reference_id=reference.id,
                    timeline_range=TimeRange(start=RationalTime.zero(), duration=program_duration),
                    source_range=TimeRange(start=RationalTime.zero(), duration=program_duration),
                    role=AudioRole.SFX,
                    effects=effects,
                )
            ],
        )
        project.sequence().timeline.tracks.append(track)
        for index, event in enumerate(events):
            start = RationalTime(
                value=max(0, int(event.time * LEGACY_SFX_SAMPLE_RATE)),
                timescale=LEGACY_SFX_SAMPLE_RATE,
            )
            if start < program_duration:
                project.sequence().timeline.markers.append(
                    Marker(
                        id=f"legacy-sfx-event-{index + 1}",
                        time=start,
                        name=event.kind.value,
                        comment=event.description,
                        extensions={"beat_id": event.beat_id, "level": event.level},
                    )
                )
        issues.append(
            self._issue(
                "faceless.sfx_materialized",
                "implicit legacy sound-design decisions were materialized as a deterministic stem",
                MigrationDisposition.EXECUTED,
                "beats[].layers.sound_cue",
                details={"event_count": len(events), "sha256": result.sha256},
                severity=MigrationSeverity.INFO,
            )
        )

    @staticmethod
    def _collect_sfx(beats: list[Any]) -> list[_LegacySFX]:
        events: list[_LegacySFX] = []
        for beat_index, raw in enumerate(beats):
            if not isinstance(raw, dict):
                continue
            beat = cast(dict[str, Any], raw)
            beat_id = str(beat.get("beat_id") or f"B{beat_index + 1:02d}")
            beat_start = float(beat.get("start", 0))
            beat_end = float(beat.get("end", beat_start + 1))
            for raw_layer in _list(beat.get("layers")):
                if not isinstance(raw_layer, dict):
                    continue
                layer = cast(dict[str, Any], raw_layer)
                if layer.get("type") == "sound_cue":
                    level = str(layer.get("level", "low_under_voice"))
                    declared_events = _list(layer.get("events"))
                    for raw_event in declared_events:
                        if not isinstance(raw_event, dict):
                            continue
                        event_data = cast(dict[str, Any], raw_event)
                        events.append(
                            _LegacySFX(
                                beat_id=beat_id,
                                time=float(event_data.get("time", layer.get("start", beat_start))),
                                kind=FacelessAdapterService._normalize_sfx_kind(
                                    str(event_data.get("kind", layer.get("effect", "")))
                                ),
                                level=str(event_data.get("level", level)),
                                description=str(event_data.get("description", "")),
                            )
                        )
                    if not declared_events:
                        events.append(
                            _LegacySFX(
                                beat_id=beat_id,
                                time=float(layer.get("start", beat_start)),
                                kind=FacelessAdapterService._normalize_sfx_kind(
                                    str(layer.get("effect", ""))
                                ),
                                level=level,
                                description="compiled sound cue",
                            )
                        )
                elif layer.get("type") == "emphasis_text" and not layer.get("suppressed"):
                    effect = str(layer.get("effect", ""))
                    kind = (
                        SynthEffectKind.GLITCH
                        if "glitch" in effect or "font_shift" in effect
                        else (
                            SynthEffectKind.SHIMMER
                            if "highlight" in effect or "wipe" in effect
                            else SynthEffectKind.POP
                        )
                    )
                    events.append(
                        _LegacySFX(
                            beat_id=beat_id,
                            time=float(layer.get("start", beat_start)),
                            kind=kind,
                            level="very low_under_voice",
                            description=f"text effect sync: {effect}",
                        )
                    )
            if beat_index and beat_start < beat_end:
                events.append(
                    _LegacySFX(
                        beat_id=beat_id,
                        time=beat_start,
                        kind=SynthEffectKind.WHOOSH,
                        level="very low_under_voice",
                        description="beat transition motion support",
                    )
                )
        deduped: list[_LegacySFX] = []
        seen: set[tuple[str, int, SynthEffectKind]] = set()
        for compiled_event in sorted(events, key=lambda item: item.time):
            key = (
                compiled_event.beat_id,
                round(compiled_event.time * 30),
                compiled_event.kind,
            )
            if key not in seen:
                seen.add(key)
                deduped.append(compiled_event)
        return deduped

    @staticmethod
    def _normalize_sfx_kind(value: str) -> SynthEffectKind:
        value = value.lower().strip()
        if "glitch" in value or "font" in value:
            return SynthEffectKind.GLITCH
        if "tick" in value or "marker" in value or "diagram" in value:
            return SynthEffectKind.TICK
        if "shimmer" in value or "highlight" in value or "wipe" in value:
            return SynthEffectKind.SHIMMER
        if "reverse" in value or "riser" in value:
            return SynthEffectKind.REVERSE_HIT
        if "whoosh" in value or "transition" in value:
            return SynthEffectKind.WHOOSH
        if any(token in value for token in ("resolve", "hit", "impact", "pop")):
            return SynthEffectKind.POP
        return SynthEffectKind.TICK

    @staticmethod
    def _sfx_gain(kind: SynthEffectKind, level: str) -> float:
        gain = {
            SynthEffectKind.TICK: 0.09,
            SynthEffectKind.SHIMMER: 0.075,
            SynthEffectKind.GLITCH: 0.07,
            SynthEffectKind.WHOOSH: 0.08,
            SynthEffectKind.REVERSE_HIT: 0.07,
            SynthEffectKind.POP: 0.10,
        }[kind]
        lowered = level.lower()
        if "very low" in lowered:
            gain *= 0.62
        elif "low" in lowered:
            gain *= 0.78
        elif "under" in lowered:
            gain *= 0.7
        return gain

    @staticmethod
    def _place_graphic(lanes: list[GraphicsTrack], family: str, item: GeneratorClip) -> None:
        for lane in lanes:
            if all(
                not existing.timeline_range.overlaps(item.timeline_range) for existing in lane.items
            ):
                lane.items.append(item)
                return
        lane_index = len(lanes) + 1
        lanes.append(
            GraphicsTrack(
                id=f"graphics-{family}-{lane_index}",
                name=f"{family.replace('-', ' ').title()} {lane_index}",
                items=[item],
            )
        )

    @staticmethod
    def _layer_range(
        layer: dict[str, Any], beat_range: TimeRange, rate: FrameRate
    ) -> TimeRange | None:
        start = rate.frames_to_time(
            rate.time_to_frames(
                _time(layer.get("start", beat_range.start.fraction)),
                RoundingMode.CEIL,
            )
        )
        raw_end = _time(layer.get("end", beat_range.end.fraction))
        end_frame = rate.time_to_frames(raw_end, RoundingMode.FLOOR) + 1
        end = rate.frames_to_time(end_frame)
        return TimeRange.from_start_end(start, max(start, end)).intersection(beat_range)

    @staticmethod
    def _emphasis_variant(value: str) -> str:
        return {
            "capcut_highlight_wipe": "highlight_wipe",
            "capcut_staggered_blur_glitch_reveal": "staggered_glitch",
            "capcut_axis_stretch_word": "axis_stretch",
            "capcut_font_shift_loop": "font_shift",
            "capcut_apple_slide_up_text": "slide_up",
        }.get(value, "glow_underline")

    @staticmethod
    def _caption_variant(value: str, stock_mode: bool) -> str:
        if stock_mode:
            return "stock_panel"
        if "adaptive_texture" in value:
            return "adaptive_texture"
        if "player3" in value:
            return "player3"
        return "default"

    @staticmethod
    def _transition_duration(
        project: dict[str, Any], rate: FrameRate, enabled: bool
    ) -> RationalTime | None:
        if not enabled:
            return None
        raw = max(0.08, min(0.65, float(project.get("transition_duration_seconds", 0.32))))
        frames = max(1, rate.time_to_frames(_time(raw), RoundingMode.NEAREST))
        return rate.frames_to_time(frames)

    @staticmethod
    def _add_transitions(
        track: VideoTrack,
        duration: RationalTime | None,
        project: dict[str, Any],
        issues: list[MigrationIssue],
    ) -> None:
        if duration is None:
            return
        endpoints = [item for item in track.items if not isinstance(item, Gap)]
        raw_kind = str(project.get("transition_xfade", "fade"))
        kinds = {
            "fade": TransitionKind.DISSOLVE,
            "fadeblack": TransitionKind.DIP_TO_COLOR,
            "wipeleft": TransitionKind.WIPE,
            "wiperight": TransitionKind.WIPE,
            "slideleft": TransitionKind.SLIDE,
            "slideright": TransitionKind.SLIDE,
            "zoomin": TransitionKind.ZOOM,
        }
        kind = kinds.get(raw_kind, TransitionKind.DISSOLVE)
        if raw_kind not in kinds:
            issues.append(
                FacelessAdapterService._issue(
                    "faceless.transition_approximated",
                    "unknown legacy xfade was approximated with a dissolve",
                    MigrationDisposition.APPROXIMATED,
                    "project.transition_xfade",
                    details={"legacy": raw_kind},
                )
            )
        for index, (left, right) in enumerate(pairwise(endpoints)):
            if left.timeline_range.end != right.timeline_range.start:
                continue
            if not isinstance(left, (Clip, StillImageClip)) or not isinstance(
                right, (Clip, StillImageClip)
            ):
                issues.append(
                    FacelessAdapterService._issue(
                        "faceless.placeholder_transition_preserved",
                        "transition adjacent to a generated placeholder was preserved in metadata",
                        MigrationDisposition.PRESERVED,
                        f"transitions[{index}]",
                    )
                )
                continue
            track.transitions.append(
                Transition(
                    id=f"stock-transition-{index + 1}",
                    kind=kind,
                    from_item_id=left.id,
                    to_item_id=right.id,
                    duration=min(
                        duration,
                        left.timeline_range.duration,
                        right.timeline_range.duration,
                    ),
                    alignment="start_at_cut",
                    extensions={"legacy:transition_xfade": raw_kind},
                )
            )

    @staticmethod
    def _manifest_lookup(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = {}
        for raw in _list(payload.get("assets")):
            if not isinstance(raw, dict):
                continue
            asset = cast(dict[str, Any], raw)
            for key in ("manifest_id", "asset_id"):
                if asset.get(key):
                    lookup[str(asset[key])] = asset
        return lookup

    @staticmethod
    def _resolve_beat_asset(
        project_dir: Path,
        beat: dict[str, Any],
        manifest: dict[str, dict[str, Any]],
    ) -> Path | None:
        candidate = beat.get("primary_asset_path")
        if candidate:
            path = Path(str(candidate))
            path = path if path.is_absolute() else project_dir / path
            if path.is_file():
                return path.resolve()
        asset = manifest.get(str(beat.get("primary_asset_id", "")))
        if asset and asset.get("local_path"):
            path = Path(str(asset["local_path"]))
            path = path if path.is_absolute() else project_dir / path
            if path.is_file():
                return path.resolve()
        return None

    @staticmethod
    def _colors(directive: dict[str, Any]) -> dict[str, str]:
        style = _dict(directive.get("style"))

        def color(name: str, fallback: str) -> str:
            value = str(style.get(name) or fallback)
            return value if re.fullmatch(r"#[0-9A-Fa-f]{6}", value) else fallback

        return {
            "accent_color": color("accent_color", "#38BDF8"),
            "secondary_accent": color("secondary_accent", "#FACC15"),
            "danger_accent": color("danger_accent", "#FB7185"),
            "text_color": color("text_color", "#FFFFFF"),
            "background_color": color("background_color", "#111111"),
        }

    @staticmethod
    def _resolution(project: dict[str, Any]) -> tuple[int, int]:
        resolution = _dict(project.get("resolution"))
        try:
            width = int(resolution.get("width", 1080))
            height = int(resolution.get("height", 1920))
        except (TypeError, ValueError) as exc:
            raise EngineError(ErrorCode.MIGRATION, "faceless resolution is invalid") from exc
        if width <= 0 or height <= 0:
            raise EngineError(ErrorCode.MIGRATION, "faceless resolution must be positive")
        return width - width % 2, height - height % 2

    @staticmethod
    def _frame_rate(value: object) -> FrameRate:
        try:
            fraction = Fraction(str(value))
            return FrameRate(numerator=fraction.numerator, denominator=fraction.denominator)
        except (ValueError, ZeroDivisionError) as exc:
            raise EngineError(ErrorCode.MIGRATION, "faceless frame rate is invalid") from exc

    @staticmethod
    def _project(
        name: str,
        identity: str,
        width: int,
        height: int,
        rate: FrameRate,
        sample_rate: int,
    ) -> Project:
        return Project(
            id=f"project-{_slug(name)}-{identity}",
            name=name,
            settings=ProjectSettings(
                width=width,
                height=height,
                frame_rate=rate,
                audio_sample_rate=sample_rate,
                audio_boundary_fade=RationalTime.zero(),
            ),
            sequences=[Sequence(id="sequence-main", name="Main", timeline=Timeline())],
            active_sequence_id="sequence-main",
            delivery_profiles=[
                DeliveryProfile(
                    id="preview",
                    name="Preview",
                    width=width,
                    height=height,
                    frame_rate=rate,
                    audio_sample_rate=sample_rate,
                    crf=22,
                    preset="veryfast",
                ),
                DeliveryProfile(
                    id="final",
                    name="Final",
                    width=width,
                    height=height,
                    frame_rate=rate,
                    audio_sample_rate=sample_rate,
                    crf=18,
                    preset="medium",
                ),
            ],
        )

    def _voiceover_path(
        self, project_dir: Path, payload: dict[str, Any], explicit: Path | None
    ) -> Path | None:
        if explicit is not None:
            return explicit.resolve()
        voiceover = _list(_dict(payload.get("tracks")).get("voiceover"))
        for raw in voiceover:
            if isinstance(raw, dict):
                for key in ("path", "file", "local_path"):
                    if raw.get(key):
                        candidate = Path(str(raw[key]))
                        candidate = (
                            candidate if candidate.is_absolute() else project_dir / candidate
                        )
                        if candidate.is_file():
                            return candidate.resolve()
        for name in ("voiceover.mp3", "voiceover.wav", "voiceover.m4a"):
            candidate = project_dir / "assets" / "audio" / name
            if candidate.is_file():
                return candidate.resolve()
        return None

    @staticmethod
    def _caption_sidecar(project_dir: Path) -> Path | None:
        for name in ("master.ass", "master.srt", "master.vtt"):
            candidate = project_dir / "captions" / name
            if candidate.is_file():
                return candidate.resolve()
        return None

    @staticmethod
    def _timeline_path(path: Path) -> Path:
        source = path.resolve()
        if source.is_dir():
            source = source / "edit_decision_list.json"
        if not source.is_file():
            raise EngineError(
                ErrorCode.MIGRATION,
                "faceless timeline does not exist",
                context={"path": str(source)},
            )
        return source

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EngineError(
                ErrorCode.MIGRATION,
                "failed to read faceless JSON",
                context={"path": str(path), "detail": str(exc)},
            ) from exc
        if not isinstance(payload, dict):
            raise EngineError(ErrorCode.MIGRATION, "faceless JSON root must be an object")
        return cast(dict[str, Any], payload)

    def _optional_json(
        self,
        path: Path,
        hashes: dict[str, str],
        issues: list[MigrationIssue],
    ) -> dict[str, Any]:
        if not path.is_file():
            issues.append(
                self._issue(
                    "faceless.optional_sidecar_missing",
                    "optional legacy sidecar is absent",
                    MigrationDisposition.PRESERVED,
                    str(path),
                    severity=MigrationSeverity.INFO,
                )
            )
            return {}
        resolved = path.resolve()
        hashes[str(resolved)] = sha256_file(resolved)
        return self._read_json(resolved)

    def _import_media(self, path: Path) -> MediaReference:
        try:
            record = self.media_service.import_media(path, deep_vfr=False)
            return self.media_service.to_media_reference(record)
        except (EngineError, ValidationError, OSError) as exc:
            raise EngineError(
                ErrorCode.MIGRATION,
                "faceless media could not be imported",
                context={"path": str(path), "detail": str(exc)},
            ) from exc

    @staticmethod
    def _append_media(project: Project, reference: MediaReference) -> None:
        if not any(item.id == reference.id for item in project.media):
            project.media.append(reference)

    @staticmethod
    def _preserve_unexecuted(
        payload: dict[str, Any], beats: list[Any], issues: list[MigrationIssue]
    ) -> None:
        tracks = _dict(payload.get("tracks"))
        for name, value in tracks.items():
            if name != "voiceover" and value:
                issues.append(
                    FacelessAdapterService._issue(
                        "faceless.legacy_track_preserved",
                        (
                            "legacy top-level track was not executed by the deprecated "
                            "renderer and remains extension metadata"
                        ),
                        MigrationDisposition.PRESERVED,
                        f"tracks.{name}",
                        severity=MigrationSeverity.INFO,
                    )
                )
        for beat_index, raw in enumerate(beats):
            if not isinstance(raw, dict):
                continue
            for layer_index, layer in enumerate(_list(raw.get("layers"))):
                if isinstance(layer, dict) and layer.get("type") == "transition":
                    issues.append(
                        FacelessAdapterService._issue(
                            "faceless.beat_transition_preserved",
                            (
                                "per-beat transition layer was ignored historically and "
                                "remains metadata"
                            ),
                            MigrationDisposition.PRESERVED,
                            f"beats[{beat_index}].layers[{layer_index}]",
                            severity=MigrationSeverity.INFO,
                        )
                    )

    @staticmethod
    def _issue(
        code: str,
        message: str,
        disposition: MigrationDisposition,
        source_path: str,
        *,
        details: dict[str, Any] | None = None,
        severity: MigrationSeverity = MigrationSeverity.WARNING,
    ) -> MigrationIssue:
        return MigrationIssue(
            code=code,
            severity=severity,
            disposition=disposition,
            message=message,
            source_path=source_path,
            details=details or {},
        )
