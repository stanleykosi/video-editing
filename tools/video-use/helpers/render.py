"""Render a video from an EDL.

Implements the HEURISTICS render pipeline in the correct order:

  1. Per-segment extract with color grade + 30ms audio fades baked in
  2. Lossless -c copy concat into base.mp4
  3. If overlays or subtitles: single filter graph that overlays animations
     (with PTS shift so frame 0 lands at the overlay window start)
     and applies `subtitles` filter LAST → final.mp4

Optionally builds a styled master ASS subtitle file from the per-source
transcripts + EDL output-timeline offsets. Caption style and font role are
resolved from root `presets/captions/ass_caption_styles.json`, not hardcoded.

Usage:
    python helpers/render.py <edl.json> -o final.mp4
    python helpers/render.py <edl.json> -o final_4k.mp4 --resolution 3840x2160
    python helpers/render.py <edl.json> -o preview.mp4 --preview
    python helpers/render.py <edl.json> -o final.mp4 --build-subtitles --caption-style editorial_serif
    python helpers/render.py --list-caption-styles
    python helpers/render.py <edl.json> -o final.mp4 --no-subtitles

Final renders default to the highest source resolution used by the EDL, with a
1080-pixel minimum on the short edge. Draft and preview modes intentionally use
lighter render sizes for fast QC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    from grade import get_preset, auto_grade_for_clip  # same directory
except Exception:
    def get_preset(name: str) -> str:
        return ""

    def auto_grade_for_clip(video, start=0.0, duration=None, verbose=False):  # type: ignore
        return "eq=contrast=1.03:saturation=0.98", {}

from caption_styles import available_caption_styles, build_master_ass, srt_force_style

# -------- Helpers ------------------------------------------------------------


def run(cmd: list[str], quiet: bool = False) -> None:
    if not quiet:
        print(f"  $ {' '.join(str(c) for c in cmd[:6])}{' …' if len(cmd) > 6 else ''}")
    subprocess.run(cmd, check=True)


def resolve_grade_filter(grade_field: str | None) -> str:
    """The EDL's 'grade' field can be a preset name, a raw ffmpeg filter, or 'auto'.

    Returns the filter string to embed into the per-segment -vf chain.
    For 'auto', returns the sentinel "__AUTO__" which is resolved per-segment.
    """
    if not grade_field:
        return ""
    if grade_field == "auto":
        return "__AUTO__"
    # Preset names are short identifiers, filter strings contain '=' or ','.
    if re.fullmatch(r"[a-zA-Z0-9_\-]+", grade_field):
        try:
            return get_preset(grade_field)
        except KeyError:
            print(f"warning: unknown preset '{grade_field}', using as raw filter")
            return grade_field
    return grade_field


def resolve_path(maybe_path: str, base: Path) -> Path:
    """Resolve a path that may be absolute or relative to `base`."""
    p = Path(maybe_path)
    if p.is_absolute():
        return p
    return (base / p).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_visual_qc_passed(edl_path: Path, edit_dir: Path) -> None:
    """Block final renders until an agent-reviewed visual QC report passes."""
    report_path = edit_dir / "visual_qc" / "visual_qc_report.json"
    guidance = (
        "Run a preview, generate visual QC, view every contact sheet, then mark it pass:\n"
        f"  python helpers/visual_qc.py --video {edit_dir / 'preview.mp4'} --edl {edl_path}\n"
        f"  python helpers/visual_qc.py --mark-reviewed {report_path} --status pass --notes \"reviewed contact sheets\""
    )
    if not report_path.exists():
        sys.exit(f"visual QC gate failed: missing {report_path}\n{guidance}")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        sys.exit(f"visual QC gate failed: invalid {report_path}: {exc}\n{guidance}")

    status = report.get("status")
    reviewed = bool(report.get("visual_review", {}).get("reviewed_by_agent"))
    if status != "pass" or not reviewed:
        sys.exit(
            "visual QC gate failed: report must be agent-reviewed with status `pass` "
            f"(found status={status!r}, reviewed={reviewed}).\n{guidance}"
        )

    report_hash = report.get("edl_sha256")
    if report_hash and report_hash != sha256_file(edl_path):
        sys.exit(
            "visual QC gate failed: EDL changed after the visual QC report was generated. "
            "Render a new preview and rerun visual QC."
        )


# -------- HDR → SDR tone mapping (HLG / PQ sources) --------------------------
#
# iPhone defaults to HLG HDR in Rec.2020 (and many mirrorless cameras ship PQ).
# If the source is HDR and we only downconvert bit depth (yuv420p10le → yuv420p)
# without tone-mapping, the output is 8-bit but still carries HLG/PQ transfer
# metadata. Players that honor the metadata (screen recorders, most social
# upload re-encodes) interpret 8-bit values in an HDR container and the result
# looks oversaturated / blown out. QuickTime on macOS can hide this locally —
# screen recording and uploaded renders cannot.
#
# Fix: detect HDR via color_transfer and prepend a zscale+tonemap chain to the
# vf graph so the output is clean Rec.709 SDR.

HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}  # PQ (HDR10) and HLG

TONEMAP_CHAIN = (
    "zscale=t=linear:npl=100,"
    "format=gbrpf32le,"
    "zscale=p=bt709,"
    "tonemap=tonemap=hable:desat=0,"
    "zscale=t=bt709:m=bt709:r=tv,"
    "format=yuv420p"
)


def is_hdr_source(video: Path) -> bool:
    """Return True if the source uses a PQ or HLG transfer function."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=color_transfer",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip() in HDR_TRANSFERS
    except subprocess.CalledProcessError:
        return False


def is_portrait_source(video: Path) -> bool:
    """Return True if the video's height > width (portrait / vertical)."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "csv=p=0", str(video)],
            capture_output=True, text=True, check=True,
        )
        w, h = map(int, out.stdout.strip().split(","))
        return h > w
    except Exception:
        return False


def video_dimensions(video: Path) -> tuple[int, int]:
    """Return source video dimensions as (width, height)."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "csv=p=0", str(video)],
            capture_output=True, text=True, check=True,
        )
        w, h = map(int, out.stdout.strip().split(","))
        return w, h
    except Exception:
        return 1920, 1080


def even_dimension(value: int) -> int:
    return max(2, int(value) - (int(value) % 2))


def parse_resolution(value) -> tuple[int, int] | None:
    """Parse common resolution shapes: '3840x2160', [3840,2160], or dict."""
    if not value:
        return None
    if isinstance(value, str):
        match = re.search(r"(\d{3,5})\s*[xX]\s*(\d{3,5})", value)
        if not match:
            return None
        return even_dimension(int(match.group(1))), even_dimension(int(match.group(2)))
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return even_dimension(int(value[0])), even_dimension(int(value[1]))
    if isinstance(value, dict):
        width = value.get("width") or value.get("w")
        height = value.get("height") or value.get("h")
        if width and height:
            return even_dimension(int(width)), even_dimension(int(height))
    return None


def requested_output_resolution(edl: dict) -> tuple[int, int] | None:
    """Read an explicit output resolution from EDL-level render settings."""
    for key in ("resolution", "output_resolution", "target_resolution"):
        parsed = parse_resolution(edl.get(key))
        if parsed:
            return parsed
    for container_key in ("render", "output", "export"):
        container = edl.get(container_key)
        if isinstance(container, dict):
            for key in ("resolution", "output_resolution", "target_resolution"):
                parsed = parse_resolution(container.get(key))
                if parsed:
                    return parsed
    return None


def output_fit_mode(edl: dict) -> str:
    """How to fit sources into an explicit/common target resolution."""
    for key in ("output_fit", "fit"):
        value = edl.get(key)
        if isinstance(value, str):
            return value.lower()
    for container_key in ("render", "output", "export"):
        container = edl.get(container_key)
        if isinstance(container, dict):
            value = container.get("fit") or container.get("output_fit")
            if isinstance(value, str):
                return value.lower()
    return "cover"


def clamp_focus(value: object, default: float = 0.5) -> float:
    try:
        focus = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, focus))


def output_focus(edl: dict, range_item: dict | None = None) -> tuple[float, float]:
    """Read per-range or EDL-level crop focus for cover-fit reframes.

    `focus_x=0` means keep the left side after scaling, `0.5` centers, and `1`
    keeps the right side. `focus_y` follows the same top/center/bottom pattern.
    This lets landscape interviews become vertical shorts without always using a
    blind center crop.
    """
    candidates: list[dict] = []
    if isinstance(range_item, dict):
        candidates.append(range_item)
        reframe = range_item.get("reframe")
        if isinstance(reframe, dict):
            candidates.append(reframe)
    for container_key in ("render", "output", "export", "reframe"):
        container = edl.get(container_key)
        if isinstance(container, dict):
            candidates.append(container)
    candidates.append(edl)

    focus_x: object | None = None
    focus_y: object | None = None
    for candidate in candidates:
        if focus_x is None:
            focus_x = (
                candidate.get("focus_x")
                or candidate.get("crop_focus_x")
                or candidate.get("output_focus_x")
            )
        if focus_y is None:
            focus_y = (
                candidate.get("focus_y")
                or candidate.get("crop_focus_y")
                or candidate.get("output_focus_y")
            )
    return clamp_focus(focus_x, 0.5), clamp_focus(focus_y, 0.5)


def highest_source_resolution(edl: dict, edit_dir: Path) -> tuple[int, int]:
    """Use the highest pixel-count source referenced by the EDL ranges."""
    sources = edl.get("sources", {})
    source_ids = [r.get("source") for r in edl.get("ranges", []) if r.get("source") in sources]
    if not source_ids:
        source_ids = list(sources)

    best: tuple[int, int] | None = None
    for source_id in source_ids:
        dims = video_dimensions(resolve_path(sources[source_id], edit_dir))
        if best is None or dims[0] * dims[1] > best[0] * best[1]:
            best = dims

    if best is None:
        return 1920, 1080
    return even_dimension(best[0]), even_dimension(best[1])


def upscale_to_min_short_edge(
    dimensions: tuple[int, int],
    min_short_edge: int = 1080,
) -> tuple[int, int]:
    """Preserve aspect ratio while guaranteeing at least 1080p-class output."""
    width, height = dimensions
    short_edge = min(width, height)
    if short_edge >= min_short_edge:
        return even_dimension(width), even_dimension(height)

    scale = min_short_edge / short_edge
    return even_dimension(round(width * scale)), even_dimension(round(height * scale))


def final_output_resolution(edl: dict, edit_dir: Path) -> tuple[int, int]:
    requested = requested_output_resolution(edl)
    if requested:
        return requested
    return upscale_to_min_short_edge(highest_source_resolution(edl, edit_dir))



def scale_filter_for_target(
    source: Path,
    target: tuple[int, int],
    fit: str,
    focus_x: float = 0.5,
    focus_y: float = 0.5,
) -> str:
    """Build a non-distorting scale filter for final common-resolution renders."""
    src_w, src_h = video_dimensions(source)
    out_w, out_h = target
    if (even_dimension(src_w), even_dimension(src_h)) == (out_w, out_h):
        return ""

    if fit == "stretch":
        return f"scale={out_w}:{out_h}:flags=lanczos"
    if fit == "contain":
        return (
            f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2"
        )

    return (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={out_w}:{out_h}:(iw-{out_w})*{focus_x:.4f}:(ih-{out_h})*{focus_y:.4f}"
    )


def manual_crop_filter_for_range(
    range_item: dict | None,
    target_resolution: tuple[int, int] | None,
) -> str:
    """Build a crop/scale filter from an EDL range's explicit crop box.

    This is useful when the delivery aspect matches the source but a source
    overlay, subtitle band, or edge artifact still needs a controlled zoom.

    EDL shape:
      {"crop": {"x": 160, "y": 0, "w": 1600, "h": 900}}

    Aliases `left`, `top`, `width`, and `height` are also accepted.
    """
    if not isinstance(range_item, dict):
        return ""
    crop = range_item.get("crop")
    if not isinstance(crop, dict):
        return ""

    def even_positive(value: object, default: int | None = None) -> int | None:
        if value is None:
            return default
        try:
            parsed = int(round(float(value)))
        except (TypeError, ValueError):
            return default
        return even_dimension(max(2, parsed))

    def even_offset(value: object, default: int = 0) -> int:
        try:
            parsed = int(round(float(value)))
        except (TypeError, ValueError):
            parsed = default
        return max(0, parsed - (parsed % 2))

    width = even_positive(crop.get("w", crop.get("width")))
    height = even_positive(crop.get("h", crop.get("height")))
    if width is None or height is None:
        return ""

    x = even_offset(crop.get("x", crop.get("left", 0)))
    y = even_offset(crop.get("y", crop.get("top", 0)))
    parts = [f"crop={width}:{height}:{x}:{y}"]
    if target_resolution:
        out_w, out_h = target_resolution
        parts.append(f"scale={out_w}:{out_h}:flags=lanczos")
    return ",".join(parts)


# -------- Per-segment extraction (Rule 2 + Rule 3) --------------------------


def extract_segment(
    source: Path,
    seg_start: float,
    duration: float,
    grade_filter: str,
    out_path: Path,
    preview: bool = False,
    draft: bool = False,
    target_resolution: tuple[int, int] | None = None,
    fit: str = "cover",
    focus_x: float = 0.5,
    focus_y: float = 0.5,
    manual_crop_filter: str = "",
) -> None:
    """Extract a cut range as its own MP4 with grade + 30ms audio fades baked in.

    `-ss` before `-i` for fast accurate seeking.

    Quality ladder:
      - final (default): highest EDL source resolution, libx264 fast CRF 20
      - preview:         explicit EDL/CLI target when set, otherwise 1080p-ish
                         libx264 medium CRF 22 (evaluable for QC)
      - draft:           720p libx264 ultrafast CRF 28 (cut-point check only)
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    portrait = is_portrait_source(source)
    if draft:
        scale = "scale=-2:1280" if portrait else "scale=1280:-2"
    elif target_resolution:
        scale = scale_filter_for_target(source, target_resolution, fit, focus_x=focus_x, focus_y=focus_y)
    elif preview:
        scale = "scale=-2:1920" if portrait else "scale=1920:-2"
    else:
        scale = ""

    vf_parts: list[str] = []
    if is_hdr_source(source):
        vf_parts.append(TONEMAP_CHAIN)
    if manual_crop_filter:
        vf_parts.append(manual_crop_filter)
    elif scale:
        vf_parts.append(scale)
    if grade_filter:
        vf_parts.append(grade_filter)
    vf = ",".join(vf_parts)

    # 30ms audio fades at both edges (Rule 3) — prevent pops
    fade_out_start = max(0.0, duration - 0.03)
    af = f"afade=t=in:st=0:d=0.03,afade=t=out:st={fade_out_start:.3f}:d=0.03"

    if draft:
        preset, crf = "ultrafast", "28"
    elif preview:
        preset, crf = "medium", "22"
    else:
        preset, crf = "fast", "20"

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{seg_start:.3f}",
        "-i", str(source),
        "-t", f"{duration:.3f}",
        "-af", af,
        "-c:v", "libx264", "-preset", preset, "-crf", crf,
        "-pix_fmt", "yuv420p", "-r", "24",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(out_path),
    ]
    if vf:
        cmd[8:8] = ["-vf", vf]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def extract_all_segments(
    edl: dict,
    edit_dir: Path,
    preview: bool,
    draft: bool = False,
) -> list[Path]:
    """Extract every EDL range into edit_dir/clips_graded/seg_NN.mp4.
    Returns the ordered list of segment paths.

    If the EDL `grade` is "auto", analyze each segment range with
    `auto_grade_for_clip` and apply a per-segment subtle correction.
    Otherwise, apply the same preset/raw filter to every segment.
    """
    resolved = resolve_grade_filter(edl.get("grade"))
    is_auto = resolved == "__AUTO__"
    clips_dir = edit_dir / (
        "clips_draft" if draft else ("clips_preview" if preview else "clips_graded")
    )
    clips_dir.mkdir(parents=True, exist_ok=True)

    ranges = edl["ranges"]
    sources = edl["sources"]
    has_explicit_target = requested_output_resolution(edl) is not None
    target_resolution = (
        final_output_resolution(edl, edit_dir)
        if (not draft and (not preview or has_explicit_target))
        else None
    )
    fit = output_fit_mode(edl)

    seg_paths: list[Path] = []
    print(f"extracting {len(ranges)} segment(s) → {clips_dir.name}/")
    if target_resolution:
        target_kind = "preview target" if preview else "final target"
        print(f"  {target_kind} resolution: {target_resolution[0]}x{target_resolution[1]} ({fit})")
    if is_auto:
        print("  (auto-grade per segment: analyzing each range)")
    for i, r in enumerate(ranges):
        src_name = r["source"]
        src_path = resolve_path(sources[src_name], edit_dir)
        start = float(r["start"])
        end = float(r["end"])
        duration = end - start
        out_path = clips_dir / f"seg_{i:02d}_{src_name}.mp4"

        if is_auto:
            seg_filter, _stats = auto_grade_for_clip(src_path, start=start, duration=duration, verbose=False)
        else:
            seg_filter = resolved

        focus_x, focus_y = output_focus(edl, r)
        manual_crop_filter = manual_crop_filter_for_range(r, target_resolution)
        note = r.get("beat") or r.get("note") or ""
        print(
            f"  [{i:02d}] {src_name}  {start:7.2f}-{end:7.2f}  "
            f"({duration:5.2f}s)  focus=({focus_x:.2f},{focus_y:.2f})  {note}"
        )
        if manual_crop_filter:
            print(f"        crop: {manual_crop_filter}")
        if is_auto:
            print(f"        grade: {seg_filter or '(none)'}")
        extract_segment(
            src_path,
            start,
            duration,
            seg_filter,
            out_path,
            preview=preview,
            draft=draft,
            target_resolution=target_resolution,
            fit=fit,
            focus_x=focus_x,
            focus_y=focus_y,
            manual_crop_filter=manual_crop_filter,
        )
        seg_paths.append(out_path)

    return seg_paths


# -------- Lossless concat ----------------------------------------------------


def concat_segments(segment_paths: list[Path], out_path: Path, edit_dir: Path) -> None:
    """Lossless concat via the concat demuxer. No re-encode."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    concat_list = edit_dir / "_concat.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in segment_paths))

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ]
    print(f"concat → {out_path.name}")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    concat_list.unlink(missing_ok=True)


# -------- Master SRT (Rule 5) ------------------------------------------------


PUNCT_BREAK = set(".,!?;:")


def _srt_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    h, rem = divmod(total_ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _words_in_range(transcript: dict, t_start: float, t_end: float) -> list[dict]:
    out: list[dict] = []
    for w in transcript.get("words", []):
        if w.get("type") != "word":
            continue
        ws = w.get("start")
        we = w.get("end")
        if ws is None or we is None:
            continue
        if we <= t_start or ws >= t_end:
            continue
        out.append(w)
    return out


def build_master_srt(edl: dict, edit_dir: Path, out_path: Path) -> None:
    """Build an output-timeline SRT from per-source transcripts.

    - 2-word chunks (break on any punctuation in between)
    - UPPERCASE text
    - Output times computed as word.start - segment_start + segment_offset
    """
    transcripts_dir = edit_dir / "transcripts"
    sources = edl["sources"]

    entries: list[tuple[float, float, str]] = []
    seg_offset = 0.0

    for r in edl["ranges"]:
        src_name = r["source"]
        seg_start = float(r["start"])
        seg_end = float(r["end"])
        seg_duration = seg_end - seg_start

        tr_path = transcripts_dir / f"{src_name}.json"
        if not tr_path.exists():
            print(f"  no transcript for {src_name}, skipping captions for this segment")
            seg_offset += seg_duration
            continue

        transcript = json.loads(tr_path.read_text())
        words_in_seg = _words_in_range(transcript, seg_start, seg_end)

        # Group into 2-word chunks, break on punctuation
        chunks: list[list[dict]] = []
        current: list[dict] = []
        for w in words_in_seg:
            text = (w.get("text") or "").strip()
            if not text:
                continue
            current.append(w)
            # Break if the current text ends in punctuation or we hit 2 words
            ends_in_punct = bool(text) and text[-1] in PUNCT_BREAK
            if len(current) >= 2 or ends_in_punct:
                chunks.append(current)
                current = []
        if current:
            chunks.append(current)

        for chunk in chunks:
            local_start = max(seg_start, chunk[0].get("start", seg_start))
            local_end = min(seg_end, chunk[-1].get("end", seg_end))
            out_start = max(0.0, local_start - seg_start) + seg_offset
            out_end = max(0.0, local_end - seg_start) + seg_offset
            if out_end <= out_start:
                out_end = out_start + 0.4
            text = " ".join((w.get("text") or "").strip() for w in chunk)
            text = re.sub(r"\s+", " ", text).strip()
            # Strip trailing punctuation for cleaner uppercase look
            text = text.rstrip(",;:")
            text = text.upper()
            entries.append((out_start, out_end, text))

        seg_offset += seg_duration

    # Sort and write as SRT
    entries.sort(key=lambda e: e[0])
    lines: list[str] = []
    for i, (a, b, t) in enumerate(entries, start=1):
        lines.append(str(i))
        lines.append(f"{_srt_timestamp(a)} --> {_srt_timestamp(b)}")
        lines.append(t)
        lines.append("")
    out_path.write_text("\n".join(lines))
    print(f"master SRT → {out_path.name} ({len(entries)} cues)")


# -------- Loudness normalization (social-ready audio) -----------------------


# Social-media standard: -14 LUFS integrated, -1 dBTP peak, LRA 11 LU.
# Matches YouTube / Instagram / TikTok / X / LinkedIn normalization targets.
LOUDNORM_I = -14.0
LOUDNORM_TP = -1.0
LOUDNORM_LRA = 11.0


def measure_loudness(video_path: Path) -> dict[str, str] | None:
    """Run ffmpeg loudnorm first pass and parse the JSON measurement.

    Returns a dict with measured_i, measured_tp, measured_lra, measured_thresh,
    target_offset, or None if measurement failed.
    """
    filter_str = (
        f"loudnorm=I={LOUDNORM_I}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}:print_format=json"
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-nostats",
        "-i", str(video_path),
        "-af", filter_str,
        "-vn", "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # loudnorm prints the JSON to stderr at the end of the run
    stderr = proc.stderr

    # Find the JSON block — loudnorm output contains a `{ ... }` block
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        data = json.loads(stderr[start : end + 1])
    except json.JSONDecodeError:
        return None
    needed = {"input_i", "input_tp", "input_lra", "input_thresh", "target_offset"}
    if not needed.issubset(data.keys()):
        return None
    return data


def apply_loudnorm_two_pass(
    input_path: Path,
    output_path: Path,
    preview: bool = False,
) -> bool:
    """Run two-pass loudnorm on input_path, write normalized copy to output_path.

    Returns True on success, False if measurement failed (caller should fall
    back to copying the input unchanged).

    In preview mode, skips the measurement pass and uses a one-pass approximation
    for speed. Final mode always does the proper two-pass.
    """
    if preview:
        # One-pass approximation — faster, slightly less accurate.
        filter_str = f"loudnorm=I={LOUDNORM_I}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}"
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-nostats",
            "-i", str(input_path),
            "-c:v", "copy",
            "-af", filter_str,
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart",
            str(output_path),
        ]
        print(f"  loudnorm (1-pass preview) → {output_path.name}")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True

    # Full two-pass
    print(f"  loudnorm pass 1: measuring {input_path.name}")
    measurement = measure_loudness(input_path)
    if measurement is None:
        print("  loudnorm measurement failed — falling back to 1-pass")
        return apply_loudnorm_two_pass(input_path, output_path, preview=True)

    print(f"    measured: I={measurement['input_i']} LUFS  "
          f"TP={measurement['input_tp']}  LRA={measurement['input_lra']}")

    filter_str = (
        f"loudnorm=I={LOUDNORM_I}:TP={LOUDNORM_TP}:LRA={LOUDNORM_LRA}"
        f":measured_I={measurement['input_i']}"
        f":measured_TP={measurement['input_tp']}"
        f":measured_LRA={measurement['input_lra']}"
        f":measured_thresh={measurement['input_thresh']}"
        f":offset={measurement['target_offset']}"
        f":linear=true"
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-nostats",
        "-i", str(input_path),
        "-c:v", "copy",
        "-af", filter_str,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(output_path),
    ]
    print(f"  loudnorm pass 2: normalizing → {output_path.name}")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return True


# -------- Final compositing (Rule 1 + Rule 4) -------------------------------


def build_final_composite(
    base_path: Path,
    overlays: list[dict],
    subtitles_path: Path | None,
    out_path: Path,
    edit_dir: Path,
    edl: dict | None = None,
    caption_style_id: str | None = None,
    sound_effects: list[dict] | None = None,
    preview: bool = False,
    draft: bool = False,
) -> None:
    """Final pass: base → overlays (PTS-shifted) → subtitles LAST → out.

    If there are no overlays and no subtitles, just copy base to out.
    """
    has_overlays = bool(overlays)
    has_subs = subtitles_path is not None and subtitles_path.exists()
    sound_effects = sound_effects or []
    has_sfx = bool(sound_effects)

    if not has_overlays and not has_subs and not has_sfx:
        # Nothing to do — just rename/copy base to final name
        run(["ffmpeg", "-y", "-i", str(base_path), "-c", "copy", str(out_path)], quiet=True)
        return

    inputs: list[str] = ["-i", str(base_path)]
    for ov in overlays:
        ov_path = resolve_path(ov["file"], edit_dir)
        inputs += ["-i", str(ov_path)]
    sfx_input_start = 1 + len(overlays)
    for effect in sound_effects:
        effect_path = resolve_path(effect["file"], edit_dir)
        inputs += ["-i", str(effect_path)]

    filter_parts: list[str] = []
    # PTS-shift every overlay so its frame 0 lands at start_in_output
    for idx, ov in enumerate(overlays, start=1):
        t = float(ov["start_in_output"])
        filter_parts.append(f"[{idx}:v]setpts=PTS-STARTPTS+{t}/TB[a{idx}]")

    # Chain overlays on top of base
    current = "[0:v]"
    for idx, ov in enumerate(overlays, start=1):
        t = float(ov["start_in_output"])
        dur = float(ov["duration"])
        end = t + dur
        next_label = f"[v{idx}]"
        filter_parts.append(
            f"{current}[a{idx}]overlay=enable='between(t,{t:.3f},{end:.3f})'{next_label}"
        )
        current = next_label

    # Subtitles LAST — Rule 1
    if has_subs:
        subs_abs = str(subtitles_path.resolve()).replace(":", r"\:").replace("'", r"\'")
        if subtitles_path.suffix.lower() in {".ass", ".ssa"}:
            filter_parts.append(f"{current}subtitles='{subs_abs}'[outv]")
        else:
            force_style = srt_force_style(edl or {}, base_path, caption_style_id)
            force_style = force_style.replace(":", r"\:").replace("'", r"\'")
            filter_parts.append(
                f"{current}subtitles='{subs_abs}':force_style='{force_style}'[outv]"
            )
        out_label = "[outv]"
    else:
        # Rename the last overlay output to [outv] for consistency
        if has_overlays:
            filter_parts.append(f"{current}null[outv]")
            out_label = "[outv]"
        else:
            out_label = "0:v"

    if has_sfx:
        audio_labels = ["[0:a]"]
        for idx, effect in enumerate(sound_effects):
            input_idx = sfx_input_start + idx
            start_ms = max(0, int(round(float(effect.get("start_in_output", effect.get("start", 0.0))) * 1000)))
            gain = float(effect.get("gain", effect.get("volume", 1.0)))
            chain = f"[{input_idx}:a]asetpts=PTS-STARTPTS"
            if effect.get("duration") is not None:
                chain += f",atrim=0:{float(effect['duration']):.3f}"
            chain += f",adelay={start_ms}|{start_ms},volume={gain:g}[sfx{idx}]"
            filter_parts.append(chain)
            audio_labels.append(f"[sfx{idx}]")
        filter_parts.append(
            "".join(audio_labels)
            + f"amix=inputs={len(audio_labels)}:duration=first:dropout_transition=0[aout]"
        )
        audio_label = "[aout]"
    else:
        audio_label = "0:a"

    filter_complex = ";".join(filter_parts)

    if draft:
        video_preset, video_crf = "ultrafast", "28"
    elif preview:
        video_preset, video_crf = "fast", "22"
    else:
        video_preset, video_crf = "fast", "18"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
    ]
    if filter_complex:
        cmd += ["-filter_complex", filter_complex]
    cmd += [
        "-map", out_label,
        "-map", audio_label,
        "-c:v", "libx264", "-preset", video_preset, "-crf", video_crf,
        "-pix_fmt", "yuv420p",
    ]
    if has_sfx:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    else:
        cmd += ["-c:a", "copy"]
    cmd += [
        "-movflags", "+faststart",
        str(out_path),
    ]
    print(f"compositing → {out_path.name}")
    print(
        "  overlays: "
        f"{len(overlays)}, subtitles: {'yes' if has_subs else 'no'}, "
        f"sfx: {len(sound_effects)}"
    )
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


# -------- Main ---------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a video from an EDL")
    ap.add_argument("edl", type=Path, nargs="?", help="Path to edl.json")
    ap.add_argument("-o", "--output", type=Path, help="Output video path")
    ap.add_argument(
        "--preview",
        action="store_true",
        help="Preview mode: medium CRF 22, evaluable for QC; honors explicit EDL/CLI resolution.",
    )
    ap.add_argument(
        "--draft",
        action="store_true",
        help="Draft mode: 720p, ultrafast, CRF 28 — cut-point verification only.",
    )
    ap.add_argument(
        "--build-subtitles",
        action="store_true",
        help="Build master.ass from transcripts + EDL offsets before compositing",
    )
    ap.add_argument(
        "--caption-style",
        help="Caption style ID from presets/captions/ass_caption_styles.json",
    )
    ap.add_argument(
        "--resolution",
        help="Output resolution override, e.g. 1080x1920 or 3840x2160. Draft ignores this.",
    )
    ap.add_argument(
        "--fit",
        choices=["cover", "contain", "stretch"],
        help="How to fit sources into the final target resolution. Default: cover.",
    )
    ap.add_argument(
        "--list-caption-styles",
        action="store_true",
        help="List available caption styles and the font each role resolves to.",
    )
    ap.add_argument(
        "--no-subtitles",
        action="store_true",
        help="Skip subtitles even if the EDL references one",
    )
    ap.add_argument(
        "--no-loudnorm",
        action="store_true",
        help="Skip audio loudness normalization. Default is on (-14 LUFS, -1 dBTP, LRA 11).",
    )
    ap.add_argument(
        "--skip-visual-qc",
        action="store_true",
        help="Allow a final render without a passed visual_qc_report.json. Use only for diagnostics.",
    )
    args = ap.parse_args()

    if args.list_caption_styles:
        print(json.dumps(available_caption_styles(), indent=2))
        return

    if args.edl is None:
        sys.exit("edl is required unless --list-caption-styles is used")
    if args.output is None:
        sys.exit("--output is required unless --list-caption-styles is used")

    edl_path = args.edl.resolve()
    if not edl_path.exists():
        sys.exit(f"edl not found: {edl_path}")

    edl = json.loads(edl_path.read_text())
    if args.resolution:
        parsed_resolution = parse_resolution(args.resolution)
        if not parsed_resolution:
            sys.exit(f"invalid --resolution: {args.resolution}")
        edl["resolution"] = f"{parsed_resolution[0]}x{parsed_resolution[1]}"
    if args.fit:
        edl["output_fit"] = args.fit
    edit_dir = edl_path.parent
    out_path = args.output.resolve()

    if not args.preview and not args.draft and not args.skip_visual_qc:
        ensure_visual_qc_passed(edl_path, edit_dir)

    # 1. Extract per-segment (auto-grade per range if EDL grade is "auto")
    segment_paths = extract_all_segments(
        edl, edit_dir, preview=args.preview, draft=args.draft
    )

    # 2. Concat → base
    if args.draft:
        base_name = "base_draft.mp4"
    elif args.preview:
        base_name = "base_preview.mp4"
    else:
        base_name = "base.mp4"
    base_path = edit_dir / base_name
    concat_segments(segment_paths, base_path, edit_dir)

    # 3. Subtitles: build if requested, resolve final path
    subs_path: Path | None = None
    if not args.no_subtitles:
        if args.build_subtitles:
            subs_path = edit_dir / "master.ass"
            caption_info = build_master_ass(
                edl,
                edit_dir,
                subs_path,
                base_path,
                explicit_style_id=args.caption_style,
            )
            print(
                "master ASS → "
                f"{subs_path.name} ({caption_info['cues']} cues, "
                f"style={caption_info['style_id']}, font={caption_info['font_family']})"
            )
        elif edl.get("subtitles"):
            subs_path = resolve_path(edl["subtitles"], edit_dir)
            if not subs_path.exists():
                print(f"warning: subtitles path in EDL does not exist: {subs_path}")
                subs_path = None

    # 4. Composite (overlays + subtitles LAST) → intermediate (pre-loudnorm) path
    overlays = edl.get("overlays") or []
    sound_effects = edl.get("sound_effects") or edl.get("sfx") or []
    if args.no_loudnorm:
        # Composite directly to final output
        build_final_composite(
            base_path,
            overlays,
            subs_path,
            out_path,
            edit_dir,
            edl=edl,
            caption_style_id=args.caption_style,
            sound_effects=sound_effects,
            preview=args.preview,
            draft=args.draft,
        )
    else:
        # Composite to a temp file, then run loudnorm → final output
        tmp_composite = out_path.with_suffix(".prenorm.mp4")
        build_final_composite(
            base_path,
            overlays,
            subs_path,
            tmp_composite,
            edit_dir,
            edl=edl,
            caption_style_id=args.caption_style,
            sound_effects=sound_effects,
            preview=args.preview,
            draft=args.draft,
        )
        print("loudness normalization → social-ready (-14 LUFS / -1 dBTP / LRA 11)")
        apply_loudnorm_two_pass(tmp_composite, out_path, preview=args.draft)
        tmp_composite.unlink(missing_ok=True)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"\ndone: {out_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
