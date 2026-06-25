"""Render vertical social clips from podcast footage and word timestamps.

The helper is intentionally narrow:
- Input is a JSON spec with source/transcript paths and clip windows.
- Cuts are snapped to transcript word groups, removing gaps over 320 ms.
- Each extracted speech group gets 30 ms audio fades.
- Segments are concatenated losslessly before the final subtitle pass.
- ASS captions and first-frame text are burned in the final filter pass.

Usage:
    python helpers/render_vertical_podcast_clips.py spec.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


GAP_CUT_SECONDS = 0.32
EDGE_PAD_SECONDS = 0.06
OUT_W = 1080
OUT_H = 1920

KEYWORDS = {
    "ai",
    "agi",
    "jobs",
    "job",
    "openai",
    "anthropic",
    "oligarchs",
    "government",
    "future",
    "children",
    "brain",
    "claude",
    "twenty",
    "seven",
    "prediction",
    "human",
    "skills",
    "enemy",
    "model",
    "surveillance",
    "target",
    "dystopia",
}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def ass_time(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{c:02d}"


def esc_ass(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def clean_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def words_in_window(words: list[dict[str, Any]], start: float, end: float) -> list[dict[str, Any]]:
    return [
        w
        for w in words
        if w.get("type") == "word"
        and w.get("end") is not None
        and w.get("start") is not None
        and float(w["end"]) > start
        and float(w["start"]) < end
    ]


def speech_segments(words: list[dict[str, Any]], start: float, end: float) -> list[dict[str, Any]]:
    selected = words_in_window(words, start, end)
    if not selected:
        return []
    groups: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    last_end: float | None = None
    for w in selected:
        ws = float(w["start"])
        if cur and last_end is not None and ws - last_end > GAP_CUT_SECONDS:
            groups.append(cur)
            cur = []
        cur.append(w)
        last_end = float(w["end"])
    if cur:
        groups.append(cur)

    out: list[dict[str, Any]] = []
    for group in groups:
        seg_start = max(start, float(group[0]["start"]) - EDGE_PAD_SECONDS)
        seg_end = min(end, float(group[-1]["end"]) + EDGE_PAD_SECONDS)
        if seg_end - seg_start < 0.25:
            continue
        text = " ".join(str(w.get("text", "")) for w in group)
        out.append({"start": seg_start, "end": seg_end, "words": group, "text": text})
    return out


def segment_needs_punch(text: str, index: int) -> bool:
    low = text.lower()
    if any(k in low for k in ["twenty twenty seven", "brain", "oligarch", "openai", "children", "learn ai", "not the enemy"]):
        return True
    return index % 3 == 1


def vertical_filter(zoom: float) -> str:
    scaled_h = int(round(OUT_H * zoom / 2) * 2)
    # Scale source by height, center-crop to 9:16, then normalize exactly.
    return (
        f"scale=-2:{scaled_h},"
        f"crop={OUT_W}:{OUT_H}:(iw-{OUT_W})/2:(ih-{OUT_H})/2,"
        "eq=contrast=1.035:saturation=1.02,"
        "unsharp=5:5:0.45:3:3:0.15"
    )


def extract_segments(source: Path, clip_dir: Path, segments: list[dict[str, Any]]) -> list[Path]:
    clip_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for index, seg in enumerate(segments):
        duration = float(seg["end"]) - float(seg["start"])
        zoom = 1.06 if segment_needs_punch(seg["text"], index) else 1.0
        fade_out = max(0.0, duration - 0.03)
        out = clip_dir / f"seg_{index:03d}.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-nostats",
            "-ss",
            f"{seg['start']:.3f}",
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vertical_filter(zoom),
            "-af",
            f"afade=t=in:st=0:d=0.03,afade=t=out:st={fade_out:.3f}:d=0.03",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(out),
        ]
        run(cmd)
        outputs.append(out)
    return outputs


def concat_segments(paths: list[Path], out: Path) -> None:
    list_path = out.parent / "_concat_vertical.txt"
    list_path.write_text("".join(f"file '{p.resolve()}'\n" for p in paths), encoding="utf-8")
    try:
        run([
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-nostats",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(out),
        ])
    finally:
        list_path.unlink(missing_ok=True)


def caption_chunks(mapped_words: list[dict[str, Any]]) -> list[tuple[float, float, str]]:
    chunks: list[tuple[float, float, str]] = []
    current: list[dict[str, Any]] = []
    for w in mapped_words:
        token = str(w.get("text", "")).strip()
        if not token:
            continue
        if clean_token(token) in {"uh", "um", "mhmm"}:
            continue
        current.append(w)
        text = " ".join(str(x["text"]) for x in current)
        too_long = len(re.sub(r"[^A-Za-z0-9]", "", text)) > 18
        punct = token.endswith((".", "?", "!"))
        dur = float(current[-1]["out_end"]) - float(current[0]["out_start"])
        if len(current) >= 3 or too_long or punct or dur > 1.15:
            chunks.append(render_chunk(current))
            current = []
    if current:
        chunks.append(render_chunk(current))
    return chunks


def render_chunk(words: list[dict[str, Any]]) -> tuple[float, float, str]:
    start = float(words[0]["out_start"])
    end = max(float(words[-1]["out_end"]), start + 0.28)
    rendered: list[str] = []
    for w in words:
        raw = str(w["text"]).strip().rstrip(",;:")
        if not raw:
            continue
        word = raw.upper()
        if clean_token(raw) in KEYWORDS:
            word = r"{\c&H0000FFFF&}" + esc_ass(word) + r"{\c&H00FFFFFF&}"
        else:
            word = esc_ass(word)
        rendered.append(word)
    text = " ".join(rendered).rstrip(".")
    if len(" ".join(str(w["text"]) for w in words)) > 18 and len(rendered) > 1:
        mid = (len(rendered) + 1) // 2
        text = " ".join(rendered[:mid]) + r"\N" + " ".join(rendered[mid:])
    return start, end, text


def build_ass(
    ass_path: Path,
    title: str,
    segments: list[dict[str, Any]],
) -> tuple[float, list[dict[str, Any]]]:
    mapped_words: list[dict[str, Any]] = []
    offset = 0.0
    for seg in segments:
        seg_start = float(seg["start"])
        seg_end = float(seg["end"])
        for w in seg["words"]:
            ws = float(w["start"])
            we = float(w["end"])
            if we <= seg_start or ws >= seg_end:
                continue
            mapped = dict(w)
            mapped["out_start"] = max(0.0, ws - seg_start) + offset
            mapped["out_end"] = max(0.0, we - seg_start) + offset
            mapped_words.append(mapped)
        offset += seg_end - seg_start

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {OUT_W}",
        f"PlayResY: {OUT_H}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,DejaVu Sans,78,&H00FFFFFF,&H0000FFFF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,5,0,2,80,80,430,1",
        "Style: Header,DejaVu Sans,62,&H00FFFFFF,&H0000FFFF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,5,0,8,70,70,135,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    lines.append(
        f"Dialogue: 2,{ass_time(0)},{ass_time(min(3.2, max(1.0, offset)))},Header,,0,0,0,,{esc_ass(title.upper())}"
    )
    for start, end, text in caption_chunks(mapped_words):
        lines.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{text}")
    ass_path.write_text("\n".join(lines), encoding="utf-8")
    return offset, mapped_words


def burn_subtitles(base: Path, ass: Path, out: Path) -> None:
    ass_escaped = str(ass.resolve()).replace(":", r"\:").replace("'", r"\'")
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-nostats",
        "-i",
        str(base),
        "-vf",
        f"subtitles='{ass_escaped}'",
        "-af",
        "loudnorm=I=-14:TP=-1:LRA=11",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        str(out),
    ]
    run(cmd)


def render_clip(spec: dict[str, Any], clip: dict[str, Any]) -> dict[str, Any]:
    source = Path(spec["source"]).resolve()
    transcript = json.loads(Path(spec["transcript"]).read_text(encoding="utf-8"))
    words = transcript.get("words", [])
    out_path = Path(clip["output"]).resolve()
    work_dir = out_path.parent / "clip_work" / out_path.stem
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    segments = speech_segments(words, float(clip["start"]), float(clip["end"]))
    if not segments:
        raise RuntimeError(f"no transcript words in clip window: {clip['id']}")

    segment_paths = extract_segments(source, work_dir / "segments", segments)
    base = work_dir / "base.mp4"
    concat_segments(segment_paths, base)
    ass = work_dir / f"{out_path.stem}.ass"
    duration, mapped_words = build_ass(ass, clip["first_frame_text"], segments)
    burn_subtitles(base, ass, out_path)
    return {
        "id": clip["id"],
        "output": str(out_path),
        "segments": [{"start": s["start"], "end": s["end"]} for s in segments],
        "duration": duration,
        "word_count": len(mapped_words),
        "ass": str(ass),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Render vertical podcast clips from a JSON spec.")
    parser.add_argument("spec", type=Path)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    results = []
    for clip in spec["clips"]:
        print(f"rendering {clip['id']} -> {clip['output']}")
        results.append(render_clip(spec, clip))
    report_path = Path(spec.get("report", "render_report.json")).resolve()
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(f"command failed: {exc}")
