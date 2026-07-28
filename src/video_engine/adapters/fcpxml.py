"""Hardened native FCPXML import into canonical multitrack projects."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from urllib.parse import unquote, urlparse

from defusedxml import ElementTree as DefusedET  # type: ignore[import-untyped]
from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]

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
    JsonValue,
    Marker,
    MediaReference,
    NestedSequenceClip,
    Project,
    ProjectSettings,
    Retime,
    Sequence,
    SequenceSettingsOverride,
    StillImageClip,
    Timeline,
    Transition,
    TransitionKind,
    VideoTrack,
)
from video_engine.core.time import (
    FrameRate,
    RationalRate,
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

_TIME = re.compile(r"^(?P<numerator>-?\d+)(?:/(?P<denominator>\d+))?s$")
_IMAGE_SUFFIXES = {".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str | None = None) -> list[ET.Element]:
    return [child for child in element if name is None or _tag(child) == name]


def _descendants(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element.iter() if _tag(child) == name]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element if _tag(item) == name), None)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "fcpxml"


def _time(value: str | None, *, default: RationalTime | None = None) -> RationalTime:
    if value is None:
        if default is None:
            raise EngineError(ErrorCode.MIGRATION, "required FCPXML time is missing")
        return default
    match = _TIME.fullmatch(value.strip())
    if match is None:
        raise EngineError(
            ErrorCode.MIGRATION,
            "FCPXML time must use exact N/Ds syntax",
            context={"value": value},
        )
    denominator = int(match.group("denominator") or 1)
    if denominator <= 0:
        raise EngineError(ErrorCode.MIGRATION, "FCPXML time denominator must be positive")
    return RationalTime.from_fraction(Fraction(int(match.group("numerator")), denominator))


class FCPXMLAdapterService:
    def __init__(self, project_root: Path, config: EngineConfig) -> None:
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)
        self.media_service = MediaService(self.project_root, self.config)

    def import_file(
        self,
        path: Path,
        *,
        name: str | None = None,
        media_paths: dict[str, Path] | None = None,
    ) -> MigrationResult:
        source = self._source_path(path)
        root = self._parse(source)
        if _tag(root) != "fcpxml":
            raise EngineError(ErrorCode.MIGRATION, "FCPXML root element must be fcpxml")
        resources = next(iter(_children(root, "resources")), None)
        if resources is None:
            raise EngineError(ErrorCode.MIGRATION, "FCPXML resources element is missing")
        project_element = next(iter(_descendants(root, "project")), None)
        if project_element is None:
            raise EngineError(ErrorCode.MIGRATION, "FCPXML project element is missing")
        main_sequence_element = _child(project_element, "sequence")
        if main_sequence_element is None:
            raise EngineError(ErrorCode.MIGRATION, "FCPXML project has no sequence")
        issues: list[MigrationIssue] = []
        formats = {
            item.get("id", ""): item for item in _children(resources, "format") if item.get("id")
        }
        asset_elements = {
            item.get("id", ""): item for item in _children(resources, "asset") if item.get("id")
        }
        media_elements = {
            item.get("id", ""): item for item in _children(resources, "media") if item.get("id")
        }
        main_rate, width, height = self._format_settings(
            main_sequence_element,
            formats,
        )
        references, resolved, offline = self._references(
            source.parent,
            asset_elements,
            media_paths or {},
            issues,
        )
        digest = sha256_file(source)
        project_name = name or project_element.get("name") or source.stem
        project = self._project(project_name, digest[:12], width, height, main_rate)
        project.media = list(references.values())
        project.extensions["fcpxml:version"] = root.get("version") or "unknown"
        project.extensions["fcpxml:source"] = str(source)
        context = _BuildContext(
            project=project,
            formats=formats,
            asset_elements=asset_elements,
            media_elements=media_elements,
            references=references,
            issues=issues,
        )
        context.nested_sequences = {
            resource_id: f"fcpxml-media-{_slug(resource_id)}"
            for resource_id, media_element in media_elements.items()
            if _child(media_element, "sequence") is not None
        }
        for resource_id, media_element in media_elements.items():
            nested_element = _child(media_element, "sequence")
            if nested_element is None:
                continue
            nested_rate, nested_width, nested_height = self._format_settings(
                nested_element, formats
            )
            nested = self._build_sequence(
                context,
                nested_element,
                sequence_id=f"fcpxml-media-{_slug(resource_id)}",
                name=media_element.get("name") or resource_id,
                rate=nested_rate,
                width=nested_width,
                height=nested_height,
                is_main=False,
            )
            project.sequences.append(nested)
        main = self._build_sequence(
            context,
            main_sequence_element,
            sequence_id="sequence-main",
            name=project_name,
            rate=main_rate,
            width=width,
            height=height,
            is_main=True,
        )
        project.sequences[0] = main
        self._validation_issues(project, issues)
        return MigrationResult(
            project=project,
            report=MigrationReport(
                adapter=AdapterKind.FCPXML,
                source_path=source,
                source_sha256=digest,
                source_schema=f"fcpxml/{root.get('version') or 'unknown'}",
                project_id=project.id,
                project_schema_version=project.schema_version,
                issues=tuple(issues),
                preserved_metadata={
                    "resource_counts": {
                        "formats": len(formats),
                        "assets": len(asset_elements),
                        "media": len(media_elements),
                    },
                    "project_attributes": dict(project_element.attrib),
                },
                resolved_assets=tuple(sorted(resolved)),
                offline_assets=tuple(sorted(offline)),
            ),
        )

    @staticmethod
    def _source_path(path: Path) -> Path:
        candidate = path.resolve()
        if candidate.is_dir():
            if candidate.suffix.lower() != ".fcpxmld":
                raise EngineError(
                    ErrorCode.MIGRATION,
                    "FCPXML directory imports must use an .fcpxmld bundle",
                )
            source = candidate / "Info.fcpxml"
            if source.is_symlink() or source.resolve().parent != candidate:
                raise EngineError(ErrorCode.MIGRATION, "unsafe FCPXML bundle entry")
            candidate = source.resolve()
        if not candidate.is_file() or candidate.suffix.lower() != ".fcpxml":
            raise EngineError(
                ErrorCode.MIGRATION,
                "FCPXML source must be an .fcpxml file or .fcpxmld bundle",
                context={"path": str(candidate)},
            )
        return candidate

    @staticmethod
    def _parse(path: Path) -> ET.Element:
        try:
            parsed: ET.Element = DefusedET.parse(path).getroot()
            return parsed
        except (OSError, ET.ParseError, DefusedXmlException) as exc:
            raise EngineError(
                ErrorCode.MIGRATION,
                "FCPXML is malformed or contains forbidden XML constructs",
                context={"path": str(path), "detail": str(exc)},
            ) from exc

    @staticmethod
    def _format_settings(
        sequence: ET.Element,
        formats: dict[str, ET.Element],
    ) -> tuple[FrameRate, int, int]:
        format_id = sequence.get("format")
        format_element = formats.get(format_id or "")
        if format_element is None:
            raise EngineError(
                ErrorCode.MIGRATION,
                "FCPXML sequence references an unknown format",
                context={"format": format_id},
            )
        frame_duration = _time(format_element.get("frameDuration"))
        if frame_duration.value <= 0:
            raise EngineError(ErrorCode.MIGRATION, "format frameDuration must be positive")
        rate_value = 1 / frame_duration.fraction
        rate = FrameRate(
            numerator=rate_value.numerator,
            denominator=rate_value.denominator,
        )
        width = int(format_element.get("width") or 1920)
        height = int(format_element.get("height") or 1080)
        return rate, max(2, width - width % 2), max(2, height - height % 2)

    def _references(
        self,
        base: Path,
        assets: dict[str, ET.Element],
        overrides: dict[str, Path],
        issues: list[MigrationIssue],
    ) -> tuple[dict[str, MediaReference], list[str], list[str]]:
        references: dict[str, MediaReference] = {}
        resolved: list[str] = []
        offline: list[str] = []
        for resource_id, asset in assets.items():
            name = asset.get("name") or resource_id
            override = overrides.get(resource_id) or overrides.get(name)
            uri = self._asset_uri(asset)
            candidate = override.resolve() if override is not None else self._uri_path(uri, base)
            if candidate is not None and candidate.is_file():
                record = self.media_service.import_media(candidate, deep_vfr=False)
                reference = self.media_service.to_media_reference(record)
                reference.extensions["fcpxml:resource_id"] = resource_id
                reference.extensions["fcpxml:asset_start"] = asset.get("start") or "0s"
                reference.extensions.update(record.probe.extensions)
                references[resource_id] = reference
                resolved.append(str(candidate))
                continue
            identity = hashlib.sha256(
                f"fcpxml-offline:{resource_id}:{uri or name}".encode()
            ).hexdigest()[:16]
            offline_uri = (
                str(candidate) if candidate is not None else uri or f"offline://{resource_id}"
            )
            references[resource_id] = MediaReference(
                id=f"offline-{identity}",
                uri=offline_uri,
                offline=True,
                extensions={
                    "fcpxml:resource_id": resource_id,
                    "fcpxml:asset_start": asset.get("start") or "0s",
                    "fcpxml:attributes": dict(asset.attrib),
                },
            )
            offline.append(offline_uri)
            issues.append(
                self._issue(
                    "fcpxml.media_offline",
                    "asset has no resolved local representation and remains relinkable",
                    MigrationDisposition.PRESERVED,
                    f"resources.asset[{resource_id}]",
                    details={"uri": offline_uri},
                )
            )
        return references, resolved, offline

    @staticmethod
    def _asset_uri(asset: ET.Element) -> str | None:
        representations = _children(asset, "media-rep")
        selected = next(
            (item for item in representations if item.get("kind") == "original-media"),
            representations[0] if representations else None,
        )
        return selected.get("src") if selected is not None else None

    @staticmethod
    def _uri_path(uri: str | None, base: Path) -> Path | None:
        if uri is None:
            return None
        parsed = urlparse(uri)
        if parsed.scheme == "file":
            if parsed.netloc not in {"", "localhost"}:
                return None
            return Path(unquote(parsed.path)).resolve()
        if parsed.scheme:
            return None
        candidate = Path(unquote(uri))
        return (candidate if candidate.is_absolute() else base / candidate).resolve()

    def _build_sequence(
        self,
        context: _BuildContext,
        sequence_element: ET.Element,
        *,
        sequence_id: str,
        name: str,
        rate: FrameRate,
        width: int,
        height: int,
        is_main: bool,
    ) -> Sequence:
        sequence = Sequence(
            id=sequence_id,
            name=name,
            timeline=Timeline(),
            settings_override=SequenceSettingsOverride(
                width=width,
                height=height,
                frame_rate=rate,
            ),
            extensions={
                "fcpxml:attributes": dict(sequence_element.attrib),
                "fcpxml:is_main": is_main,
            },
        )
        spine = _child(sequence_element, "spine")
        if spine is None:
            context.issues.append(
                self._issue(
                    "fcpxml.sequence_without_spine",
                    "sequence has no primary storyline",
                    MigrationDisposition.PRESERVED,
                    f"sequence[{sequence_id}]",
                )
            )
            return sequence
        state = _SequenceState(
            sequence=sequence,
            rate=rate,
            width=width,
            height=height,
        )
        cursor = RationalTime.zero()
        for index, element in enumerate(_children(spine)):
            tag = _tag(element)
            if tag == "transition":
                state.transitions.append(element)
                continue
            duration = self._duration(element, rate, context.issues, index)
            offset = self._offset(element, cursor, rate, context.issues, index)
            cursor = max(cursor, offset + duration)
            self._timeline_element(
                context,
                state,
                element,
                TimeRange(start=offset, duration=duration),
                source_path=f"sequence[{sequence_id}].spine[{index}]",
            )
        self._apply_transitions(context, state)
        sequence.timeline.tracks.extend(
            [
                *state.video_tracks.values(),
                *state.graphics_tracks.values(),
                *state.audio_tracks.values(),
            ]
        )
        if state.caption_items:
            sequence.timeline.tracks.append(
                CaptionTrack(
                    id=f"{sequence_id}-captions",
                    name="FCPXML captions",
                    default_style_id="fcpxml-default",
                    items=list[CaptionCue | Gap](state.caption_items),
                )
            )
            if not any(style.id == "fcpxml-default" for style in context.project.caption_styles):
                context.project.caption_styles.append(
                    CaptionStyle(id="fcpxml-default", name="FCPXML Default")
                )
        sequence.timeline.markers.extend(state.markers)
        return sequence

    def _timeline_element(
        self,
        context: _BuildContext,
        state: _SequenceState,
        element: ET.Element,
        timeline_range: TimeRange,
        *,
        source_path: str,
    ) -> None:
        tag = _tag(element)
        lane = int(element.get("lane") or 0)
        if tag == "gap":
            self._video_track(state, lane).items.append(
                Gap(
                    id=self._item_id(state, "gap"),
                    name=element.get("name") or "Gap",
                    timeline_range=timeline_range,
                    extensions={"fcpxml:attributes": dict(element.attrib)},
                )
            )
            self._connected_children(context, state, element, source_path)
            return
        if tag == "caption":
            self._caption(state, element, timeline_range)
            return
        if tag in {"title"}:
            text = (
                " ".join(
                    item.text.strip()
                    for item in _descendants(element, "text-style")
                    if item.text and item.text.strip()
                )
                or element.get("name")
                or "Title"
            )
            self._graphics_track(state, lane).items.append(
                GeneratorClip(
                    id=self._item_id(state, "title"),
                    name=element.get("name") or text,
                    timeline_range=timeline_range,
                    generator_id="title_card",
                    properties={"title": text[:180], "alignment": "center"},
                    transparent=True,
                    effects=self._visual_effects(element, state, source_path),
                    extensions=self._extensions(element, {"text", "text-style"}),
                )
            )
            return
        if tag == "ref-clip":
            reference_id = element.get("ref") or ""
            nested_id = context.nested_sequences.get(reference_id)
            if nested_id is None:
                context.issues.append(
                    self._issue(
                        "fcpxml.nested_sequence_missing",
                        "ref-clip resource has no importable sequence",
                        MigrationDisposition.PRESERVED,
                        source_path,
                        details={"ref": reference_id},
                    )
                )
                return
            source_start = _time(element.get("start"), default=RationalTime.zero())
            self._video_track(state, lane).items.append(
                NestedSequenceClip(
                    id=self._item_id(state, "nested"),
                    name=element.get("name") or reference_id,
                    sequence_id=nested_id,
                    timeline_range=timeline_range,
                    source_range=TimeRange(start=source_start, duration=timeline_range.duration),
                    source_audio_enabled=True,
                    extensions=self._extensions(element, set()),
                )
            )
            return
        if tag not in {"asset-clip", "clip", "sync-clip", "mc-clip", "audio"}:
            context.issues.append(
                self._issue(
                    "fcpxml.unsupported_timeline_element",
                    "timeline element was preserved but not executed",
                    MigrationDisposition.PRESERVED,
                    source_path,
                    details={"tag": tag, "xml": self._xml(element)},
                )
            )
            return
        reference_id = element.get("ref") or ""
        reference = context.references.get(reference_id)
        asset = context.asset_elements.get(reference_id)
        if reference is None or asset is None:
            context.issues.append(
                self._issue(
                    "fcpxml.asset_reference_missing",
                    "clip references an unknown asset resource",
                    MigrationDisposition.PRESERVED,
                    source_path,
                    details={"ref": reference_id},
                    severity=MigrationSeverity.ERROR,
                )
            )
            return
        source_start, source_duration, retime = self._source_mapping(
            context,
            element,
            asset,
            timeline_range.duration,
            source_path,
        )
        effects = self._visual_effects(element, state, source_path)
        self._report_unsupported_children(
            context,
            element,
            self._supported_children(),
            source_path,
        )
        has_video = self._has_video(asset, reference) and tag != "audio"
        has_audio = self._has_audio(asset, reference)
        if has_video:
            if Path(reference.uri).suffix.lower() in _IMAGE_SUFFIXES:
                self._video_track(state, lane).items.append(
                    StillImageClip(
                        id=self._item_id(state, "still"),
                        name=element.get("name") or asset.get("name") or reference_id,
                        media_reference_id=reference.id,
                        timeline_range=timeline_range,
                        effects=effects,
                        extensions=self._extensions(element, self._supported_children()),
                    )
                )
            else:
                self._video_track(state, lane).items.append(
                    Clip(
                        id=self._item_id(state, "clip"),
                        name=element.get("name") or asset.get("name") or reference_id,
                        media_reference_id=reference.id,
                        timeline_range=timeline_range,
                        source_range=TimeRange(start=source_start, duration=source_duration),
                        source_audio_enabled=False,
                        retime=retime,
                        effects=effects,
                        extensions=self._extensions(element, self._supported_children()),
                    )
                )
        if has_audio:
            self._audio_track(state, lane).items.append(
                AudioClip(
                    id=self._item_id(state, "audio"),
                    name=element.get("name") or asset.get("name") or reference_id,
                    media_reference_id=reference.id,
                    timeline_range=timeline_range,
                    source_range=TimeRange(start=source_start, duration=source_duration),
                    role=AudioRole.SOURCE,
                    retime=retime,
                    extensions=self._extensions(element, self._supported_children()),
                )
            )
        self._markers(state, element, timeline_range, source_start, retime)
        self._connected_children(context, state, element, source_path)

    def _connected_children(
        self,
        context: _BuildContext,
        state: _SequenceState,
        parent: ET.Element,
        source_path: str,
    ) -> None:
        supported = {
            "asset-clip",
            "audio",
            "caption",
            "clip",
            "gap",
            "mc-clip",
            "ref-clip",
            "sync-clip",
            "title",
        }
        for index, child in enumerate(_children(parent)):
            if _tag(child) not in supported:
                continue
            duration = self._duration(child, state.rate, context.issues, index)
            offset = self._offset(
                child,
                RationalTime.zero(),
                state.rate,
                context.issues,
                index,
            )
            self._timeline_element(
                context,
                state,
                child,
                TimeRange(start=offset, duration=duration),
                source_path=f"{source_path}.{_tag(child)}[{index}]",
            )

    def _source_mapping(
        self,
        context: _BuildContext,
        element: ET.Element,
        asset: ET.Element,
        timeline_duration: RationalTime,
        source_path: str,
    ) -> tuple[RationalTime, RationalTime, Retime]:
        asset_start = _time(asset.get("start"), default=RationalTime.zero())
        clip_start = _time(element.get("start"), default=asset_start)
        source_start = clip_start - asset_start
        if source_start.value < 0:
            raise EngineError(
                ErrorCode.MIGRATION,
                "FCPXML clip starts before its asset origin",
                context={"path": source_path},
            )
        time_map = _child(element, "timeMap")
        ratio = Fraction(1, 1)
        if time_map is not None:
            points = _children(time_map, "timept")
            if len(points) >= 2:
                timeline_delta = _time(points[-1].get("time")) - _time(points[0].get("time"))
                source_delta = _time(points[-1].get("value")) - _time(points[0].get("value"))
                if timeline_delta.value > 0 and source_delta.value > 0:
                    ratio = source_delta.fraction / timeline_delta.fraction
                if len(points) > 2 or any(point.get("interp") == "smooth2" for point in points):
                    context.issues.append(
                        self._issue(
                            "fcpxml.variable_retime_approximated",
                            "variable time map was approximated by its endpoint rate",
                            MigrationDisposition.APPROXIMATED,
                            source_path,
                            details={"point_count": len(points), "rate": str(ratio)},
                        )
                    )
            else:
                context.issues.append(
                    self._issue(
                        "fcpxml.time_map_preserved",
                        "incomplete time map was preserved without execution",
                        MigrationDisposition.PRESERVED,
                        source_path,
                    )
                )
        source_duration = timeline_duration * ratio
        return (
            source_start,
            source_duration,
            Retime(
                rate=RationalRate(
                    numerator=ratio.numerator,
                    denominator=ratio.denominator,
                )
            ),
        )

    def _visual_effects(
        self,
        element: ET.Element,
        state: _SequenceState,
        source_path: str,
    ) -> list[Effect]:
        effects: list[Effect] = []
        transform = _child(element, "adjust-transform")
        if transform is not None:
            position = self._pair(transform.get("position"), (0.0, 0.0))
            scale = self._pair(transform.get("scale"), (100.0, 100.0))
            if position != (0.0, 0.0):
                effects.append(
                    Effect(
                        id=f"{self._item_id(state, 'position')}-effect",
                        kind=EffectKind.POSITION,
                        parameters={
                            "x": position[0] * state.width / 100,
                            "y": -position[1] * state.height / 100,
                        },
                        extensions={"fcpxml:path": source_path},
                    )
                )
            if scale != (100.0, 100.0):
                effects.append(
                    Effect(
                        id=f"{self._item_id(state, 'scale')}-effect",
                        kind=EffectKind.SCALE,
                        parameters={"x": scale[0] / 100, "y": scale[1] / 100},
                    )
                )
            rotation = float(transform.get("rotation") or 0)
            if rotation:
                effects.append(
                    Effect(
                        id=f"{self._item_id(state, 'rotation')}-effect",
                        kind=EffectKind.ROTATION,
                        parameters={"degrees": -rotation},
                    )
                )
        blend = _child(element, "adjust-blend")
        if blend is not None and blend.get("amount") is not None:
            opacity = max(0.0, min(1.0, float(blend.get("amount", "100")) / 100))
            effects.append(
                Effect(
                    id=f"{self._item_id(state, 'opacity')}-effect",
                    kind=EffectKind.OPACITY,
                    parameters={"value": opacity},
                )
            )
        crop = _child(element, "adjust-crop")
        if crop is not None:
            trim = _child(crop, "trim-rect")
            if trim is not None:
                left = float(trim.get("left") or 0)
                right = float(trim.get("right") or 0)
                top = float(trim.get("top") or 0)
                bottom = float(trim.get("bottom") or 0)
                x = max(0, round(state.width * left / 100))
                y = max(0, round(state.height * top / 100))
                width = max(1, round(state.width * (100 - left - right) / 100))
                height = max(1, round(state.height * (100 - top - bottom) / 100))
                effects.append(
                    Effect(
                        id=f"{self._item_id(state, 'crop')}-effect",
                        kind=EffectKind.CROP,
                        parameters={
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "space": "canvas",
                        },
                    )
                )
        return effects

    @staticmethod
    def _pair(value: str | None, default: tuple[float, float]) -> tuple[float, float]:
        if value is None:
            return default
        fields = value.replace(",", " ").split()
        if len(fields) != 2:
            return default
        try:
            return float(fields[0]), float(fields[1])
        except ValueError:
            return default

    def _markers(
        self,
        state: _SequenceState,
        element: ET.Element,
        timeline_range: TimeRange,
        source_start: RationalTime,
        retime: Retime,
    ) -> None:
        xml_source_start = _time(element.get("start"), default=source_start)
        for marker in [*_children(element, "marker"), *_children(element, "chapter-marker")]:
            marker_source = _time(marker.get("start"), default=xml_source_start)
            relative_source = max(RationalTime.zero(), marker_source - xml_source_start)
            marker_time = timeline_range.start + relative_source / retime.rate.fraction
            if marker_time > timeline_range.end:
                continue
            state.markers.append(
                Marker(
                    id=self._item_id(state, "marker"),
                    time=marker_time,
                    name=marker.get("value") or marker.get("name") or "Marker",
                    comment=marker.get("note") or "",
                    extensions={"fcpxml:attributes": dict(marker.attrib)},
                )
            )

    def _caption(
        self,
        state: _SequenceState,
        element: ET.Element,
        timeline_range: TimeRange,
    ) -> None:
        text = element.get("value") or " ".join(
            item.text.strip() for item in element.iter() if item.text and item.text.strip()
        )
        if not text.strip():
            return
        state.caption_items.append(
            CaptionCue(
                id=self._item_id(state, "caption"),
                text=text,
                timeline_range=timeline_range,
                style_id="fcpxml-default",
                speaker=element.get("role"),
                extensions={"fcpxml:attributes": dict(element.attrib)},
            )
        )

    def _apply_transitions(self, context: _BuildContext, state: _SequenceState) -> None:
        for index, element in enumerate(state.transitions):
            offset = _time(element.get("offset"), default=RationalTime.zero())
            duration = _time(element.get("duration"), default=state.rate.frame_duration)
            name = (element.get("name") or "").lower()
            if name and "dissolve" not in name and "crossfade" not in name:
                context.issues.append(
                    self._issue(
                        "fcpxml.transition_preserved",
                        "non-dissolve transition was preserved without approximation",
                        MigrationDisposition.PRESERVED,
                        f"transition[{index}]",
                        details={"name": element.get("name"), "xml": self._xml(element)},
                    )
                )
                continue
            for video_track in state.video_tracks.values():
                self._transition_on_track(video_track, element, offset, duration, index)
            for graphics_track in state.graphics_tracks.values():
                self._transition_on_track(graphics_track, element, offset, duration, index)

    @staticmethod
    def _transition_on_track(
        track: VideoTrack | GraphicsTrack,
        element: ET.Element,
        offset: RationalTime,
        duration: RationalTime,
        index: int,
    ) -> None:
        ordered = sorted(track.items, key=lambda item: item.timeline_range.start)
        left = next(
            (item for item in reversed(ordered) if item.timeline_range.end == offset),
            None,
        )
        right = next(
            (item for item in ordered if item.timeline_range.start == offset),
            None,
        )
        if left is None or right is None:
            return
        track.transitions.append(
            Transition(
                id=f"fcpxml-transition-{index}-{track.id}",
                from_item_id=left.id,
                to_item_id=right.id,
                duration=duration,
                kind=TransitionKind.DISSOLVE,
                extensions={"fcpxml:attributes": dict(element.attrib)},
            )
        )

    @staticmethod
    def _duration(
        element: ET.Element,
        rate: FrameRate,
        issues: list[MigrationIssue],
        index: int,
    ) -> RationalTime:
        value = _time(element.get("duration"), default=rate.frame_duration)
        if value.value <= 0:
            raise EngineError(ErrorCode.MIGRATION, "FCPXML item duration must be positive")
        return FCPXMLAdapterService._frame_time(value, rate, issues, f"item[{index}].duration")

    @staticmethod
    def _offset(
        element: ET.Element,
        default: RationalTime,
        rate: FrameRate,
        issues: list[MigrationIssue],
        index: int,
    ) -> RationalTime:
        value = _time(element.get("offset"), default=default)
        return FCPXMLAdapterService._frame_time(value, rate, issues, f"item[{index}].offset")

    @staticmethod
    def _frame_time(
        value: RationalTime,
        rate: FrameRate,
        issues: list[MigrationIssue],
        path: str,
    ) -> RationalTime:
        frames = rate.time_to_frames(value, rounding=RoundingMode.NEAREST)
        converted = rate.frames_to_time(frames)
        if converted != value:
            issues.append(
                FCPXMLAdapterService._issue(
                    "fcpxml.time_quantized",
                    "time was quantized to the nearest project frame",
                    MigrationDisposition.APPROXIMATED,
                    path,
                    details={
                        "source": value.model_dump(mode="json"),
                        "canonical": converted.model_dump(mode="json"),
                    },
                )
            )
        return converted

    @staticmethod
    def _has_video(asset: ET.Element, reference: MediaReference) -> bool:
        declared = asset.get("hasVideo")
        if reference.offline:
            return declared != "0"
        return any(stream.codec_type == "video" for stream in reference.streams)

    @staticmethod
    def _has_audio(asset: ET.Element, reference: MediaReference) -> bool:
        declared = asset.get("hasAudio")
        if reference.offline:
            return declared != "0"
        return any(stream.codec_type == "audio" for stream in reference.streams)

    @staticmethod
    def _video_track(state: _SequenceState, lane: int) -> VideoTrack:
        if lane not in state.video_tracks:
            state.video_tracks[lane] = VideoTrack(
                id=f"{state.sequence.id}-video-lane-{lane}",
                name="Primary Storyline" if lane == 0 else f"Connected Video Lane {lane}",
            )
        return state.video_tracks[lane]

    @staticmethod
    def _graphics_track(state: _SequenceState, lane: int) -> GraphicsTrack:
        if lane not in state.graphics_tracks:
            state.graphics_tracks[lane] = GraphicsTrack(
                id=f"{state.sequence.id}-graphics-lane-{lane}",
                name=f"Graphics Lane {lane}",
            )
        return state.graphics_tracks[lane]

    @staticmethod
    def _audio_track(state: _SequenceState, lane: int) -> AudioTrack:
        if lane not in state.audio_tracks:
            state.audio_tracks[lane] = AudioTrack(
                id=f"{state.sequence.id}-audio-lane-{lane}",
                name=f"Audio Lane {lane}",
                role=AudioRole.SOURCE,
            )
        return state.audio_tracks[lane]

    @staticmethod
    def _item_id(state: _SequenceState, kind: str) -> str:
        state.item_counter += 1
        return f"{state.sequence.id}-{kind}-{state.item_counter}"

    @staticmethod
    def _supported_children() -> set[str]:
        return {
            "adjust-blend",
            "adjust-crop",
            "adjust-transform",
            "asset-clip",
            "audio",
            "caption",
            "chapter-marker",
            "clip",
            "gap",
            "marker",
            "mc-clip",
            "ref-clip",
            "sync-clip",
            "timeMap",
            "title",
        }

    @staticmethod
    def _report_unsupported_children(
        context: _BuildContext,
        element: ET.Element,
        supported_children: set[str],
        source_path: str,
    ) -> None:
        unsupported = [
            child for child in _children(element) if _tag(child) not in supported_children
        ]
        for child in unsupported:
            context.issues.append(
                FCPXMLAdapterService._issue(
                    "fcpxml.unsupported_child_preserved",
                    "unsupported child element was preserved in extension metadata",
                    MigrationDisposition.PRESERVED,
                    source_path,
                    details={"tag": _tag(child), "xml": FCPXMLAdapterService._xml(child)},
                )
            )

    @staticmethod
    def _extensions(element: ET.Element, supported_children: set[str]) -> dict[str, JsonValue]:
        unsupported = [
            FCPXMLAdapterService._xml(child)
            for child in _children(element)
            if _tag(child) not in supported_children
        ]
        return {
            "fcpxml:tag": _tag(element),
            "fcpxml:attributes": dict(element.attrib),
            "fcpxml:unsupported_children": unsupported,
        }

    @staticmethod
    def _xml(element: ET.Element) -> str:
        return ET.tostring(element, encoding="unicode")[:16_384]

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


class _BuildContext:
    def __init__(
        self,
        *,
        project: Project,
        formats: dict[str, ET.Element],
        asset_elements: dict[str, ET.Element],
        media_elements: dict[str, ET.Element],
        references: dict[str, MediaReference],
        issues: list[MigrationIssue],
    ) -> None:
        self.project = project
        self.formats = formats
        self.asset_elements = asset_elements
        self.media_elements = media_elements
        self.references = references
        self.issues = issues
        self.nested_sequences: dict[str, str] = {}


class _SequenceState:
    def __init__(
        self,
        *,
        sequence: Sequence,
        rate: FrameRate,
        width: int,
        height: int,
    ) -> None:
        self.sequence = sequence
        self.rate = rate
        self.width = width
        self.height = height
        self.video_tracks: dict[int, VideoTrack] = {}
        self.graphics_tracks: dict[int, GraphicsTrack] = {}
        self.audio_tracks: dict[int, AudioTrack] = {}
        self.caption_items: list[CaptionCue] = []
        self.markers: list[Marker] = []
        self.transitions: list[ET.Element] = []
        self.item_counter = 0
