"""Native caption import, sidecar export, and layout service."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Literal

import pysubs2
import webvtt  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from video_engine.config import EngineConfig
from video_engine.core.schema import CaptionCue, CaptionItem, CaptionStyle, CaptionTrack
from video_engine.core.time import RationalTime, TimeRange
from video_engine.errors import EngineError, ErrorCode
from video_engine.render.nodes import (
    ArtifactType,
    CaptionNode,
    CaptionRenderCue,
    CaptionRenderWord,
)

from .ass import write_ass
from .layout import CaptionLayoutResult, validate_caption_layout


class CaptionImportLoss(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str | None = None
    feature: str
    disposition: str


class CaptionImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    track: CaptionTrack
    styles: tuple[CaptionStyle, ...]
    warnings: tuple[str, ...] = ()
    losses: tuple[CaptionImportLoss, ...] = ()


class CaptionExportLoss(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str | None = None
    feature: str
    disposition: str


class CaptionExportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    format: Literal["ass", "srt", "webvtt"]
    losses: tuple[CaptionExportLoss, ...] = ()


def _vtt_time(milliseconds: int) -> str:
    hours, remainder = divmod(max(0, milliseconds), 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def _sidecar_losses(
    cue: CaptionCue,
    track: CaptionTrack,
    suffix: str,
) -> list[CaptionExportLoss]:
    losses: list[CaptionExportLoss] = []
    if suffix == ".srt" and cue.speaker:
        losses.append(
            CaptionExportLoss(
                item_id=cue.id,
                feature="speaker",
                disposition="retained in the canonical project; SRT has no speaker field",
            )
        )
    if cue.words:
        losses.append(
            CaptionExportLoss(
                item_id=cue.id,
                feature="word_timing_and_highlights",
                disposition="retained in the canonical project; sidecar is phrase-timed",
            )
        )
    if (
        cue.style_id is not None
        or cue.style_overrides != cue.style_overrides.__class__()
        or track.default_style_id != "default"
    ):
        losses.append(
            CaptionExportLoss(
                item_id=cue.id,
                feature="typography",
                disposition="retained in the canonical project; format has no native ASS style",
            )
        )
    if cue.position != "bottom" or cue.position_x is not None or cue.position_y is not None:
        losses.append(
            CaptionExportLoss(
                item_id=cue.id,
                feature="position",
                disposition="retained in the canonical project; cue settings are not emitted",
            )
        )
    if cue.language != "und" or track.language != "und":
        losses.append(
            CaptionExportLoss(
                item_id=cue.id,
                feature="language",
                disposition="retained in the canonical project; no sidecar language metadata",
            )
        )
    if cue.extensions or any(word.extensions for word in cue.words):
        losses.append(
            CaptionExportLoss(
                item_id=cue.id,
                feature="extension_metadata",
                disposition="retained in the canonical project only",
            )
        )
    return losses


class CaptionService:
    def __init__(self, config: EngineConfig) -> None:
        self.config = config

    def import_file(
        self,
        path: Path,
        *,
        track_id: str = "captions",
        language: str = "und",
    ) -> CaptionImportResult:
        if path.suffix.lower() not in {".srt", ".ass", ".ssa", ".vtt"}:
            raise EngineError(
                ErrorCode.MIGRATION,
                "caption format is unsupported",
                context={"path": str(path)},
            )
        try:
            source_text = path.read_text(encoding="utf-8")
            subtitles = pysubs2.load(str(path), encoding="utf-8")
        except Exception as exc:
            raise EngineError(
                ErrorCode.MIGRATION,
                "failed to parse caption sidecar",
                context={"path": str(path), "detail": str(exc)},
            ) from exc
        losses: list[CaptionImportLoss] = []
        styles: list[CaptionStyle] = [CaptionStyle(id="default", name="Default")]
        source_style_ids: dict[str, str] = {"Default": "default"}
        style_positions: dict[str, Literal["top", "center", "bottom", "custom"]] = {
            "default": "bottom"
        }
        if path.suffix.lower() in {".ass", ".ssa"}:
            styles = []
            source_style_ids = {}
            style_positions = {}
            for name, source in subtitles.styles.items():
                base_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-") or "default"
                style_id = base_id
                suffix = 2
                while style_id in source_style_ids.values():
                    style_id = f"{base_id}-{suffix}"
                    suffix += 1
                source_style_ids[name] = style_id
                alignment = int(source.alignment)
                position: Literal["top", "center", "bottom", "custom"] = (
                    "top" if alignment >= 7 else "center" if alignment >= 4 else "bottom"
                )
                style_positions[style_id] = position
                losses.append(
                    CaptionImportLoss(
                        item_id=f"style:{style_id}",
                        feature="ass_style_metrics",
                        disposition=(
                            "font size, margins, alignment, alpha, border, scale, spacing, "
                            "and decoration metadata preserved; canonical style is responsive"
                        ),
                    )
                )
                styles.append(
                    CaptionStyle(
                        id=style_id,
                        name=name,
                        font_family=source.fontname or "DejaVu Sans",
                        bold=source.bold,
                        italic=source.italic,
                        primary_color=(
                            f"#{source.primarycolor.r:02X}{source.primarycolor.g:02X}"
                            f"{source.primarycolor.b:02X}"
                        ),
                        outline_color=(
                            f"#{source.outlinecolor.r:02X}{source.outlinecolor.g:02X}"
                            f"{source.outlinecolor.b:02X}"
                        ),
                        background_color=(
                            f"#{source.backcolor.r:02X}{source.backcolor.g:02X}"
                            f"{source.backcolor.b:02X}"
                        ),
                        background_opacity=(
                            round(1 - source.backcolor.a / 255, 6) if source.borderstyle == 3 else 0
                        ),
                        extensions={
                            "legacy_ass_alignment": alignment,
                            "legacy_ass_font_size": source.fontsize,
                            "legacy_ass_margins": [
                                source.marginl,
                                source.marginr,
                                source.marginv,
                            ],
                            "legacy_ass_style": {
                                "primary_alpha": source.primarycolor.a,
                                "secondary_color": [
                                    source.secondarycolor.r,
                                    source.secondarycolor.g,
                                    source.secondarycolor.b,
                                    source.secondarycolor.a,
                                ],
                                "underline": source.underline,
                                "strikeout": source.strikeout,
                                "scale_x": source.scalex,
                                "scale_y": source.scaley,
                                "spacing": source.spacing,
                                "angle": source.angle,
                                "border_style": source.borderstyle,
                                "outline": source.outline,
                                "shadow": source.shadow,
                            },
                        },
                    )
                )
            if not styles:
                styles.append(CaptionStyle(id="default", name="Default"))
                source_style_ids = {"Default": "default"}
                style_positions = {"default": "bottom"}
        style_ids = {style.id for style in styles}
        default_style_id = styles[0].id
        cues: list[CaptionItem] = []
        source_comments: list[dict[str, object]] = []
        vtt_captions = (
            list(webvtt.read(str(path)).captions) if path.suffix.lower() == ".vtt" else []
        )
        vtt_index = 0
        for index, event in enumerate(subtitles, start=1):
            if event.is_comment:
                source_comments.append(
                    {
                        "start_ms": event.start,
                        "end_ms": event.end,
                        "style": event.style,
                        "name": event.name,
                        "text": event.text,
                    }
                )
                losses.append(
                    CaptionImportLoss(
                        item_id=f"comment:{index}",
                        feature="ass_comment",
                        disposition="preserved in caption track extension metadata",
                    )
                )
                continue
            if event.end <= event.start:
                continue
            style_id = source_style_ids.get(event.style, "")
            if style_id not in style_ids:
                style_id = default_style_id
            cue_id = f"{track_id}-{index}"
            unsupported = event.text if re.search(r"(?<!\\)\{[^}]*\}", event.text) else ""
            if unsupported:
                losses.append(
                    CaptionImportLoss(
                        item_id=cue_id,
                        feature="ass_override_tags",
                        disposition="preserved in cue extension metadata; not interpreted",
                    )
                )
            cue_text = event.plaintext
            speaker = event.name or None
            if vtt_index < len(vtt_captions):
                vtt_text = vtt_captions[vtt_index].raw_text
                voice_match = re.fullmatch(
                    r"<v(?:\.[^ ]+)?\s+([^>]+)>(.*)</v>",
                    vtt_text,
                    flags=re.DOTALL,
                )
                if voice_match:
                    speaker = html.unescape(voice_match.group(1)).strip() or None
                    cue_text = html.unescape(voice_match.group(2))
                vtt_index += 1
            if "; VideoEngine Escapes: fullwidth-v1" in source_text:
                cue_text = (
                    cue_text.replace("\uff3c", "\\").replace("\uff5b", "{").replace("\uff5d", "}")
                )
            cues.append(
                CaptionCue(
                    id=cue_id,
                    text=cue_text,
                    timeline_range=TimeRange(
                        start=RationalTime(value=event.start, timescale=1000),
                        duration=RationalTime(value=event.end - event.start, timescale=1000),
                    ),
                    speaker=speaker,
                    language=language,
                    style_id=style_id,
                    position=style_positions.get(style_id, "bottom"),
                    extensions={
                        "source_format": path.suffix.lower().lstrip("."),
                        "source_effect": event.effect,
                        "source_layer": event.layer,
                        "source_margins": [event.marginl, event.marginr, event.marginv],
                        "unsupported_override_tags": unsupported,
                    },
                )
            )
        return CaptionImportResult(
            track=CaptionTrack(
                id=track_id,
                language=language,
                default_style_id=default_style_id,
                items=cues,
                extensions={
                    "source_script_info": {
                        str(key): str(value) for key, value in subtitles.info.items()
                    },
                    "source_comments": source_comments,
                },
            ),
            styles=tuple(styles),
            warnings=(),
            losses=tuple(losses),
        )

    def export(
        self,
        track: CaptionTrack,
        styles: list[CaptionStyle],
        path: Path,
        *,
        width: int = 1920,
        height: int = 1080,
    ) -> CaptionExportResult:
        suffix = path.suffix.lower()
        losses: list[CaptionExportLoss] = []
        if suffix == ".ssa":
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "SSA v4 export is not supported; use an .ass output path",
                context={"path": str(path)},
            )
        if suffix == ".ass":
            cues = tuple(
                CaptionRenderCue(
                    text=item.text,
                    timeline_range=item.timeline_range,
                    words=tuple(
                        CaptionRenderWord(
                            text=word.text,
                            timeline_range=word.range,
                            highlight=word.highlight,
                            style_id=word.style_id,
                        )
                        for word in item.words
                    ),
                    style_id=item.style_id or track.default_style_id,
                    position=item.position,
                    speaker=item.speaker,
                    language=item.language,
                    position_x=item.position_x,
                    position_y=item.position_y,
                    style_overrides=item.style_overrides,
                )
                for item in track.items
                if isinstance(item, CaptionCue) and item.enabled and not item.suppressed
            )
            node = CaptionNode(
                id="caption-export",
                inputs=("sidecar-source",),
                artifact_type=ArtifactType.VIDEO,
                cues=cues,
                width=width,
                height=height,
                styles=tuple(styles),
                default_style_id=track.default_style_id,
            )
            write_ass(node, path)
            for item in track.items:
                if not isinstance(item, CaptionCue):
                    continue
                if any(character in item.text for character in "{}\\"):
                    losses.append(
                        CaptionExportLoss(
                            item_id=item.id,
                            feature="ass_reserved_characters",
                            disposition=(
                                "reversible VideoEngine fullwidth escapes emitted because ASS "
                                "has no literal brace/backslash escape"
                            ),
                        )
                    )
                if item.language != "und" or track.language != "und":
                    losses.append(
                        CaptionExportLoss(
                            item_id=item.id,
                            feature="language",
                            disposition="retained in the canonical project, absent from ASS event",
                        )
                    )
                if any(word.confidence is not None for word in item.words):
                    losses.append(
                        CaptionExportLoss(
                            item_id=item.id,
                            feature="word_confidence",
                            disposition="retained in the canonical project, absent from ASS",
                        )
                    )
            return CaptionExportResult(path=path, format="ass", losses=tuple(losses))
        if suffix not in {".srt", ".vtt"}:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "caption export format is unsupported",
                context={"path": str(path)},
            )
        output = pysubs2.SSAFile()
        vtt_output: list[webvtt.Caption] = []
        for item in track.items:
            if not isinstance(item, CaptionCue) or not item.enabled or item.suppressed:
                continue
            start_ms = round(item.timeline_range.start.fraction * 1000)
            end_ms = round(item.timeline_range.end.fraction * 1000)
            if suffix == ".vtt":
                text = html.escape(item.text, quote=False)
                if item.speaker:
                    text = f"<v {html.escape(item.speaker)}>{text}</v>"
                vtt_output.append(
                    webvtt.Caption(
                        start=_vtt_time(start_ms),
                        end=_vtt_time(end_ms),
                        text=text,
                    )
                )
            else:
                output.append(
                    pysubs2.SSAEvent(
                        start=start_ms,
                        end=end_ms,
                        text=item.text.replace("\n", r"\N"),
                    )
                )
            losses.extend(_sidecar_losses(item, track, suffix))
        path.parent.mkdir(parents=True, exist_ok=True)
        if suffix == ".vtt":
            webvtt.WebVTT(captions=vtt_output).save(str(path))
        else:
            output.save(str(path), format_="srt")
        return CaptionExportResult(
            path=path,
            format="srt" if suffix == ".srt" else "webvtt",
            losses=tuple(losses),
        )

    def validate_layout(
        self,
        track: CaptionTrack,
        styles: list[CaptionStyle],
        *,
        width: int,
        height: int,
    ) -> CaptionLayoutResult:
        return validate_caption_layout(
            track, styles, width=width, height=height, config=self.config
        )
