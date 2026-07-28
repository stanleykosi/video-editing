"""Caption measurement, fitting, safe-area, reading-speed, and collision checks."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from PIL import ImageFont
from pydantic import BaseModel, ConfigDict, Field

from video_engine.config import EngineConfig
from video_engine.core.schema import CaptionCue, CaptionStyle, CaptionTrack
from video_engine.errors import EngineError
from video_engine.process import CommandRunner


class CaptionLayoutIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    severity: Literal["error", "warning"]
    cue_id: str
    message: str
    context: dict[str, object] = Field(default_factory=dict)


class CaptionLayoutResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issues: tuple[CaptionLayoutIssue, ...]
    resolved_fonts: dict[str, str]
    fitted_font_sizes: dict[str, int]

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


class FontResolver:
    def __init__(self, config: EngineConfig, runner: CommandRunner | None = None) -> None:
        self.config = config
        self.runner = runner or CommandRunner()

    def resolve(self, style: CaptionStyle) -> Path | None:
        for family in [style.font_family, *style.fallback_families]:
            try:
                result = self.runner.run(
                    ["fc-match", "-f", "%{family[0]}|%{file}\n", family],
                    check=False,
                )
            except EngineError:
                return None
            line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
            matched_family, separator, path_value = line.partition("|")
            candidate = Path(path_value) if separator else None
            family_matches = family.casefold() in {
                name.strip().casefold() for name in matched_family.split(",")
            }
            generic_family = family.casefold() in {"sans", "serif", "monospace"}
            if (
                result.return_code == 0
                and candidate is not None
                and candidate.is_file()
                and (family_matches or generic_family)
            ):
                return candidate
        return None


def _wrapped_lines(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current: list[str] = []
        for word in paragraph.split():
            candidate = " ".join([*current, word])
            if current and font.getlength(candidate) > max_width:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        lines.append(" ".join(current))
    return lines


def validate_caption_layout(
    track: CaptionTrack,
    styles: list[CaptionStyle],
    *,
    width: int,
    height: int,
    config: EngineConfig,
) -> CaptionLayoutResult:
    style_map = {style.id: style for style in styles}
    resolver = FontResolver(config)
    resolved: dict[str, str] = {}
    sizes: dict[str, int] = {}
    issues: list[CaptionLayoutIssue] = []
    for style in styles:
        font_path = resolver.resolve(style)
        if font_path is None:
            issues.append(
                CaptionLayoutIssue(
                    code="caption.font_missing",
                    severity="error",
                    cue_id="",
                    message=f"no installed font resolved for style {style.id!r}",
                )
            )
        else:
            resolved[style.id] = str(font_path)
    for item in track.items:
        if not isinstance(item, CaptionCue) or not item.enabled or item.suppressed:
            continue
        style_id = item.style_id or track.default_style_id
        resolved_style = style_map.get(style_id)
        font_path_value = resolved.get(style_id)
        if resolved_style is None or font_path_value is None:
            issues.append(
                CaptionLayoutIssue(
                    code="caption.style_missing",
                    severity="error",
                    cue_id=item.id,
                    message=f"caption style {style_id!r} is unavailable",
                )
            )
            continue
        style = resolved_style
        max_width = round(width * (1 - 2 * style.margin_x_ratio))
        requested = item.style_overrides.font_size_px or max(
            style.min_font_size_px,
            min(
                style.max_font_size_px,
                round(min(width, height) * style.font_size_ratio),
            ),
        )
        fitted = requested
        lines: list[str] = []
        while fitted >= style.min_font_size_px:
            font = ImageFont.truetype(font_path_value, fitted)
            lines = _wrapped_lines(item.text, font, max_width)
            if len(lines) <= style.max_lines and all(
                len(line) <= style.max_chars_per_line and font.getlength(line) <= max_width
                for line in lines
            ):
                break
            fitted -= 1
        if fitted < style.min_font_size_px:
            issues.append(
                CaptionLayoutIssue(
                    code="caption.fit_failed",
                    severity="error",
                    cue_id=item.id,
                    message="caption cannot fit within line and safe-area limits",
                    context={"lines": lines, "max_width": max_width},
                )
            )
            fitted = style.min_font_size_px
        sizes[item.id] = fitted
        duration = float(item.timeline_range.duration.fraction)
        characters = len("".join(item.text.split()))
        cps = characters / duration if duration else float("inf")
        if cps > style.max_reading_speed_cps:
            issues.append(
                CaptionLayoutIssue(
                    code="caption.reading_speed",
                    severity="warning",
                    cue_id=item.id,
                    message="caption exceeds the configured reading speed",
                    context={"characters_per_second": round(cps, 3)},
                )
            )
        line_height = fitted * style.line_spacing
        fitted_font = ImageFont.truetype(font_path_value, fitted)
        box_width = min(max_width, max((fitted_font.getlength(line) for line in lines), default=0))
        box_height = max(1, len(lines)) * line_height
        center_x = (item.position_x if item.position_x is not None else 0.5) * width
        if item.position == "top":
            center_x = width / 2
            center_y = style.margin_y_ratio * height + box_height / 2
        elif item.position == "center":
            center_x = width / 2
            center_y = height / 2
        elif item.position == "custom":
            anchor_y = (item.position_y if item.position_y is not None else 0.5) * height
            center_y = anchor_y - box_height / 2
        else:
            center_x = width / 2
            center_y = height - style.margin_y_ratio * height - box_height / 2
        caption_box = (
            center_x - box_width / 2,
            center_y - box_height / 2,
            center_x + box_width / 2,
            center_y + box_height / 2,
        )
        safe_x = style.margin_x_ratio * width
        safe_y = style.margin_y_ratio * height
        if (
            caption_box[0] < safe_x
            or caption_box[2] > width - safe_x
            or caption_box[1] < safe_y
            or caption_box[3] > height - safe_y
        ):
            issues.append(
                CaptionLayoutIssue(
                    code="caption.safe_area",
                    severity="error",
                    cue_id=item.id,
                    message="caption extends outside the configured title-safe area",
                    context={"box": list(caption_box)},
                )
            )
        for region in track.collision_regions:
            if not region.timeline_range.overlaps(item.timeline_range):
                continue
            region_box = (
                region.x * width,
                region.y * height,
                (region.x + region.width) * width,
                (region.y + region.height) * height,
            )
            if (
                caption_box[0] < region_box[2]
                and region_box[0] < caption_box[2]
                and caption_box[1] < region_box[3]
                and region_box[1] < caption_box[3]
            ):
                issues.append(
                    CaptionLayoutIssue(
                        code="caption.collision",
                        severity="error",
                        cue_id=item.id,
                        message=f"caption overlaps {region.kind} exclusion region",
                        context={"region_id": region.id},
                    )
                )
    return CaptionLayoutResult(
        issues=tuple(issues), resolved_fonts=resolved, fitted_font_sizes=sizes
    )
