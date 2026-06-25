"""Render a knowledge-driven faceless video from `edit_decision_list.json`.

This renderer turns the rich timeline into a finished vertical edit. It creates
base visual segments, applies color/motion treatment, muxes voiceover, then
renders a final knowledge-driven overlay pass for kinetic captions, emphasis
text, glow/highlight wipes, diagram callouts, transitions, and progress accents.
Subtitles/effects are applied after the base visual composition.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import shlex
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from asset_manifest import load_manifest
from caption_styles import srt_force_style
from sfx_renderer import mix_sfx_into_video


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


def run(cmd: list[str]) -> None:
    print(f"  $ {' '.join(shlex.quote(c) for c in cmd[:8])}{' ...' if len(cmd) > 8 else ''}")
    subprocess.run(cmd, check=True)


def valid_video(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and "video" in result.stdout


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf" if bold else "/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu[wdth,wght].ttf" if bold else "/usr/share/fonts/truetype/ubuntu/Ubuntu[wdth,wght].ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease_out_cubic(value: float) -> float:
    value = clamp(value)
    return 1 - pow(1 - value, 3)


def ease_in_out(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


def hex_to_rgba(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        return (56, 189, 248, alpha)
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def scaled_font_size(width: int, ratio: float, minimum: int, maximum: int, scale: float = 1.0) -> int:
    return int(max(minimum, min(maximum, width * ratio * scale)))


def fitted_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    base_size: int,
    min_size: int,
    bold: bool = True,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    size = max(min_size, base_size)
    while size > min_size:
        font = load_font(size, bold=bold)
        if text_size(draw, text, font)[0] <= max_width:
            return font
        size -= 2
    return load_font(min_size, bold=bold)


def wrap_words(
    draw: ImageDraw.ImageDraw,
    words: list[str],
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: int = 2,
) -> list[list[str]]:
    lines: list[list[str]] = []
    current: list[str] = []
    for word in words:
        candidate = current + [word]
        if current and text_size(draw, " ".join(candidate), font)[0] > max_width:
            lines.append(current)
            current = [word]
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) <= max_lines:
        return lines
    merged = lines[: max_lines - 1]
    merged.append([word for line in lines[max_lines - 1 :] for word in line])
    return merged


def active_beat(beats: list[dict[str, Any]], t: float) -> dict[str, Any] | None:
    for beat in beats:
        start = float(beat.get("start", 0))
        end = float(beat.get("end", start))
        if start <= t < end or (math.isclose(t, end) and beat is beats[-1]):
            return beat
    return None


def active_cue(cues: list[dict[str, Any]], t: float) -> dict[str, Any] | None:
    for cue in cues:
        if float(cue.get("start", 0)) <= t < float(cue.get("end", 0)):
            return cue
    return None


def layer_by_type(beat: dict[str, Any], layer_type: str) -> dict[str, Any] | None:
    for layer in beat.get("layers", []):
        if layer.get("type") == layer_type:
            return layer
    return None


def stock_montage_mode(timeline: dict[str, Any]) -> bool:
    project = timeline.get("project", {})
    return bool(
        project.get("stock_montage_only")
        or project.get("render_profile") == "premium_stock_montage"
    )


def draw_glow_text(
    image: Image.Image,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    glow: tuple[int, int, int, int],
    blur: int = 18,
) -> None:
    glow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.text(xy, text, font=font, fill=glow)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(blur))
    image.alpha_composite(glow_layer)
    ImageDraw.Draw(image).text(xy, text, font=font, fill=fill)


def text_sprite(text: str, font: ImageFont.ImageFont, fill: tuple[int, int, int, int], pad: int = 32) -> Image.Image:
    probe = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    tw, th = text_size(draw, text, font)
    image = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((pad, pad), text, font=font, fill=fill)
    return image


def fit_text_font(overlay: Image.Image, text: str, width_ratio: float, base_ratio: float) -> ImageFont.ImageFont:
    draw = ImageDraw.Draw(overlay)
    width, _ = overlay.size
    return fitted_font(
        draw,
        text,
        int(width * width_ratio),
        scaled_font_size(width, base_ratio, 28, 92),
        scaled_font_size(width, 0.04, 20, 44),
        bold=True,
    )


def emphasis_box_position(overlay: Image.Image, text: str, font: ImageFont.ImageFont, y_ratio: float = 0.135) -> tuple[int, int, int, int, int, int]:
    draw = ImageDraw.Draw(overlay)
    width, height = overlay.size
    tw, th = text_size(draw, text, font)
    x = (width - tw) // 2
    y = int(height * y_ratio)
    pad_x = max(18, int(width * 0.032))
    pad_y = max(12, int(height * 0.012))
    return x, y, tw, th, pad_x, pad_y


def draw_progress_and_frame(
    overlay: Image.Image,
    beat: dict[str, Any],
    t: float,
    duration: float,
    accent: str,
) -> None:
    draw = ImageDraw.Draw(overlay)
    width, height = overlay.size
    progress = clamp(t / max(duration, 0.1))
    accent_rgba = hex_to_rgba(accent, 230)
    draw.rectangle((0, 0, width, 8), fill=(255, 255, 255, 44))
    draw.rectangle((0, 0, int(width * progress), 8), fill=accent_rgba)
    beat_start = float(beat.get("start", 0))
    beat_end = float(beat.get("end", beat_start + 1))
    local = clamp((t - beat_start) / max(beat_end - beat_start, 0.1))
    side_alpha = int(80 * (1 - abs(local - 0.5) * 1.4))
    draw.rounded_rectangle((26, 58, 38, height - 58), radius=8, fill=hex_to_rgba(accent, max(20, side_alpha)))


def draw_visual_overlay(overlay: Image.Image, beat: dict[str, Any], t: float, style: dict[str, Any]) -> None:
    layer = layer_by_type(beat, "visual_motion_overlay")
    if not layer:
        return
    start = float(layer.get("start", beat.get("start", 0)))
    end = float(layer.get("end", beat.get("end", start)))
    if not (start <= t <= end):
        return
    draw = ImageDraw.Draw(overlay)
    width, height = overlay.size
    progress = ease_in_out((t - start) / max(end - start, 0.1))
    accent = hex_to_rgba(layer.get("accent_color") or style.get("accent_color", "#38bdf8"), int(160 + 70 * math.sin(progress * math.pi)))
    effect = layer.get("effect", "callout_label_pop")
    cx, cy = width // 2, int(height * 0.42)

    if effect == "corner_pulse":
        box_w, box_h = int(width * 0.45), int(height * 0.22)
        x1, y1 = cx - box_w // 2, cy - box_h // 2
        x2, y2 = cx + box_w // 2, cy + box_h // 2
        draw.rounded_rectangle((x1, y1, x2, y2), radius=18, outline=(255, 255, 255, 80), width=4)
        pulse = int(26 + 24 * abs(math.sin(progress * math.pi * 4)))
        for x, y in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
            draw.ellipse((x - pulse, y - pulse, x + pulse, y + pulse), outline=(251, 113, 133, 210), width=7)
    elif effect == "arrow_trace":
        if str(beat.get("purpose", "")).lower() == "payoff":
            cy = int(height * 0.355)
            box = (int(width * 0.26), int(height * 0.18), int(width * 0.74), int(height * 0.61))
            draw.arc(box, start=210, end=330, fill=hex_to_rgba(layer.get("accent_color") or "#38bdf8", 140), width=5)
            draw.arc(box, start=30, end=150, fill=hex_to_rgba("#22c55e", 150), width=6)
            for idx in range(6):
                angle = (progress * 360 + idx * 60) * math.pi / 180
                x = cx + int(math.cos(angle) * width * 0.2)
                y = cy + int(math.sin(angle) * height * 0.15)
                draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=hex_to_rgba(style.get("accent_color", "#38bdf8"), 130))
            return
        box = (int(width * 0.22), int(height * 0.24), int(width * 0.78), int(height * 0.62))
        draw.ellipse(box, outline=accent, width=7)
        for idx in range(6):
            angle = (progress * 360 + idx * 60) * math.pi / 180
            x = cx + int(math.cos(angle) * width * 0.25)
            y = cy + int(math.sin(angle) * height * 0.16)
            draw.line((cx, cy, x, y), fill=accent, width=4)
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=accent)
    elif effect == "outline_trace":
        pad_x, pad_y = int(width * 0.19), int(height * 0.2)
        draw.rounded_rectangle((pad_x, pad_y, width - pad_x, height - pad_y), radius=90, outline=accent, width=7)
        sweep = int((width - pad_x * 2) * progress)
        draw.line((pad_x, height - pad_y + 18, pad_x + sweep, height - pad_y + 18), fill=accent, width=8)
    else:
        label = str(layer.get("label") or "").upper()[:28]
        if not label:
            return
        font = load_font(42, bold=True)
        tw, th = text_size(draw, label, font)
        x = (width - tw) // 2
        y = int(height * 0.2)
        alpha = int(220 * min(progress * 3, 1, (1 - progress) * 3 if progress > 0.66 else 1))
        draw.rounded_rectangle((x - 28, y - 18, x + tw + 28, y + th + 26), radius=24, fill=(5, 13, 28, max(0, alpha - 35)), outline=hex_to_rgba(style.get("accent_color", "#38bdf8"), alpha), width=3)
        draw.text((x, y), label, font=font, fill=(255, 255, 255, alpha))


def draw_capcut_highlight_wipe(overlay: Image.Image, layer: dict[str, Any], text: str, progress: float, alpha: int, style: dict[str, Any]) -> None:
    draw = ImageDraw.Draw(overlay)
    width, height = overlay.size
    font = fit_text_font(overlay, text, 0.82, 0.078)
    x, y, tw, th, pad_x, pad_y = emphasis_box_position(overlay, text, font, 0.13)
    accent = layer.get("accent_color") or style.get("secondary_accent", "#facc15")
    bg = (2, 6, 16, max(0, alpha - 85))
    draw.rounded_rectangle((x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y + 8), radius=18, fill=bg)
    draw.text((x, y), text, font=font, fill=(255, 255, 255, alpha))
    sweep = ease_in_out(progress)
    bar_x1 = x - pad_x
    bar_x2 = int(bar_x1 + (tw + pad_x * 2) * sweep)
    if bar_x2 > bar_x1:
        mask = Image.new("L", overlay.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((bar_x1, y - pad_y, bar_x2, y + th + pad_y + 8), radius=18, fill=int(alpha))
        highlight = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
        hdraw = ImageDraw.Draw(highlight)
        hdraw.rounded_rectangle((bar_x1, y - pad_y, bar_x2, y + th + pad_y + 8), radius=18, fill=hex_to_rgba(accent, int(alpha * 0.92)))
        hdraw.text((x, y), text, font=font, fill=(4, 10, 20, alpha))
        overlay.alpha_composite(Image.composite(highlight, Image.new("RGBA", overlay.size, (0, 0, 0, 0)), mask))


def draw_staggered_glitch_reveal(overlay: Image.Image, layer: dict[str, Any], text: str, progress: float, alpha: int, style: dict[str, Any]) -> None:
    draw = ImageDraw.Draw(overlay)
    width, height = overlay.size
    words = text.split() or [text]
    base_font = fit_text_font(overlay, text, 0.84, 0.075)
    space = text_size(draw, " ", base_font)[0]
    word_sizes = [text_size(draw, word, base_font) for word in words]
    total_w = sum(w for w, _ in word_sizes) + space * max(0, len(words) - 1)
    cursor = (width - total_w) // 2
    y = int(height * 0.13)
    accent = style.get("danger_accent", "#fb7185")
    final_accent = layer.get("accent_color") or style.get("accent_color", "#38bdf8")
    for idx, (word, (ww, _)) in enumerate(zip(words, word_sizes)):
        local = clamp((progress - idx * 0.13) / 0.48)
        word_alpha = int(alpha * ease_out_cubic(local))
        if word_alpha <= 0:
            cursor += ww + space
            continue
        jitter = int((1 - local) * max(5, width * 0.012))
        pre_color = hex_to_rgba(accent, int(word_alpha * (1 - min(local, 0.8) * 0.55)))
        final_color = (255, 255, 255, word_alpha)
        blur_layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(blur_layer)
        bdraw.text((cursor - jitter, y), word, font=base_font, fill=pre_color)
        bdraw.text((cursor + jitter, y + max(1, jitter // 2)), word, font=base_font, fill=hex_to_rgba(final_accent, int(word_alpha * 0.45)))
        blur_layer = blur_layer.filter(ImageFilter.GaussianBlur(max(1, int((1 - local) * 8))))
        overlay.alpha_composite(blur_layer)
        draw.text((cursor, y), word, font=base_font, fill=final_color)
        cursor += ww + space


def draw_axis_stretch_word(overlay: Image.Image, layer: dict[str, Any], text: str, progress: float, alpha: int, style: dict[str, Any]) -> None:
    width, height = overlay.size
    font = fit_text_font(overlay, text, 0.78, 0.08)
    accent = layer.get("accent_color") or style.get("secondary_accent", "#facc15")
    peak = math.sin(math.pi * clamp(progress / 0.78))
    scale_y = 1.0 + 0.34 * peak
    scale_x = 1.0 - 0.08 * peak
    sprite = text_sprite(text, font, (255, 255, 255, alpha), pad=max(22, width // 40))
    glow = text_sprite(text, font, hex_to_rgba(accent, int(alpha * 0.55)), pad=max(22, width // 40)).filter(ImageFilter.GaussianBlur(max(5, width // 110)))
    new_size = (max(1, int(sprite.width * scale_x)), max(1, int(sprite.height * scale_y)))
    sprite = sprite.resize(new_size, Image.Resampling.BICUBIC)
    glow = glow.resize(new_size, Image.Resampling.BICUBIC)
    x = (width - new_size[0]) // 2
    y = int(height * 0.125) - int((scale_y - 1) * sprite.height * 0.25)
    overlay.alpha_composite(glow, (x, y))
    overlay.alpha_composite(sprite, (x, y))


def draw_font_shift_loop(overlay: Image.Image, layer: dict[str, Any], text: str, progress: float, alpha: int, style: dict[str, Any]) -> None:
    draw = ImageDraw.Draw(overlay)
    width, height = overlay.size
    size = scaled_font_size(width, 0.076, 30, 88)
    fonts = [
        load_font(size, bold=True),
        load_font(max(24, int(size * 0.92)), bold=False),
        load_font(max(24, int(size * 1.04)), bold=True),
    ]
    font = fonts[int(progress * 16) % len(fonts)] if progress < 0.68 else fonts[0]
    max_width = int(width * 0.82)
    if text_size(draw, text, font)[0] > max_width:
        font = fitted_font(draw, text, max_width, size, scaled_font_size(width, 0.04, 20, 42), bold=True)
    x, y, tw, th, pad_x, pad_y = emphasis_box_position(overlay, text, font, 0.13)
    accent = style.get("secondary_accent", "#facc15") if int(progress * 18) % 2 else style.get("accent_color", "#38bdf8")
    draw.rounded_rectangle((x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y + 8), radius=20, fill=(3, 7, 18, max(0, alpha - 80)))
    draw.text((x + 3, y), text, font=font, fill=hex_to_rgba(accent, int(alpha * 0.45)))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, alpha))


def draw_apple_slide_up_text(overlay: Image.Image, layer: dict[str, Any], text: str, progress: float, alpha: int, style: dict[str, Any]) -> None:
    draw = ImageDraw.Draw(overlay)
    width, height = overlay.size
    slide = 1 - ease_out_cubic(min(progress / 0.34, 1))
    font = fit_text_font(overlay, text, 0.82, 0.07)
    x, y, tw, th, pad_x, pad_y = emphasis_box_position(overlay, text, font, 0.16)
    y += int(slide * height * 0.05)
    draw.text((x + 2, y + 3), text, font=font, fill=(0, 0, 0, int(alpha * 0.35)))
    draw.text((x, y), text, font=font, fill=(245, 248, 252, alpha))


def draw_emphasis_text(overlay: Image.Image, beat: dict[str, Any], t: float, style: dict[str, Any]) -> None:
    layer = layer_by_type(beat, "emphasis_text")
    if not layer or not layer.get("text"):
        return
    if layer.get("suppressed"):
        return
    start = float(layer.get("start", beat.get("start", 0)))
    end = float(layer.get("end", start + 1))
    if not (start <= t <= end):
        return
    width, height = overlay.size
    progress = clamp((t - start) / max(end - start, 0.1))
    in_pop = ease_out_cubic(min(progress / 0.22, 1))
    out_fade = 1 if progress < 0.76 else clamp((1 - progress) / 0.24)
    alpha = int(235 * min(in_pop, out_fade))
    text = str(layer["text"]).upper()
    effect = str(layer.get("effect", "capcut_highlight_wipe"))
    if effect == "capcut_highlight_wipe":
        draw_capcut_highlight_wipe(overlay, layer, text, progress, alpha, style)
        return
    if effect == "capcut_staggered_blur_glitch_reveal":
        draw_staggered_glitch_reveal(overlay, layer, text, progress, alpha, style)
        return
    if effect == "capcut_axis_stretch_word":
        draw_axis_stretch_word(overlay, layer, text, progress, alpha, style)
        return
    if effect == "capcut_font_shift_loop":
        draw_font_shift_loop(overlay, layer, text, progress, alpha, style)
        return
    if effect == "capcut_apple_slide_up_text":
        draw_apple_slide_up_text(overlay, layer, text, progress, alpha, style)
        return
    scale = 0.88 + 0.18 * in_pop - 0.04 * ease_in_out(max(0, progress - 0.22) / 0.54)
    draw = ImageDraw.Draw(overlay)
    max_text_width = int(width * 0.82)
    base_font_size = scaled_font_size(width, 0.071, 28, 78, scale)
    min_font_size = scaled_font_size(width, 0.044, 20, 42)
    font = fitted_font(draw, text, max_text_width, base_font_size, min_font_size, bold=True)
    tw, th = text_size(draw, text, font)
    x = (width - tw) // 2
    y = int(height * 0.125)
    accent = layer.get("accent_color") or style.get("secondary_accent", "#facc15")
    pad_x = max(18, int(width * 0.032))
    pad_y = max(12, int(height * 0.012))
    draw.rounded_rectangle((x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y + 6), radius=max(16, int(width * 0.028)), fill=(3, 7, 18, max(0, alpha - 72)))
    draw_glow_text(
        overlay,
        (x, y),
        text,
        font,
        fill=(255, 255, 255, alpha),
        glow=hex_to_rgba(accent, int(alpha * 0.72)),
        blur=max(8, int(width * 0.018)),
    )
    sweep_w = int((tw + pad_x * 2) * ease_in_out(progress))
    if sweep_w > 0:
        underline_y = y + th + pad_y
        draw.rounded_rectangle((x - pad_x, underline_y, x - pad_x + sweep_w, underline_y + max(4, int(height * 0.006))), radius=5, fill=hex_to_rgba(accent, int(alpha * 0.9)))


def draw_caption(overlay: Image.Image, cue: dict[str, Any], t: float, style: dict[str, Any], beat: dict[str, Any] | None = None) -> None:
    text = str(cue.get("text", "")).strip()
    if not text:
        return
    if style.get("_stock_montage_mode"):
        draw_stock_caption(overlay, cue, t, style, beat)
        return
    width, height = overlay.size
    start = float(cue.get("start", 0))
    end = float(cue.get("end", start + 1))
    progress = clamp((t - start) / max(end - start, 0.1))
    pop = ease_out_cubic(min(progress / 0.16, 1))
    fade = 1 if progress < 0.86 else clamp((1 - progress) / 0.14)
    alpha = int(245 * min(pop, fade))
    draw = ImageDraw.Draw(overlay)
    words = text.split()
    caption_layer = layer_by_type(beat or {}, "caption_kinetic") if beat else {}
    effect = str((caption_layer or {}).get("effect") or cue.get("style_id") or "")
    max_text_width = int(width * 0.82)
    font_size = scaled_font_size(width, 0.063, 28, 70, 0.92 + 0.1 * pop)
    min_font_size = scaled_font_size(width, 0.044, 20, 42)
    font = fitted_font(draw, text, max_text_width, font_size, min_font_size, bold=True)
    lines = wrap_words(draw, words, font, max_text_width, max_lines=2)
    line_gap = max(5, int(getattr(font, "size", font_size) * 0.18))
    line_sizes = [text_size(draw, " ".join(line), font) for line in lines]
    total_w = max((w for w, _ in line_sizes), default=0)
    total_h = sum(h for _, h in line_sizes) + line_gap * max(0, len(lines) - 1)
    x = (width - total_w) // 2
    y = int(height * 0.795) - total_h // 2
    pad_x, pad_y = max(16, int(width * 0.026)), max(10, int(height * 0.012))
    if "caption_suppressed" in effect:
        return
    elif "adaptive_texture" in effect:
        texture_alpha = int(alpha * 0.2)
        draw.rounded_rectangle(
            (x - pad_x, y - pad_y, x + total_w + pad_x, y + total_h + pad_y + 6),
            radius=max(14, int(width * 0.025)),
            fill=(255, 255, 255, int(alpha * 0.08)),
            outline=hex_to_rgba(style.get("accent_color", "#38bdf8"), int(alpha * 0.18)),
            width=2,
        )
        for offset in range(0, max(1, total_h + pad_y * 2), max(8, int(height * 0.01))):
            draw.line((x - pad_x + 10, y - pad_y + offset, x + total_w + pad_x - 10, y - pad_y + offset), fill=(255, 255, 255, texture_alpha), width=1)
    else:
        draw.rounded_rectangle(
            (x - pad_x, y - pad_y, x + total_w + pad_x, y + total_h + pad_y + 6),
            radius=max(14, int(width * 0.025)),
            fill=(2, 6, 16, int(alpha * 0.72)),
            outline=(255, 255, 255, int(alpha * 0.13)),
            width=2,
        )
        if "player3" in effect:
            stripe_w = int((total_w + pad_x * 2) * ease_out_cubic(min(progress / 0.28, 1)))
            draw.rounded_rectangle(
                (x - pad_x, y + total_h + pad_y + 1, x - pad_x + stripe_w, y + total_h + pad_y + 5),
                radius=4,
                fill=hex_to_rgba(style.get("accent_color", "#38bdf8"), int(alpha * 0.85)),
            )
    emphasis = " ".join(str(x).lower() for x in cue.get("emphasis_terms", []))
    hot_tokens = set(re.findall(r"[a-z0-9']+", emphasis))
    accent = style.get("secondary_accent", "#facc15")
    line_y = y
    for line, (_, line_h) in zip(lines, line_sizes):
        line_text = " ".join(line)
        line_w = text_size(draw, line_text, font)[0]
        cursor = (width - line_w) // 2
        space_w = text_size(draw, " ", font)[0]
        for word in line:
            ww, _ = text_size(draw, word, font)
            clean = re.sub(r"[^a-z0-9']+", "", word.lower())
            is_hot = bool(clean and clean in hot_tokens)
            fill = hex_to_rgba(accent, alpha) if is_hot else (255, 255, 255, alpha)
            if is_hot:
                glow_layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
                ImageDraw.Draw(glow_layer).text((cursor, line_y), word, font=font, fill=hex_to_rgba(accent, int(alpha * 0.5)))
                overlay.alpha_composite(glow_layer.filter(ImageFilter.GaussianBlur(max(6, int(width * 0.01)))))
            draw.text((cursor, line_y), word, font=font, fill=fill)
            cursor += ww + space_w
        line_y += line_h + line_gap


def draw_stock_caption(overlay: Image.Image, cue: dict[str, Any], t: float, style: dict[str, Any], beat: dict[str, Any] | None = None) -> None:
    text = str(cue.get("text", "")).strip()
    if not text:
        return
    width, height = overlay.size
    start = float(cue.get("start", 0))
    end = float(cue.get("end", start + 1))
    progress = clamp((t - start) / max(end - start, 0.1))
    pop = ease_out_cubic(min(progress / 0.18, 1))
    fade = 1 if progress < 0.86 else clamp((1 - progress) / 0.14)
    alpha = int(245 * min(pop, fade))
    draw = ImageDraw.Draw(overlay)
    max_text_width = int(width * 0.78)
    base_size = scaled_font_size(width, 0.058, 26, 64, 0.94 + 0.05 * pop)
    min_size = scaled_font_size(width, 0.04, 19, 40)
    font = fitted_font(draw, text, max_text_width, base_size, min_size, bold=True)
    lines = wrap_words(draw, text.split(), font, max_text_width, max_lines=2)
    line_gap = max(5, int(getattr(font, "size", base_size) * 0.18))
    line_sizes = [text_size(draw, " ".join(line), font) for line in lines]
    total_w = max((w for w, _ in line_sizes), default=0)
    total_h = sum(h for _, h in line_sizes) + line_gap * max(0, len(lines) - 1)
    y = int(height * 0.725) - total_h // 2 + int((1 - pop) * height * 0.018)
    x = (width - total_w) // 2
    pad_x = max(20, int(width * 0.032))
    pad_y = max(14, int(height * 0.013))

    panel = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(panel)
    box = (x - pad_x, y - pad_y, x + total_w + pad_x, y + total_h + pad_y + 8)
    shadow = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle(
        (box[0] - 8, box[1] + 10, box[2] + 8, box[3] + 16),
        radius=max(16, int(width * 0.024)),
        fill=(0, 0, 0, int(alpha * 0.42)),
    )
    overlay.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(max(10, int(width * 0.02)))))
    pdraw.rounded_rectangle(
        box,
        radius=max(14, int(width * 0.023)),
        fill=(5, 10, 18, int(alpha * 0.48)),
        outline=(255, 255, 255, int(alpha * 0.10)),
        width=1,
    )
    overlay.alpha_composite(panel)

    emphasis = " ".join(str(item).lower() for item in cue.get("emphasis_terms", []))
    hot_tokens = set(re.findall(r"[a-z0-9']+", emphasis))
    accent = style.get("secondary_accent") or style.get("accent_color") or "#facc15"
    line_y = y
    for line, (_, line_h) in zip(lines, line_sizes):
        line_text = " ".join(line)
        line_w = text_size(draw, line_text, font)[0]
        cursor = (width - line_w) // 2
        space_w = text_size(draw, " ", font)[0]
        for word in line:
            ww, _ = text_size(draw, word, font)
            clean = re.sub(r"[^a-z0-9']+", "", word.lower())
            is_hot = bool(clean and clean in hot_tokens)
            if is_hot:
                highlight_pad = max(4, int(width * 0.006))
                draw.rounded_rectangle(
                    (cursor - highlight_pad, line_y - 2, cursor + ww + highlight_pad, line_y + line_h + 7),
                    radius=max(6, int(width * 0.01)),
                    fill=hex_to_rgba(accent, int(alpha * 0.24)),
                )
                fill = hex_to_rgba(accent, alpha)
            else:
                fill = (248, 250, 252, alpha)
            draw.text((cursor + 2, line_y + 3), word, font=font, fill=(0, 0, 0, int(alpha * 0.36)))
            draw.text((cursor, line_y), word, font=font, fill=fill)
            cursor += ww + space_w
        line_y += line_h + line_gap


def render_rich_overlay_frames(
    project_dir: Path,
    timeline: dict[str, Any],
    captions_data: dict[str, Any],
    frames_dir: Path,
    width: int,
    height: int,
    fps: int,
    duration: float,
) -> Path:
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    directive = load_json(project_dir / "creative_directive.json")
    style = directive.get("style", {})
    stock_mode = stock_montage_mode(timeline)
    if stock_mode:
        style = {**style, "_stock_montage_mode": True}
    beats = timeline.get("beats", [])
    cues = captions_data.get("cues", [])
    frame_count = max(1, int(round(duration * fps)))
    accent = style.get("accent_color", "#38bdf8")
    for frame in range(frame_count):
        t = frame / fps
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        beat = active_beat(beats, t)
        if beat:
            if not stock_mode:
                draw_progress_and_frame(overlay, beat, t, duration, accent)
                draw_visual_overlay(overlay, beat, t, style)
                draw_emphasis_text(overlay, beat, t, style)
        cue = active_cue(cues, t)
        if cue:
            draw_caption(overlay, cue, t, style, beat)
        overlay.save(frames_dir / f"frame_{frame:05d}.png")
    return frames_dir / "frame_%05d.png"


def draw_overlay_frame(
    project_dir: Path,
    timeline: dict[str, Any],
    captions_data: dict[str, Any],
    width: int,
    height: int,
    fps: int,
    duration: float,
    frame: int,
    directive: dict[str, Any] | None = None,
) -> Image.Image:
    directive = directive if directive is not None else load_json(project_dir / "creative_directive.json")
    style = directive.get("style", {})
    stock_mode = stock_montage_mode(timeline)
    if stock_mode:
        style = {**style, "_stock_montage_mode": True}
    beats = timeline.get("beats", [])
    cues = captions_data.get("cues", [])
    t = frame / fps
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    beat = active_beat(beats, t)
    if beat:
        if not stock_mode:
            draw_progress_and_frame(overlay, beat, t, duration, style.get("accent_color", "#38bdf8"))
            draw_visual_overlay(overlay, beat, t, style)
            draw_emphasis_text(overlay, beat, t, style)
    cue = active_cue(cues, t)
    if cue:
        draw_caption(overlay, cue, t, style, beat)
    return overlay


def composite_overlay(video: Path, frame_pattern: Path, output: Path, fps: int, crf: int) -> None:
    run([
        "ffmpeg", "-y", "-hide_banner", "-nostats",
        "-i", str(video),
        "-framerate", str(fps), "-i", str(frame_pattern),
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-c:a", "copy", "-shortest",
        str(output),
    ])


def composite_overlay_scaled(video: Path, frame_pattern: Path, output: Path, overlay_fps: int, width: int, height: int, crf: int) -> None:
    run([
        "ffmpeg", "-y", "-hide_banner", "-nostats",
        "-i", str(video),
        "-framerate", str(overlay_fps), "-i", str(frame_pattern),
        "-filter_complex", f"[1:v]scale={width}:{height}:flags=lanczos[ov];[0:v][ov]overlay=0:0:format=auto,format=yuv420p[v]",
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-c:a", "copy", "-shortest",
        str(output),
    ])


def composite_rich_overlay_pipe(
    video: Path,
    output: Path,
    project_dir: Path,
    timeline: dict[str, Any],
    captions_data: dict[str, Any],
    width: int,
    height: int,
    fps: int,
    duration: float,
    crf: int,
) -> None:
    preview_mode = crf >= 26
    overlay_width = width // 2 if preview_mode else width
    overlay_height = height // 2 if preview_mode else height
    overlay_fps = 15 if preview_mode else fps
    frame_count = max(1, int(round(duration * overlay_fps)))
    directive = load_json(project_dir / "creative_directive.json")
    overlay_filter = f"[1:v]scale={width}:{height}:flags=lanczos[ov];[0:v][ov]overlay=0:0:format=auto,format=yuv420p[v]"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-nostats",
        "-i", str(video),
        "-thread_queue_size", "128", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{overlay_width}x{overlay_height}", "-r", str(overlay_fps), "-i", "-",
        "-filter_complex", overlay_filter,
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-c:a", "copy", "-shortest",
        str(output),
    ]
    print(f"  $ {' '.join(shlex.quote(c) for c in cmd[:10])} ...")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for frame in range(frame_count):
            overlay = draw_overlay_frame(project_dir, timeline, captions_data, overlay_width, overlay_height, overlay_fps, duration, frame, directive)
            proc.stdin.write(overlay.tobytes())
    except BrokenPipeError as exc:
        raise RuntimeError("ffmpeg closed the overlay pipe early") from exc
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
    return_code = proc.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, cmd)


def render_placeholder(text: str, output: Path, width: int, height: int) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (width, height), "#101820")
    draw = ImageDraw.Draw(image)
    title_font = load_font(max(36, width // 18), bold=True)
    body_font = load_font(max(18, width // 44))
    draw.rectangle((0, 0, width, height), fill="#101820")
    draw.rectangle((40, 40, width - 40, height - 40), outline="#334155", width=2)
    draw.rectangle((0, 0, width, 14), fill="#22c55e")
    lines = textwrap.wrap(text or "Visual placeholder", width=24 if height > width else 42)[:8]
    line_height = int(getattr(title_font, "size", 44) * 1.22)
    y = max(96, (height - line_height * len(lines)) // 2)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        draw.text(((width - (bbox[2] - bbox[0])) // 2, y), line, fill="#f8fafc", font=title_font)
        y += line_height
    draw.text((56, height - 90), "placeholder visual", fill="#94a3b8", font=body_font)
    image.save(output)
    return output


def manifest_lookup(project_dir: Path) -> dict[str, dict[str, Any]]:
    try:
        manifest = load_manifest(project_dir)
    except Exception:
        return {}
    lookup: dict[str, dict[str, Any]] = {}
    for asset in manifest.get("assets", []):
        for key in ("manifest_id", "asset_id"):
            value = asset.get(key)
            if value:
                lookup[str(value)] = asset
    return lookup


def resolve_asset(project_dir: Path, beat: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> Path | None:
    candidate = beat.get("primary_asset_path")
    if candidate:
        path = Path(candidate)
        if not path.is_absolute():
            path = project_dir / path
        if path.exists():
            return path
    asset_id = beat.get("primary_asset_id")
    if asset_id and asset_id in lookup:
        local = lookup[asset_id].get("local_path")
        if local:
            path = Path(local)
            if not path.is_absolute():
                path = project_dir / path
            if path.exists():
                return path
    return None


def make_clip(asset: Path, output: Path, duration: float, width: int, height: int, fps: int, crf: int, beat: dict[str, Any]) -> None:
    if valid_video(output) and output.stat().st_mtime >= asset.stat().st_mtime:
        return
    if output.exists():
        output.unlink()
    color_layer = layer_by_type(beat, "color_grade") or {}
    filters = color_layer.get("filters", {}) if isinstance(color_layer.get("filters", {}), dict) else {}
    contrast = float(filters.get("contrast", 1.05))
    saturation = float(filters.get("saturation", 1.06))
    brightness = float(filters.get("brightness", 0.0))
    color_vf = f"eq=contrast={contrast}:saturation={saturation}:brightness={brightness},unsharp=5:5:0.45:3:3:0.15"
    if asset.suffix.lower() in IMAGE_EXTS:
        frames = max(1, int(round(duration * fps)))
        static_frame = bool(beat.get("static_frame") or beat.get("stock_montage_static"))
        if crf >= 28 or static_frame:
            vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},{color_vf},format=yuv420p"
        else:
            vf = (
                f"scale={width * 2}:-2,"
                f"zoompan=z='min(zoom+0.0012,1.075)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={frames}:s={width}x{height}:fps={fps},"
                f"{color_vf},format=yuv420p"
            )
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-nostats",
            "-loop", "1", "-t", f"{duration:.3f}", "-i", str(asset),
            "-vf", vf,
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
            str(output),
        ]
    elif asset.suffix.lower() in VIDEO_EXTS:
        vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},{color_vf},format=yuv420p"
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-nostats",
            "-stream_loop", "-1", "-t", f"{duration:.3f}", "-i", str(asset),
            "-vf", vf,
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
            str(output),
        ]
    else:
        raise RuntimeError(f"unsupported asset type for render: {asset}")
    run(cmd)


def concat_clips(clips: list[Path], output: Path) -> None:
    concat_file = output.parent / "concat.txt"
    concat_file.write_text("".join(f"file '{clip.resolve()}'\n" for clip in clips), encoding="utf-8")
    run(["ffmpeg", "-y", "-hide_banner", "-nostats", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output)])


def concat_clips_xfade(clips: list[Path], output: Path, durations: list[float], transition_duration: float = 0.32, transition: str = "fade") -> None:
    if len(clips) == 1:
        output.write_bytes(clips[0].read_bytes())
        return
    transition_duration = max(0.08, min(0.65, transition_duration))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-nostats"]
    for clip in clips:
        cmd.extend(["-i", str(clip)])
    filters: list[str] = []
    last = "[0:v]"
    current_duration = float(durations[0])
    for idx in range(1, len(clips)):
        out = f"[v{idx}]"
        offset = max(0.1, current_duration - transition_duration)
        filters.append(
            f"{last}[{idx}:v]xfade=transition={transition}:duration={transition_duration:.3f}:offset={offset:.3f}{out}"
        )
        current_duration = current_duration + float(durations[idx]) - transition_duration
        last = out
    cmd.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            last,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )
    run(cmd)


def mux_voiceover(video: Path, voiceover: Path | None, output: Path) -> None:
    if not voiceover or not voiceover.exists():
        output.write_bytes(video.read_bytes())
        return
    run([
        "ffmpeg", "-y", "-hide_banner", "-nostats",
        "-i", str(video), "-i", str(voiceover),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(output),
    ])


def caption_style_edl_from_timeline(timeline: dict[str, Any]) -> dict[str, Any]:
    project = timeline.get("project", {}) if isinstance(timeline.get("project"), dict) else {}
    captions = timeline.get("captions", {}) if isinstance(timeline.get("captions"), dict) else {}
    caption_options = project.get("caption_options") if isinstance(project.get("caption_options"), dict) else {}
    style_id = (
        project.get("caption_style")
        or project.get("subtitle_style")
        or captions.get("style")
        or captions.get("style_id")
    )
    edl: dict[str, Any] = {}
    if style_id:
        edl["caption_style"] = style_id
    if caption_options:
        edl["caption_options"] = caption_options
    return edl


def dynamic_subtitle_force_style(timeline: dict[str, Any], video: Path) -> str:
    try:
        return srt_force_style(caption_style_edl_from_timeline(timeline), video)
    except Exception:
        return srt_force_style({}, video)


def burn_captions(video: Path, captions: Path | None, output: Path, timeline: dict[str, Any]) -> None:
    if not captions or not captions.exists():
        output.write_bytes(video.read_bytes())
        return
    subs = str(captions.resolve()).replace(":", r"\:").replace("'", r"\'")
    if captions.suffix.lower() in {".ass", ".ssa"}:
        vf = f"subtitles='{subs}'"
    else:
        force_style = dynamic_subtitle_force_style(timeline, video).replace(":", r"\:").replace("'", r"\'")
        vf = f"subtitles='{subs}':force_style='{force_style}'"
    run(["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", str(video), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", str(output)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Render preview/final from a from-scratch edit_decision_list.json.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--voiceover", type=Path)
    parser.add_argument("--captions", type=Path)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--no-captions", action="store_true")
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    timeline_path = args.timeline or project_dir / "edit_decision_list.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    project = timeline.get("project", {})
    resolution = project.get("resolution", {})
    width = int(resolution.get("width", 1080))
    height = int(resolution.get("height", 1920))
    fps = int(project.get("fps", 30))
    crf = 28 if args.preview else 20
    output = args.output or project_dir / ("preview.mp4" if args.preview else "final.mp4")
    renders = project_dir / "renders" / ("preview" if args.preview else "final")
    renders.mkdir(parents=True, exist_ok=True)
    lookup = manifest_lookup(project_dir)
    use_stock_xfade = bool(project.get("stock_montage_only") or project.get("transition_style") == "stock_crossfade")
    transition_duration = float(project.get("transition_duration_seconds", 0.32))
    beats = timeline.get("beats", [])

    clips: list[Path] = []
    durations: list[float] = []
    for idx, beat in enumerate(beats, start=1):
        start = float(beat.get("start", 0))
        end = float(beat.get("end", start + 3))
        duration = max(0.2, end - start)
        render_duration = duration + transition_duration if use_stock_xfade and idx < len(beats) else duration
        asset = resolve_asset(project_dir, beat, lookup)
        if asset is None:
            asset = render_placeholder(
                beat.get("visual_job") or beat.get("script_text") or f"Beat {idx}",
                renders / f"placeholder_{idx:03d}.png",
                width,
                height,
            )
        clip = renders / f"clip_{idx:03d}.mp4"
        make_clip(asset, clip, render_duration, width, height, fps, crf, beat)
        clips.append(clip)
        durations.append(render_duration)

    if not clips:
        raise SystemExit("timeline has no beats to render")
    base = renders / "base.mp4"
    with_audio = renders / "with_audio.mp4"
    if use_stock_xfade:
        concat_clips_xfade(clips, base, durations, transition_duration=transition_duration, transition=str(project.get("transition_xfade", "fade")))
    else:
        concat_clips(clips, base)

    voiceover = args.voiceover or project_dir / "assets" / "audio" / "voiceover.mp3"
    captions = None if args.no_captions else (args.captions or project_dir / "captions" / "master.srt")
    mux_voiceover(base, voiceover if voiceover.exists() else None, with_audio)
    with_sfx = renders / "with_sfx.mp4"
    _, sfx_events = mix_sfx_into_video(with_audio, timeline, with_sfx, renders / "sfx_mix.wav")
    audio_video = with_sfx if with_sfx.exists() else with_audio
    captions_json = project_dir / "captions" / "captions.json"
    if not args.no_captions and captions_json.exists():
        duration = max((float(beat.get("end", 0)) for beat in timeline.get("beats", [])), default=float(project.get("target_duration_seconds", 0) or 0))
        if duration <= 0:
            duration = float(project.get("target_duration_seconds", 30))
        overlay_width = width // 2 if args.preview else width
        overlay_height = height // 2 if args.preview else height
        overlay_fps = 15 if args.preview else fps
        frame_pattern = render_rich_overlay_frames(
            project_dir,
            timeline,
            load_json(captions_json),
            renders / "rich_overlay_frames",
            overlay_width,
            overlay_height,
            overlay_fps,
            duration,
        )
        composite_overlay_scaled(audio_video, frame_pattern, output, overlay_fps, width, height, crf=26 if args.preview else 20)
    else:
        burn_captions(audio_video, captions if captions and captions.exists() else None, output, timeline)
    print(json.dumps({"output": str(output), "beats": len(clips), "captions": bool((captions and captions.exists()) or captions_json.exists()), "rich_overlay": captions_json.exists() and not args.no_captions, "voiceover": bool(voiceover.exists()), "sfx_events": len(sfx_events)}, indent=2))


if __name__ == "__main__":
    main()
