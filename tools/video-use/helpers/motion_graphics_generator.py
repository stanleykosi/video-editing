"""Generate polished motion-card image assets for from-scratch timelines.

The cards are still local Pillow renders, but they follow the same placement
rules as the rest of the video system: clear visual hierarchy, protected center
space for proof/diagrams, safe lower-caption area, and no generic placeholder
labels in finished projects. Complex animation should still be delegated to
Remotion, HyperFrames, Manim, or a dedicated motion sub-agent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from asset_manifest import add_asset_entry, utc_now


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    base_size: int,
    min_size: int,
    bold: bool = True,
) -> ImageFont.ImageFont:
    size = max(base_size, min_size)
    while size > min_size:
        candidate = load_font(size, bold=bold)
        if text_size(draw, text, candidate)[0] <= max_width:
            return candidate
        size -= 2
    return load_font(min_size, bold=bold)


def wrap_to_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    max_lines: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if current and text_size(draw, candidate, font)[0] > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    if len(lines) <= max_lines:
        return lines
    kept = lines[: max_lines - 1]
    kept.append(" ".join(lines[max_lines - 1 :]))
    return kept


def draw_gradient_background(draw: ImageDraw.ImageDraw, width: int, height: int, bg: str) -> None:
    base = bg.lstrip("#")
    try:
        r, g, b = int(base[0:2], 16), int(base[2:4], 16), int(base[4:6], 16)
    except Exception:
        r, g, b = 10, 24, 38
    for y in range(height):
        lift = y / max(height, 1)
        draw.line(
            (0, y, width, y),
            fill=(
                min(255, int(r + 8 * lift)),
                min(255, int(g + 20 * lift)),
                min(255, int(b + 30 * lift)),
            ),
        )


def split_copy(text: str) -> tuple[str, str]:
    clean = " ".join(text.split())
    if not clean:
        return "Key idea", ""
    sentences = [part.strip() for part in clean.replace("?", ".").replace("!", ".").split(".") if part.strip()]
    headline = sentences[0] if sentences else clean
    if len(headline.split()) > 7:
        words = headline.split()
        headline = " ".join(words[:7])
        body = " ".join(words[7:] + [word for sentence in sentences[1:] for word in sentence.split()])
    else:
        body = " ".join(sentences[1:])
    return headline, body


def render_card(text: str, output: Path, size: tuple[int, int], accent: str, bg: str) -> None:
    width, height = size
    image = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(image)
    draw_gradient_background(draw, width, height, bg)

    margin = int(width * 0.07)
    inner = (margin, int(height * 0.07), width - margin, int(height * 0.88))
    draw.rounded_rectangle(inner, radius=max(26, width // 28), outline="#24445c", width=3)
    draw.rectangle((0, 0, int(width * 0.42), max(10, height // 150)), fill=accent)
    draw.rounded_rectangle(
        (margin + 18, int(height * 0.11), margin + 236, int(height * 0.15)),
        radius=18,
        fill="#082f49",
        outline=accent,
        width=2,
    )

    eyebrow_font = load_font(max(22, width // 38), bold=True)
    draw.text((margin + 36, int(height * 0.115)), "KEY IDEA", fill="#bae6fd", font=eyebrow_font)

    headline, body = split_copy(text)
    max_width = width - margin * 2 - 56
    title_font = fit_font(draw, headline, max_width, max(52, width // 12), max(34, width // 26), bold=True)
    title_lines = wrap_to_width(draw, headline, title_font, max_width, max_lines=3)
    title_line_h = int(getattr(title_font, "size", width // 12) * 1.08)
    y = int(height * 0.19)
    for line in title_lines:
        draw.text((margin + 28, y), line, fill="#f8fafc", font=title_font)
        y += title_line_h

    accent_y = y + int(height * 0.02)
    draw.rounded_rectangle(
        (margin + 28, accent_y, margin + 28 + int(max_width * 0.52), accent_y + 8),
        radius=5,
        fill=accent,
    )

    visual_top = int(height * 0.47)
    visual_center = (width // 2, int(height * 0.56))
    orbit_w, orbit_h = int(width * 0.55), int(height * 0.21)
    draw.ellipse(
        (
            visual_center[0] - orbit_w // 2,
            visual_center[1] - orbit_h // 2,
            visual_center[0] + orbit_w // 2,
            visual_center[1] + orbit_h // 2,
        ),
        outline="#38bdf8",
        width=max(4, width // 130),
    )
    draw.ellipse(
        (
            visual_center[0] - orbit_w // 5,
            visual_center[1] - orbit_h // 5,
            visual_center[0] + orbit_w // 5,
            visual_center[1] + orbit_h // 5,
        ),
        fill="#0ea5e9",
    )
    draw.arc(
        (
            visual_center[0] - orbit_w // 2 - 34,
            visual_center[1] - orbit_h // 2 - 34,
            visual_center[0] + orbit_w // 2 + 34,
            visual_center[1] + orbit_h // 2 + 34,
        ),
        205,
        335,
        fill="#22c55e",
        width=max(6, width // 90),
    )
    draw.arc(
        (
            visual_center[0] - orbit_w // 2 - 34,
            visual_center[1] - orbit_h // 2 - 34,
            visual_center[0] + orbit_w // 2 + 34,
            visual_center[1] + orbit_h // 2 + 34,
        ),
        25,
        155,
        fill="#22c55e",
        width=max(6, width // 90),
    )

    if body:
        body_font = fit_font(draw, body, max_width, max(30, width // 25), max(22, width // 42), bold=False)
        body_lines = wrap_to_width(draw, body, body_font, max_width, max_lines=3)
        body_y = max(visual_top + int(height * 0.24), int(height * 0.69))
        line_h = int(getattr(body_font, "size", width // 25) * 1.28)
        for line in body_lines:
            draw.text((margin + 28, body_y), line, fill="#cbd5e1", font=body_font)
            body_y += line_h

    draw.rounded_rectangle(
        (margin + 28, int(height * 0.82), width - margin - 28, int(height * 0.85)),
        radius=14,
        fill="#0f172a",
        outline="#1e3a4c",
        width=2,
    )
    draw.rectangle((margin + 44, int(height * 0.835), width - margin - 44, int(height * 0.838)), fill=accent)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate simple motion-card PNGs from a timeline.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--accent", default="#38bdf8")
    parser.add_argument("--background", default="#111827")
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    timeline_path = args.timeline or project_dir / "edit_decision_list.json"
    output_json = args.output_json or project_dir / "motion_graphics_plan.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    resolution = timeline.get("project", {}).get("resolution", {"width": 1080, "height": 1920})
    size = (int(resolution.get("width", 1080)), int(resolution.get("height", 1920)))
    overlays: list[dict[str, Any]] = []

    for beat in timeline.get("beats", []):
        beat_id = beat.get("beat_id", "beat")
        text = beat.get("caption", {}).get("text") or beat.get("script_text") or beat.get("visual_job") or beat_id
        output = project_dir / "assets" / "generated" / "motion_cards" / f"{beat_id.lower()}_motion_card.png"
        render_card(text, output, size, args.accent, args.background)
        entry = {
            "source_platform": "local_generation",
            "asset_type": "motion_card",
            "asset_id": output.stem,
            "asset_title": f"Motion card {beat_id}",
            "creator": "video-use motion_graphics_generator.py",
            "local_path": str(output),
            "downloaded_at": utc_now(),
            "generation_provider": "local_pillow",
            "prompt": text,
            "generation_date": utc_now(),
            "policy_or_license_notes": "Locally generated graphic card.",
            "used_in_timeline": True,
        }
        _, asset = add_asset_entry(project_dir, entry)
        beat["primary_asset_id"] = asset.get("manifest_id", output.stem)
        beat["primary_asset_path"] = str(output)
        overlays.append({"beat_id": beat_id, "path": str(output), "start": beat.get("start"), "end": beat.get("end")})

    timeline_path.write_text(json.dumps(timeline, indent=2) + "\n", encoding="utf-8")
    output_json.write_text(json.dumps({"created_at": utc_now(), "overlays": overlays}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"timeline": str(timeline_path), "json": str(output_json), "cards": len(overlays)}, indent=2))


if __name__ == "__main__":
    main()
