"""Generate visual QC contact sheets and reports for clipping/editing work.

This helper exists to close the gap between transcript-led clipping and actual
frame review. It samples either source ranges from an EDL or a rendered preview,
creates contact sheets for the agent/LLM to inspect, optionally runs OCR on the
frames, and writes JSON/Markdown reports.

Typical flow for existing-footage work:

    # Before locking a cut, inspect the proposed source ranges.
    python helpers/visual_qc.py --edl edit/edl.json --source-preflight

    # After rendering preview.mp4, generate the blocking pre-final report.
    python helpers/visual_qc.py --video edit/preview.mp4 --edl edit/edl.json

    # After the agent has viewed every contact sheet, mark the report.
    python helpers/visual_qc.py --mark-reviewed edit/visual_qc/visual_qc_report.json \
        --status pass --notes "No source overlays, bad crops, or caption collisions found."

Final renders are allowed to proceed only after the rendered-preview report is
marked pass by the reviewing agent/LLM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import cv2
except Exception:  # pragma: no cover - optional at runtime
    cv2 = None

try:
    import pytesseract
except Exception:  # pragma: no cover - optional at runtime
    pytesseract = None


STATUSES = {
    "needs_llm_review",
    "pass",
    "needs_reclip",
    "needs_reframe",
    "needs_mask",
    "blocked",
}


OCR_REGIONS = {
    "top_band": (0.0, 0.0, 1.0, 0.24),
    "middle_band": (0.0, 0.24, 1.0, 0.70),
    "lower_band": (0.0, 0.66, 1.0, 1.0),
}

CAPTION_SAFE_ZONES = {
    "lower": (0.10, 0.66, 0.90, 0.94),
    "center": (0.10, 0.36, 0.90, 0.68),
}


FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
]


@dataclass
class Sample:
    index: int
    video: Path
    timestamp: float
    label: str
    mode: str
    source_id: str | None = None
    range_index: int | None = None
    output_time: float | None = None
    beat: str | None = None
    frame_path: Path | None = None
    findings: list[dict[str, Any]] = field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_json(cmd: list[str]) -> dict[str, Any]:
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"command failed: {' '.join(cmd)}")
    return json.loads(result.stdout or "{}")


def ffprobe_duration(video: Path) -> float:
    data = run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video),
        ]
    )
    return float(data.get("format", {}).get("duration") or 0.0)


def resolve_path(value: str, base: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def load_edl(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def output_offsets(edl: dict[str, Any]) -> list[tuple[float, float]]:
    offsets: list[tuple[float, float]] = []
    cursor = 0.0
    for item in edl.get("ranges", []):
        start = float(item.get("start", 0.0))
        end = float(item.get("end", start))
        duration = max(0.0, end - start)
        offsets.append((cursor, cursor + duration))
        cursor += duration
    return offsets


def clamp_time(value: float, duration: float) -> float:
    if duration <= 0:
        return 0.0
    return max(0.0, min(duration - 0.02, value))


def uniq_times(times: list[float], duration: float) -> list[float]:
    rounded = sorted({round(clamp_time(t, duration), 2) for t in times if math.isfinite(t)})
    return [t for t in rounded if 0.0 <= t < max(0.02, duration)]


def thin_samples(samples: list[Sample], max_frames: int) -> list[Sample]:
    if len(samples) <= max_frames:
        return samples
    if max_frames < 1:
        max_frames = 1
    step = (len(samples) - 1) / max(1, max_frames - 1)
    keep = sorted({round(i * step) for i in range(max_frames)})
    return [samples[i] for i in keep]


def make_render_samples(
    video: Path,
    edl: dict[str, Any] | None,
    interval: float,
    max_frames: int,
) -> list[Sample]:
    duration = ffprobe_duration(video)
    times = [0.25, 1.25, duration * 0.25, duration * 0.5, duration * 0.75, duration - 1.25, duration - 0.25]
    if interval > 0:
        t = interval
        while t < duration:
            times.append(t)
            t += interval
    if edl:
        for cut_start, cut_end in output_offsets(edl)[1:]:
            cut = cut_start
            times.extend([cut - 0.30, cut - 0.08, cut + 0.08, cut + 0.30])

    samples: list[Sample] = []
    for idx, t in enumerate(uniq_times(times, duration), start=1):
        samples.append(
            Sample(
                index=idx,
                video=video,
                timestamp=t,
                output_time=t,
                mode="render",
                label=f"render t={t:.2f}s",
            )
        )
    return thin_samples(samples, max_frames)


def make_source_samples(
    edl_path: Path,
    edl: dict[str, Any],
    interval: float,
    max_frames: int,
) -> list[Sample]:
    edit_dir = edl_path.parent
    sources = edl.get("sources", {})
    offsets = output_offsets(edl)
    samples: list[Sample] = []

    for range_index, item in enumerate(edl.get("ranges", []), start=1):
        source_id = item.get("source")
        if source_id not in sources:
            continue
        video = resolve_path(str(sources[source_id]), edit_dir)
        start = float(item.get("start", 0.0))
        end = float(item.get("end", start))
        duration = max(0.0, end - start)
        if duration <= 0:
            continue

        local_times = [0.15, min(1.0, duration * 0.25), duration * 0.5, max(0.15, duration - 1.0), duration - 0.15]
        if interval > 0 and duration > interval:
            t = interval
            while t < duration:
                local_times.append(t)
                t += interval

        output_start = offsets[range_index - 1][0] if range_index - 1 < len(offsets) else None
        for local_time in uniq_times(local_times, duration):
            timestamp = start + local_time
            output_time = output_start + local_time if output_start is not None else None
            beat = item.get("beat") or item.get("note")
            samples.append(
                Sample(
                    index=len(samples) + 1,
                    video=video,
                    timestamp=timestamp,
                    source_id=str(source_id),
                    range_index=range_index,
                    output_time=output_time,
                    beat=str(beat) if beat else None,
                    mode="source",
                    label=(
                        f"{source_id} r{range_index} src={timestamp:.2f}s"
                        + (f" out={output_time:.2f}s" if output_time is not None else "")
                    ),
                )
            )

    return thin_samples(samples, max_frames)


def extract_frame(video: Path, timestamp: float, out_path: Path, width: int) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale={width}:-2"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-vf",
        vf,
        "-q:v",
        "3",
        str(out_path),
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return result.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue
    return ImageFont.load_default()


def normalize_ocr_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"^[^\w$#@]+|[^\w.!?%$#@]+$", "", text)
    return text


def has_tesseract() -> bool:
    return pytesseract is not None and shutil.which("tesseract") is not None


def face_detection_available() -> bool:
    if cv2 is None:
        return False
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    return cascade_path.exists()


def selected_caption_zone(name: str) -> tuple[float, float, float, float] | None:
    if name == "none":
        return None
    return CAPTION_SAFE_ZONES.get(name, CAPTION_SAFE_ZONES["lower"])


def box_intersection_area(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    if right <= left or bottom <= top:
        return 0.0
    return (right - left) * (bottom - top)


def detect_face_findings(image_path: Path, caption_zone_name: str) -> list[dict[str, Any]]:
    if not face_detection_available():
        return []

    image = cv2.imread(str(image_path))
    if image is None:
        return []
    height, width = image.shape[:2]
    if width <= 0 or height <= 0:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    cascade_path = str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
    cascade = cv2.CascadeClassifier(cascade_path)
    min_face = max(28, int(min(width, height) * 0.045))
    detections = cascade.detectMultiScale(
        gray,
        scaleFactor=1.08,
        minNeighbors=5,
        minSize=(min_face, min_face),
    )

    findings: list[dict[str, Any]] = []
    zone = selected_caption_zone(caption_zone_name)
    edge_margin = 0.045
    for idx, (x, y, w, h) in enumerate(detections, start=1):
        box = (
            round(x / width, 4),
            round(y / height, 4),
            round((x + w) / width, 4),
            round((y + h) / height, 4),
        )
        face_area = max(1e-6, (w / width) * (h / height))
        findings.append(
            {
                "type": "face_detected",
                "severity": "info",
                "region": "face",
                "face_index": idx,
                "box": box,
            }
        )

        if zone:
            overlap = box_intersection_area(box, zone)
            center_x = (box[0] + box[2]) / 2
            center_y = (box[1] + box[3]) / 2
            center_in_zone = zone[0] <= center_x <= zone[2] and zone[1] <= center_y <= zone[3]
            if center_in_zone or (overlap / face_area) >= 0.12:
                findings.append(
                    {
                        "type": "caption_face_collision_risk",
                        "severity": "needs_reframe_or_caption_move",
                        "region": f"{caption_zone_name}_caption_safe_zone",
                        "face_index": idx,
                        "face_box": box,
                        "safe_zone": tuple(round(v, 4) for v in zone),
                        "overlap_face_ratio": round(overlap / face_area, 3),
                    }
                )

        if box[0] < edge_margin or box[1] < edge_margin or box[2] > 1 - edge_margin or box[3] > 1 - edge_margin:
            findings.append(
                {
                    "type": "face_near_crop_edge",
                    "severity": "reframe_review",
                    "region": "frame_edge",
                    "face_index": idx,
                    "face_box": box,
                }
            )

    return findings


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    # Upscale smaller crops: OCR is much better when text height is not tiny.
    if gray.width < 900:
        scale = 900 / max(1, gray.width)
        gray = gray.resize((int(gray.width * scale), int(gray.height * scale)), Image.Resampling.LANCZOS)
    return ImageOps.autocontrast(gray)


def ocr_regions(image_path: Path, mode: str, confidence_threshold: int = 45) -> list[dict[str, Any]]:
    if not has_tesseract():
        return []

    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    findings: list[dict[str, Any]] = []
    config = "--psm 6"

    for region_name, box in OCR_REGIONS.items():
        left = int(box[0] * width)
        top = int(box[1] * height)
        right = int(box[2] * width)
        bottom = int(box[3] * height)
        crop = image.crop((left, top, right, bottom))
        prepared = preprocess_for_ocr(crop)
        try:
            data = pytesseract.image_to_data(
                prepared,
                lang="eng",
                config=config,
                output_type=pytesseract.Output.DICT,
            )
        except Exception as exc:
            return [{"type": "ocr_error", "severity": "warning", "message": str(exc)}]

        words: list[str] = []
        confidences: list[float] = []
        for raw_text, raw_conf in zip(data.get("text", []), data.get("conf", [])):
            text = normalize_ocr_text(raw_text)
            if not text:
                continue
            try:
                confidence = float(raw_conf)
            except Exception:
                confidence = -1.0
            if confidence < confidence_threshold:
                continue
            words.append(text)
            confidences.append(confidence)

        phrase = normalize_ocr_text(" ".join(words))
        if len(phrase) < 4:
            continue

        severity = "review"
        if mode == "source":
            severity = "source_text_present"
        elif region_name != "lower_band":
            severity = "possible_obstacle"
        findings.append(
            {
                "type": "ocr_text",
                "severity": severity,
                "region": region_name,
                "text": phrase[:220],
                "word_count": len(words),
                "mean_confidence": round(sum(confidences) / max(1, len(confidences)), 1),
            }
        )
    return findings


def possible_banner_findings(image_path: Path) -> list[dict[str, Any]]:
    image = Image.open(image_path).convert("L")
    width, height = image.size
    body = image.crop((0, int(height * 0.28), width, int(height * 0.64)))
    body_mean = sum(body.getdata()) / max(1, body.width * body.height)
    findings: list[dict[str, Any]] = []

    for region_name, box in {
        "top_band": (0, 0, width, int(height * 0.18)),
        "lower_band": (0, int(height * 0.78), width, height),
    }.items():
        region = image.crop(box)
        pixels = list(region.getdata())
        if not pixels:
            continue
        mean = sum(pixels) / len(pixels)
        variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
        stddev = math.sqrt(variance)
        if stddev < 28 and abs(mean - body_mean) > 30:
            findings.append(
                {
                    "type": "possible_solid_banner",
                    "severity": "review",
                    "region": region_name,
                    "mean_luma": round(mean, 1),
                    "stddev_luma": round(stddev, 1),
                }
            )
    return findings


def is_review_finding(finding: dict[str, Any]) -> bool:
    return finding.get("severity") != "info"


def review_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [finding for finding in findings if is_review_finding(finding)]


def analyze_sample(sample: Sample, ocr: bool, face_detect: bool, caption_zone: str) -> None:
    if not sample.frame_path:
        return
    findings: list[dict[str, Any]] = []
    if face_detect:
        findings.extend(detect_face_findings(sample.frame_path, caption_zone))
    if ocr:
        findings.extend(ocr_regions(sample.frame_path, sample.mode))
    findings.extend(possible_banner_findings(sample.frame_path))
    sample.findings = findings


def sample_to_json(sample: Sample) -> dict[str, Any]:
    return {
        "index": sample.index,
        "mode": sample.mode,
        "video": str(sample.video),
        "timestamp": round(sample.timestamp, 3),
        "source_id": sample.source_id,
        "range_index": sample.range_index,
        "output_time": round(sample.output_time, 3) if sample.output_time is not None else None,
        "beat": sample.beat,
        "label": sample.label,
        "frame_path": str(sample.frame_path) if sample.frame_path else None,
        "findings": sample.findings,
    }


def normalized_box_to_pixels(
    box: tuple[float, float, float, float] | list[float],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    return (
        int(float(box[0]) * width),
        int(float(box[1]) * height),
        int(float(box[2]) * width),
        int(float(box[3]) * height),
    )


def annotate_frame(frame: Image.Image, sample: Sample, caption_zone: str) -> Image.Image:
    annotated = frame.convert("RGBA")
    overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = annotated.size

    zone = selected_caption_zone(caption_zone)
    has_caption_collision = any(f.get("type") == "caption_face_collision_risk" for f in sample.findings)
    if zone:
        zone_px = normalized_box_to_pixels(zone, width, height)
        fill = (255, 170, 40, 42 if has_caption_collision else 24)
        outline = (255, 170, 40, 210 if has_caption_collision else 110)
        draw.rectangle(zone_px, fill=fill, outline=outline, width=3)

    face_boxes: list[tuple[float, float, float, float] | list[float]] = []
    for finding in sample.findings:
        if finding.get("type") == "face_detected" and finding.get("box"):
            face_boxes.append(finding["box"])
        elif finding.get("type") in {"caption_face_collision_risk", "face_near_crop_edge"} and finding.get("face_box"):
            face_boxes.append(finding["face_box"])

    seen: set[tuple[int, int, int, int]] = set()
    for box in face_boxes:
        box_px = normalized_box_to_pixels(box, width, height)
        if box_px in seen:
            continue
        seen.add(box_px)
        draw.rectangle(box_px, outline=(80, 220, 120, 230), width=max(3, width // 240))

    return Image.alpha_composite(annotated, overlay).convert("RGB")


def make_contact_sheets(
    samples: list[Sample],
    out_dir: Path,
    frames_per_sheet: int = 12,
    columns: int = 3,
    caption_zone: str = "lower",
) -> list[Path]:
    sheets_dir = out_dir / "contact_sheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)
    sheet_paths: list[Path] = []
    font = load_font(18)
    small_font = load_font(14)
    cell_w = 430
    cell_h = 330
    frame_h = 245
    pad = 16

    for sheet_index, offset in enumerate(range(0, len(samples), frames_per_sheet), start=1):
        chunk = samples[offset : offset + frames_per_sheet]
        rows = math.ceil(len(chunk) / columns)
        sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (18, 18, 22))
        draw = ImageDraw.Draw(sheet)

        for cell_index, sample in enumerate(chunk):
            col = cell_index % columns
            row = cell_index // columns
            x0 = col * cell_w
            y0 = row * cell_h
            has_findings = bool(review_findings(sample.findings))
            border = (235, 80, 70) if has_findings else (80, 90, 105)
            draw.rectangle((x0 + 5, y0 + 5, x0 + cell_w - 5, y0 + cell_h - 5), outline=border, width=3)

            if sample.frame_path and sample.frame_path.exists():
                frame = Image.open(sample.frame_path).convert("RGB")
                frame = annotate_frame(frame, sample, caption_zone)
                frame = ImageOps.contain(frame, (cell_w - pad * 2, frame_h), Image.Resampling.LANCZOS)
                fx = x0 + (cell_w - frame.width) // 2
                fy = y0 + pad
                sheet.paste(frame, (fx, fy))

            label = f"{sample.index:02d}  {sample.label}"
            draw.text((x0 + pad, y0 + frame_h + 22), label[:48], fill=(245, 245, 245), font=font)
            if sample.beat:
                draw.text((x0 + pad, y0 + frame_h + 47), sample.beat[:58], fill=(175, 180, 190), font=small_font)
            if has_findings:
                summary = ", ".join(f"{f.get('region', f.get('type'))}" for f in review_findings(sample.findings)[:3])
                draw.text((x0 + pad, y0 + frame_h + 70), f"review: {summary[:54]}", fill=(255, 160, 120), font=small_font)

        out_path = sheets_dir / f"contact_sheet_{sheet_index:02d}.png"
        sheet.save(out_path, "PNG", optimize=True)
        sheet_paths.append(out_path)

    return sheet_paths


def write_blocked_ranges(report: dict[str, Any], out_dir: Path, padding: float) -> Path | None:
    source_samples = [
        s
        for s in report["samples"]
        if s.get("mode") == "source" and review_findings(s.get("findings", []))
    ]
    if not source_samples:
        return None

    by_source: dict[str, list[dict[str, Any]]] = {}
    for sample in source_samples:
        source_id = sample.get("source_id") or Path(sample.get("video", "")).stem
        start = max(0.0, float(sample["timestamp"]) - padding)
        end = float(sample["timestamp"]) + padding
        by_source.setdefault(source_id, []).append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "reason": "visual_qc_ocr_or_banner_finding",
                "sample_index": sample["index"],
                "output_time": sample.get("output_time"),
                "findings": review_findings(sample.get("findings", [])),
            }
        )

    data = {
        "created_at": utc_now(),
        "source": "visual_qc.py",
        "padding_s": padding,
        "ranges_by_source": by_source,
    }
    out_path = out_dir / "source_blocked_ranges.json"
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return out_path


def report_status(samples: list[Sample]) -> str:
    # The generated report is intentionally never auto-passed. A real agent/LLM
    # still has to view the contact sheets and mark the report pass/fail.
    return "needs_llm_review"


def build_recommendations(samples: list[Sample]) -> list[str]:
    recommendations = [
        "Agent/LLM must view every contact sheet before final render.",
        "If a source overlay or description text appears, trim around the marked timestamp or choose a cleaner nearby transcript range.",
        "If a caption or crop collision appears in the rendered preview, reframe or rebuild captions, then render another preview and rerun visual QC.",
    ]
    all_findings = [finding for sample in samples for finding in sample.findings]
    if any(finding.get("type") == "caption_face_collision_risk" for finding in all_findings):
        recommendations.append(
            "Move captions away from the flagged face zone or reframe the subject before marking visual QC as passed."
        )
    if any(finding.get("type") == "face_near_crop_edge" for finding in all_findings):
        recommendations.append(
            "Review flagged crop-edge faces; use a wider crop, alternate range, or reframing pass if the subject feels clipped."
        )
    if any(review_findings(sample.findings) for sample in samples):
        recommendations.append(
            "OCR/banner/face-safe-area findings are review flags, not automatic failures; use the frame images as the final decision source."
        )
    return recommendations


def write_markdown_report(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Visual QC Report",
        "",
        f"- Status: `{data['status']}`",
        f"- Scope: `{data['scope']}`",
        f"- Created at: {data['created_at']}",
        f"- OCR available: {'yes' if data['ocr']['available'] else 'no'}",
        f"- Face detection available: {'yes' if data.get('face_detection', {}).get('available') else 'no'}",
        f"- Caption safe zone: `{data.get('face_detection', {}).get('caption_zone', 'unknown')}`",
        f"- Agent reviewed: {'yes' if data['visual_review']['reviewed_by_agent'] else 'no'}",
        "",
        "## Contact Sheets",
        "",
    ]
    for sheet in data.get("contact_sheets", []):
        lines.append(f"- `{sheet}`")

    lines.extend(["", "## Review Checklist", ""])
    lines.extend(
        [
            "- Source overlays, description text, burned-in social UI, watermarks, or lower-thirds that should not ship.",
            "- Caption collisions with faces, products, proof visuals, UI, or existing text.",
            "- Face boxes should stay out of the caption safe zone unless captions are moved or suppressed.",
            "- Faces near crop edges should be reframed or replaced when they feel clipped.",
            "- Bad crops, awkward jump frames, flashes, freeze frames, or unreadable cut moments.",
            "- Any flagged OCR/banner/face-safe-area sample below.",
        ]
    )

    lines.extend(["", "## Findings", ""])
    flagged = [sample for sample in data["samples"] if review_findings(sample.get("findings", []))]
    if not flagged:
        lines.append("- No automated OCR/banner/face-safe-area findings. Visual review is still required.")
    for sample in flagged:
        where = f"{sample['label']}"
        if sample.get("output_time") is not None:
            where += f" / output {sample['output_time']:.2f}s"
        lines.append(f"- Sample {sample['index']:02d}: {where}")
        for finding in review_findings(sample.get("findings", [])):
            text = finding.get("text")
            detail = f"{finding.get('type')} in {finding.get('region', 'frame')} ({finding.get('severity')})"
            if text:
                detail += f": {text}"
            lines.append(f"  - {detail}")

    lines.extend(["", "## Recommended Actions", ""])
    lines.extend(f"- {item}" for item in data.get("recommendations", []))

    notes = data.get("visual_review", {}).get("notes")
    if notes:
        lines.extend(["", "## Agent Review Notes", "", str(notes)])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_report(args: argparse.Namespace) -> dict[str, Any]:
    if not args.video and not args.source_preflight:
        raise SystemExit("provide --video for rendered-preview QC or --source-preflight with --edl")
    if args.source_preflight and not args.edl:
        raise SystemExit("--source-preflight requires --edl")

    edl_path = args.edl.resolve() if args.edl else None
    edl = load_edl(edl_path)
    if edl_path:
        out_dir = (args.output_dir or edl_path.parent / "visual_qc").resolve()
    else:
        video = args.video.resolve()
        out_dir = (args.output_dir or video.parent / "visual_qc").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.source_preflight:
        samples = make_source_samples(edl_path, edl, args.interval, args.max_frames)  # type: ignore[arg-type]
        scope = "source_preflight"
        json_path = out_dir / "source_visual_qc_report.json"
        md_path = out_dir / "source_visual_qc_report.md"
    else:
        video = args.video.resolve()
        if not video.exists():
            raise SystemExit(f"video not found: {video}")
        samples = make_render_samples(video, edl, args.interval, args.max_frames)
        scope = "render_preview"
        json_path = out_dir / "visual_qc_report.json"
        md_path = out_dir / "visual_qc_report.md"

    frames_dir = out_dir / "frames"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for sample in samples:
            frame_name = (
                f"{sample.index:03d}_{sample.mode}_"
                f"{sample.source_id or 'render'}_{sample.timestamp:.2f}.jpg"
            ).replace("/", "_")
            temp_frame = tmp_dir / frame_name
            if extract_frame(sample.video, sample.timestamp, temp_frame, args.frame_width):
                final_frame = frames_dir / frame_name
                final_frame.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(temp_frame, final_frame)
                sample.frame_path = final_frame
                analyze_sample(
                    sample,
                    ocr=not args.no_ocr,
                    face_detect=not args.no_face_detect,
                    caption_zone=args.caption_zone,
                )

    contact_sheets = make_contact_sheets(
        samples,
        out_dir,
        frames_per_sheet=args.frames_per_sheet,
        columns=args.columns,
        caption_zone=args.caption_zone,
    )
    report = {
        "created_at": utc_now(),
        "status": report_status(samples),
        "scope": scope,
        "edl": str(edl_path) if edl_path else None,
        "edl_sha256": sha256_file(edl_path) if edl_path and edl_path.exists() else None,
        "checked_video": str(args.video.resolve()) if args.video else None,
        "ocr": {
            "available": has_tesseract(),
            "enabled": not args.no_ocr,
            "engine": shutil.which("tesseract"),
        },
        "face_detection": {
            "available": face_detection_available(),
            "enabled": not args.no_face_detect,
            "engine": "opencv_haar_frontalface_default" if face_detection_available() else None,
            "caption_zone": args.caption_zone,
            "caption_zone_box": selected_caption_zone(args.caption_zone),
        },
        "visual_review": {
            "reviewed_by_agent": False,
            "reviewed_at": None,
            "reviewer": None,
            "notes": None,
        },
        "contact_sheets": [str(path) for path in contact_sheets],
        "samples": [sample_to_json(sample) for sample in samples],
        "recommendations": build_recommendations(samples),
    }

    blocked_ranges = write_blocked_ranges(report, out_dir, args.block_padding)
    if blocked_ranges:
        report["source_blocked_ranges"] = str(blocked_ranges)

    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown_report(md_path, report)
    print(json.dumps({"report": str(md_path), "json": str(json_path), "status": report["status"]}, indent=2))
    return report


def mark_reviewed(args: argparse.Namespace) -> None:
    report_path = args.mark_reviewed.resolve()
    if not report_path.exists():
        raise SystemExit(f"report not found: {report_path}")
    if args.status not in STATUSES - {"needs_llm_review"}:
        raise SystemExit("--status must be pass, needs_reclip, needs_reframe, needs_mask, or blocked")

    data = json.loads(report_path.read_text(encoding="utf-8"))
    data["status"] = args.status
    data.setdefault("visual_review", {})
    data["visual_review"].update(
        {
            "reviewed_by_agent": True,
            "reviewed_at": utc_now(),
            "reviewer": "agent_llm",
            "notes": args.notes or "",
        }
    )
    report_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    md_path = report_path.with_suffix(".md")
    write_markdown_report(md_path, data)
    print(json.dumps({"report": str(md_path), "json": str(report_path), "status": data["status"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or mark visual QC reports for video edits.")
    parser.add_argument("--video", type=Path, help="Rendered preview/output video to inspect.")
    parser.add_argument("--edl", type=Path, help="EDL used to compute source ranges/cut-boundary samples.")
    parser.add_argument("--source-preflight", action="store_true", help="Inspect the EDL source ranges instead of a rendered video.")
    parser.add_argument("--output-dir", type=Path, help="Directory for visual_qc outputs. Default: <edit>/visual_qc.")
    parser.add_argument("--interval", type=float, default=3.0, help="Regular sampling interval in seconds.")
    parser.add_argument("--max-frames", type=int, default=72, help="Maximum frames to sample.")
    parser.add_argument("--frame-width", type=int, default=960, help="Extracted frame width before contact sheet/OCR.")
    parser.add_argument("--frames-per-sheet", type=int, default=12, help="Number of frames per contact sheet.")
    parser.add_argument("--columns", type=int, default=3, help="Contact sheet columns.")
    parser.add_argument("--block-padding", type=float, default=0.8, help="Padding around flagged source timestamps in source_blocked_ranges.json.")
    parser.add_argument("--no-ocr", action="store_true", help="Skip OCR even when pytesseract/tesseract are available.")
    parser.add_argument("--no-face-detect", action="store_true", help="Skip lightweight OpenCV face/safe-area detection.")
    parser.add_argument(
        "--caption-zone",
        choices=["lower", "center", "none"],
        default="lower",
        help="Caption safe zone to draw/check against detected faces. Default: lower.",
    )
    parser.add_argument("--mark-reviewed", type=Path, help="Mark an existing JSON report after the agent/LLM has viewed the contact sheets.")
    parser.add_argument("--status", choices=sorted(STATUSES - {"needs_llm_review"}), help="Review result when using --mark-reviewed.")
    parser.add_argument("--notes", help="Agent review notes when using --mark-reviewed.")
    args = parser.parse_args()

    if args.mark_reviewed:
        if not args.status:
            raise SystemExit("--mark-reviewed requires --status")
        mark_reviewed(args)
        return

    generate_report(args)


if __name__ == "__main__":
    main()
