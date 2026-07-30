"""ASS serialization for native canonical caption tracks."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from video_engine.core.schema import CaptionStyle, CaptionStyleOverride
from video_engine.core.time import RationalTime
from video_engine.errors import EngineError, ErrorCode
from video_engine.render.nodes import CaptionNode, CaptionRenderCue


def _ass_time(value: RationalTime, *, boundary: str) -> str:
    scaled = value.fraction * 100
    if boundary == "start":
        centiseconds = max(0, scaled.numerator // scaled.denominator)
    else:
        centiseconds = max(0, -(-scaled.numerator // scaled.denominator))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    seconds, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centis:02d}"


def _ass_color(value: str, *, opacity: float = 1, override: bool = False) -> str:
    red, green, blue = value[1:3], value[3:5], value[5:7]
    alpha = round(255 * (1 - opacity))
    suffix = "&" if override else ""
    return f"&H{alpha:02X}{blue}{green}{red}{suffix}"


def escape_ass_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\\", "\uff3c")
    normalized = normalized.replace("{", "\uff5b").replace("}", "\uff5d")
    return normalized.replace("\n", r"\N")


def _style_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "Default"
    if normalized != value:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
        normalized = f"{normalized}-{digest}"
    return normalized


def _ass_field(value: str) -> str:
    return " ".join(value.replace(",", " ").splitlines()).strip()


def _ass_tag_value(value: str) -> str:
    return _ass_field(value).replace("\\", "").replace("{", "").replace("}", "")


def _font_size(style: CaptionStyle, width: int, height: int) -> int:
    reference = min(width, height)
    return max(
        style.min_font_size_px,
        min(style.max_font_size_px, round(reference * style.font_size_ratio)),
    )


def _style_line(style: CaptionStyle, width: int, height: int) -> str:
    reference = min(width, height)
    font_size = _font_size(style, width, height)
    outline = max(0, round(reference * style.outline_ratio, 2))
    shadow = max(0, round(reference * style.shadow_ratio, 2))
    margin_x = round(width * style.margin_x_ratio)
    margin_y = round(height * style.margin_y_ratio)
    border_style = 3 if style.background_opacity > 0 else 1
    return (
        f"Style: {_style_name(style.id)},{_ass_field(style.font_family)},{font_size},"
        f"{_ass_color(style.primary_color)},{_ass_color(style.highlight_color)},"
        f"{_ass_color(style.outline_color)},"
        f"{_ass_color(style.background_color, opacity=style.background_opacity)},"
        f"{-1 if style.bold else 0},{-1 if style.italic else 0},0,0,100,100,0,0,"
        f"{border_style},{outline},{shadow},2,{margin_x},{margin_x},{margin_y},1"
    )


def _override_tags(overrides: CaptionStyleOverride) -> str:
    tags: list[str] = []
    if overrides.font_size_px is not None:
        tags.append(f"\\fs{overrides.font_size_px}")
    if overrides.bold is not None:
        tags.append(f"\\b{1 if overrides.bold else 0}")
    if overrides.italic is not None:
        tags.append(f"\\i{1 if overrides.italic else 0}")
    for value, tag in (
        (overrides.primary_color, "1c"),
        (overrides.outline_color, "3c"),
    ):
        if value is not None:
            tags.append(f"\\{tag}{_ass_color(value, override=True)}")
    return "{" + "".join(tags) + "}" if tags else ""


def _cue_text(
    cue: CaptionRenderCue,
    styles: dict[str, CaptionStyle],
    width: int,
    height: int,
) -> str:
    if not cue.words:
        return escape_ass_text(cue.text)
    parts: list[str] = []
    cursor = cue.timeline_range.start
    text_cursor = 0
    aligned = True
    for index, word in enumerate(cue.words):
        gap = max(0, round((word.timeline_range.start - cursor).fraction * 100))
        if gap:
            parts.append(f"{{\\k{gap}}}")
        centiseconds = max(1, round(word.timeline_range.duration.fraction * 100))
        word_style_id = word.style_id or cue.style_id
        if word_style_id not in styles:
            raise EngineError(
                ErrorCode.INVALID_PROJECT,
                "caption word references a missing render style",
                context={"style_id": word_style_id},
            )
        tags = [f"\\kf{centiseconds}"]
        word_style = styles[word_style_id]
        uses_cue_style = word.style_id is None or word.style_id == cue.style_id
        font_size = (
            cue.style_overrides.font_size_px
            if uses_cue_style and cue.style_overrides.font_size_px is not None
            else _font_size(word_style, width, height)
        )
        bold = (
            cue.style_overrides.bold
            if uses_cue_style and cue.style_overrides.bold is not None
            else word_style.bold
        )
        italic = (
            cue.style_overrides.italic
            if uses_cue_style and cue.style_overrides.italic is not None
            else word_style.italic
        )
        primary_color = (
            cue.style_overrides.primary_color
            if uses_cue_style and cue.style_overrides.primary_color is not None
            else word_style.primary_color
        )
        outline_color = (
            cue.style_overrides.outline_color
            if uses_cue_style and cue.style_overrides.outline_color is not None
            else word_style.outline_color
        )
        tags.extend(
            [
                f"\\fn{_ass_tag_value(word_style.font_family)}",
                f"\\fs{font_size}",
                f"\\b{1 if bold else 0}",
                f"\\i{1 if italic else 0}",
                f"\\3c{_ass_color(outline_color, override=True)}",
                f"\\1c{_ass_color(primary_color, override=True)}",
            ]
        )
        if word.highlight:
            tags[-1] = f"\\1c{_ass_color(word_style.highlight_color, override=True)}"
        word_index = cue.text.find(word.text, text_cursor)
        if word_index < 0:
            aligned = False
            separator = "" if index == 0 else " "
        else:
            separator = cue.text[text_cursor:word_index]
            text_cursor = word_index + len(word.text)
        parts.append(
            escape_ass_text(separator) + "{" + "".join(tags) + "}" + escape_ass_text(word.text)
        )
        cursor = word.timeline_range.end
    if aligned:
        parts.append(escape_ass_text(cue.text[text_cursor:]))
    return "".join(parts)


def write_ass(node: CaptionNode, path: Path) -> None:
    styles = {style.id: style for style in node.styles}
    if not styles:
        default = CaptionStyle(id="default", name="Default")
        styles[default.id] = default
    if node.default_style_id not in styles:
        raise EngineError(
            ErrorCode.INVALID_PROJECT,
            "caption node default style is missing",
            context={"style_id": node.default_style_id},
        )
    style_values = node.styles or tuple(styles.values())
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {node.width}",
        f"PlayResY: {node.height}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "; VideoEngine Escapes: fullwidth-v1",
        "",
        "[V4+ Styles]",
        (
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
            "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,"
            "ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,"
            "MarginR,MarginV,Encoding"
        ),
        *(_style_line(style, node.width, node.height) for style in style_values),
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]
    alignments = {"top": 8, "center": 5, "bottom": 2, "custom": 2}
    for cue in node.cues:
        style_id = cue.style_id or node.default_style_id
        if style_id not in styles:
            raise EngineError(
                ErrorCode.INVALID_PROJECT,
                "caption cue references a missing render style",
                context={"style_id": style_id},
            )
        tags = [f"\\an{alignments[cue.position]}"]
        if cue.position == "custom":
            if cue.position_x is None or cue.position_y is None:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "custom caption position is incomplete",
                )
            tags.append(
                f"\\pos({round(cue.position_x * node.width)},{round(cue.position_y * node.height)})"
            )
        text = "{" + "".join(tags) + "}" + _override_tags(cue.style_overrides)
        text += _cue_text(cue, styles, node.width, node.height)
        lines.append(
            "Dialogue: 0,"
            f"{_ass_time(cue.timeline_range.start, boundary='start')},"
            f"{_ass_time(cue.timeline_range.end, boundary='end')},"
            f"{_style_name(style_id)},{_ass_field(cue.speaker or '')},0,0,0,,{text}"
        )
    dialogue = "\n".join(line for line in lines if line.startswith("Dialogue:"))
    if r"\\N" in dialogue:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "ASS dialogue contains a double-escaped hard line break",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
