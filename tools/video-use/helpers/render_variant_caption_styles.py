"""Render styled caption/title variants from existing vertical podcast clip bases.

Input is a JSON spec pointing at the original word transcript, the top clip render
report, and a list of variants. The helper reuses each clip_work/<id>/base.mp4 so
cut timing and meaning stay intact while title/caption typography can be tested.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


OUT_W = 1080
OUT_H = 1920

KEYWORDS = {
    "ai",
    "agi",
    "jobs",
    "job",
    "entry",
    "level",
    "openai",
    "anthropic",
    "oligarchs",
    "oligarch",
    "government",
    "governments",
    "future",
    "children",
    "brain",
    "claude",
    "model",
    "target",
    "spy",
    "ethical",
    "server",
    "decision",
    "decisions",
    "paralegal",
    "ceo",
    "2027",
    "twenty",
    "seven",
}

FILLER = {"uh", "um", "mhmm", "hmm"}

STYLE_META = {
    "clean_podcast": {
        "label": "Clean podcast style",
        "caption_mode": "phrase",
        "font": "Liberation Sans",
        "subtitle_font": "Liberation Sans",
        "accent": "F4C95D",
        "filter": "eq=contrast=1.015:saturation=1.0",
        "notes": "Restrained editorial header, readable phrase captions, soft gold emphasis.",
    },
    "aggressive_tiktok": {
        "label": "Aggressive TikTok hook style",
        "caption_mode": "punch",
        "font": "Liberation Sans",
        "subtitle_font": "Liberation Sans",
        "accent": "FF2D55",
        "filter": (
            "eq=contrast=1.075:saturation=1.08,"
            "unsharp=5:5:0.55:3:3:0.20,"
            "drawbox=x=0:y=0:w=iw:h=14:color=0xFF2D55@0.92:t=fill,"
            "drawbox=x=0:y=14:w=iw:h=5:color=0xFFF200@0.82:t=fill"
        ),
        "notes": "Large urgency hook, high-contrast social captions, red/yellow accent system.",
    },
    "caption_first_curiosity": {
        "label": "Caption-first curiosity style",
        "caption_mode": "curiosity",
        "font": "Liberation Serif",
        "subtitle_font": "Liberation Sans",
        "accent": "55E6FF",
        "filter": (
            "eq=contrast=1.035:saturation=0.97,"
            "drawbox=x=0:y=0:w=iw:h=360:color=black@0.20:t=fill"
        ),
        "notes": "Question-led first frame, editorial serif title, body captions treated as the main visual path.",
    },
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


def ass_color(rgb: str, alpha: str = "00") -> str:
    rgb = rgb.strip().lstrip("#")
    rr, gg, bb = rgb[0:2], rgb[2:4], rgb[4:6]
    return f"&H{alpha}{bb}{gg}{rr}"


def words_in_segment(words: list[dict[str, Any]], start: float, end: float) -> list[dict[str, Any]]:
    return [
        w
        for w in words
        if w.get("type") == "word"
        and w.get("start") is not None
        and w.get("end") is not None
        and float(w["end"]) > start
        and float(w["start"]) < end
    ]


def mapped_words(transcript_words: list[dict[str, Any]], segments: list[dict[str, float]]) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    offset = 0.0
    for seg in segments:
        seg_start = float(seg["start"])
        seg_end = float(seg["end"])
        for word in words_in_segment(transcript_words, seg_start, seg_end):
            ws = float(word["start"])
            we = float(word["end"])
            if we <= seg_start or ws >= seg_end:
                continue
            item = dict(word)
            item["out_start"] = max(0.0, ws - seg_start) + offset
            item["out_end"] = max(0.0, we - seg_start) + offset
            mapped.append(item)
        offset += seg_end - seg_start
    return cleanup_caption_words(mapped)


def cleanup_caption_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    i = 0
    while i < len(words):
        raw = str(words[i].get("text", "")).strip()
        token = clean_token(raw)
        next_token = clean_token(str(words[i + 1].get("text", ""))) if i + 1 < len(words) else ""
        if not token or token in FILLER:
            i += 1
            continue
        if token == "you" and next_token == "know":
            i += 2
            continue
        if cleaned and clean_token(str(cleaned[-1].get("text", ""))) == token:
            i += 1
            continue
        cleaned.append(words[i])
        i += 1
    return cleaned


def event_words(words: list[dict[str, Any]], mode: str) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    if mode == "punch":
        max_words, max_chars, max_dur = 2, 13, 0.90
    elif mode == "curiosity":
        max_words, max_chars, max_dur = 3, 18, 1.25
    else:
        max_words, max_chars, max_dur = 5, 28, 1.75

    for word in words:
        token = str(word.get("text", "")).strip()
        if not token:
            continue
        cur.append(word)
        text = " ".join(str(w["text"]) for w in cur)
        dur = float(cur[-1]["out_end"]) - float(cur[0]["out_start"])
        punct = token.endswith((".", "?", "!"))
        too_long = len(re.sub(r"[^A-Za-z0-9]", "", text)) >= max_chars
        impact = mode == "punch" and clean_token(token) in KEYWORDS
        if len(cur) >= max_words or too_long or punct or dur >= max_dur or impact:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def format_caption_text(words: list[dict[str, Any]], style_id: str) -> str:
    accent_rgb = STYLE_META[style_id]["accent"]
    accent = ass_color(accent_rgb)
    alt = ass_color("FFF200" if style_id == "aggressive_tiktok" else "F4C95D")
    rendered: list[str] = []
    for word in words:
        raw = str(word.get("text", "")).strip().rstrip(",;:")
        if not raw:
            continue
        token = clean_token(raw)
        text = esc_ass(raw.upper().rstrip("."))
        if token in KEYWORDS:
            if style_id == "aggressive_tiktok":
                text = rf"{{\c{alt}\bord7}}{text}{{\c&H00FFFFFF&\bord6}}"
            elif style_id == "caption_first_curiosity":
                text = rf"{{\c{accent}\b1}}{text}{{\c&H00FFFFFF&\b1}}"
            else:
                text = rf"{{\c{ass_color('F4C95D')}}}{text}{{\c&H00FFFFFF&}}"
        rendered.append(text)
    if not rendered:
        return ""
    if style_id == "clean_podcast":
        if len(rendered) > 3:
            mid = (len(rendered) + 1) // 2
            return " ".join(rendered[:mid]) + r"\N" + " ".join(rendered[mid:])
        return " ".join(rendered)
    if style_id == "caption_first_curiosity":
        if len(rendered) > 2:
            return " ".join(rendered[:-1]) + r"\N" + rendered[-1]
        return " ".join(rendered)
    return " ".join(rendered)


def style_lines(style_id: str) -> list[str]:
    clean = style_id == "clean_podcast"
    aggressive = style_id == "aggressive_tiktok"
    curiosity = style_id == "caption_first_curiosity"
    if clean:
        return [
            f"Style: Caption,Liberation Sans,66,&H00FFFFFF,&H00000000,{ass_color('141414')},{ass_color('000000','72')},-1,0,0,0,100,100,0,0,3,12,0,2,88,88,350,1",
            f"Style: Header,Liberation Sans,68,{ass_color('FFFFFF')},&H00000000,{ass_color('050505')},{ass_color('000000','86')},-1,0,0,0,100,100,0,0,3,16,0,8,82,82,116,1",
            f"Style: Kicker,Liberation Sans,36,{ass_color('F4C95D')},&H00000000,{ass_color('050505')},{ass_color('000000','92')},-1,0,0,0,100,100,0,0,3,10,0,8,82,82,76,1",
        ]
    if aggressive:
        return [
            f"Style: Caption,Liberation Sans,90,&H00FFFFFF,&H00000000,{ass_color('000000')},&H99000000,-1,0,0,0,100,100,0,0,1,7,0,2,56,56,332,1",
            f"Style: Header,Liberation Sans,86,{ass_color('FFFFFF')},&H00000000,{ass_color('000000')},{ass_color('FF2D55','10')},-1,0,0,0,104,100,0,0,3,20,0,8,58,58,92,1",
            f"Style: Kicker,Liberation Sans,34,{ass_color('FFF200')},&H00000000,{ass_color('000000')},{ass_color('000000','80')},-1,0,0,0,112,100,0,0,1,4,0,8,58,58,54,1",
        ]
    if curiosity:
        return [
            f"Style: Caption,Liberation Sans,76,&H00FFFFFF,&H00000000,{ass_color('071217')},{ass_color('000000','75')},-1,0,0,0,100,100,0,0,3,12,0,2,74,74,374,1",
            f"Style: Header,Liberation Serif,82,{ass_color('F8F1E7')},&H00000000,{ass_color('061015')},{ass_color('000000','88')},-1,0,0,0,100,100,0,0,1,5,1,8,66,66,98,1",
            f"Style: Kicker,Liberation Sans,36,{ass_color('55E6FF')},&H00000000,{ass_color('061015')},{ass_color('000000','90')},-1,0,0,0,108,100,0,0,1,3,0,8,66,66,62,1",
        ]
    raise ValueError(f"unknown style_id {style_id}")


def add_header_events(lines: list[str], variant: dict[str, Any], style_id: str, duration: float) -> None:
    hook = str(variant["first_frame_text"]).upper()
    kicker = str(variant.get("kicker", "")).upper()
    hook_end = min(float(variant.get("hook_duration", 3.4)), max(1.0, duration))
    if kicker:
        lines.append(f"Dialogue: 3,{ass_time(0)},{ass_time(hook_end)},Kicker,,0,0,0,,{esc_ass(kicker)}")
    if style_id == "aggressive_tiktok":
        text = rf"{{\fad(60,130)\t(0,140,\fscx108\fscy108)}}{esc_ass(hook)}"
    elif style_id == "caption_first_curiosity":
        text = rf"{{\fad(120,180)}}{esc_ass(hook)}"
    else:
        text = rf"{{\fad(120,160)}}{esc_ass(hook)}"
    lines.append(f"Dialogue: 3,{ass_time(0)},{ass_time(hook_end)},Header,,0,0,0,,{text}")


def build_ass(
    ass_path: Path,
    style_id: str,
    variant: dict[str, Any],
    words: list[dict[str, Any]],
    duration: float,
) -> None:
    mode = STYLE_META[style_id]["caption_mode"]
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {OUT_W}",
        f"PlayResY: {OUT_H}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        *style_lines(style_id),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    add_header_events(lines, variant, style_id, duration)
    suppress_until = min(float(variant.get("caption_delay", 0.0)), duration)
    for chunk in event_words(words, mode):
        start = max(float(chunk[0]["out_start"]), suppress_until)
        end = max(float(chunk[-1]["out_end"]), start + 0.28)
        if end <= suppress_until + 0.08:
            continue
        text = format_caption_text(chunk, style_id)
        if not text:
            continue
        if style_id == "aggressive_tiktok":
            text = rf"{{\fad(25,45)\t(0,85,\fscx106\fscy106)}}{text}"
        elif style_id == "caption_first_curiosity":
            text = rf"{{\fad(55,70)}}{text}"
        else:
            text = rf"{{\fad(45,60)}}{text}"
        lines.append(f"Dialogue: 2,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{text}")
    ass_path.write_text("\n".join(lines), encoding="utf-8")


def burn_variant(base: Path, ass: Path, out: Path, style_id: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    ass_escaped = str(ass.resolve()).replace(":", r"\:").replace("'", r"\'")
    filters = [STYLE_META[style_id]["filter"], f"subtitles='{ass_escaped}'"]
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-nostats",
        "-i",
        str(base),
        "-vf",
        ",".join(filters),
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Render styled variants for vertical podcast clips.")
    parser.add_argument("spec", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))

    transcript = json.loads(Path(spec["transcript"]).read_text(encoding="utf-8"))
    transcript_words = transcript.get("words", [])
    report_items = {item["id"]: item for item in json.loads(Path(spec["render_report"]).read_text(encoding="utf-8"))}

    results = []
    for variant in spec["variants"]:
        clip_id = variant["clip_id"]
        style_id = variant["style_id"]
        item = report_items[clip_id]
        base = Path(spec["edit_dir"]) / "clip_work" / clip_id / "base.mp4"
        out = Path(variant["output"]).resolve()
        ass = out.with_suffix(".ass")
        words = mapped_words(transcript_words, item["segments"])
        duration = float(item["duration"])
        print(f"rendering {clip_id} {style_id} -> {out}")
        build_ass(ass, style_id, variant, words, duration)
        burn_variant(base, ass, out, style_id)
        results.append(
            {
                "clip_id": clip_id,
                "style_id": style_id,
                "label": STYLE_META[style_id]["label"],
                "output": str(out),
                "ass": str(ass),
                "first_frame_text": variant["first_frame_text"],
                "kicker": variant.get("kicker", ""),
                "style_notes": STYLE_META[style_id]["notes"],
            }
        )

    report_path = Path(spec.get("variant_report", "variant_render_report.json")).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
