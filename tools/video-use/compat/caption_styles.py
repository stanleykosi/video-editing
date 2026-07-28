"""ASS caption style builder for existing-footage renders.

The style values live in root `knowledge/presets/captions/ass_caption_styles.json` so
caption taste can evolve with the knowledge base. This module turns those style
roles into concrete ASS subtitles using the fonts installed on this machine.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STYLE_CONFIG = (
    REPO_ROOT / "knowledge" / "presets" / "captions" / "ass_caption_styles.json"
)

SOFT_ENDERS = {
    "a",
    "an",
    "the",
    "to",
    "for",
    "of",
    "with",
    "beside",
    "through",
    "around",
    "into",
    "your",
    "my",
    "our",
    "their",
    "his",
    "her",
    "is",
    "are",
    "was",
    "were",
    "not",
    "so",
    "and",
    "or",
    "but",
}

FILLER_WORDS = {"uh", "um", "umm", "hmm", "mhmm"}
PUNCT_BREAK = set(".,!?;:")


def load_style_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_STYLE_CONFIG
    if not config_path.exists():
        raise FileNotFoundError(f"caption style config not found: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def normalize_family(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def installed_font_families() -> dict[str, str]:
    """Return normalized family name -> display family name from fontconfig."""
    families: dict[str, str] = {}
    try:
        proc = subprocess.run(
            ["fc-list", ":", "family"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return families

    for raw_line in proc.stdout.splitlines():
        for raw_family in raw_line.split(","):
            family = raw_family.strip()
            if not family:
                continue
            # Some fontconfig outputs include aliases after a colon.
            family = family.split(":", 1)[0].strip()
            key = normalize_family(family)
            families.setdefault(key, family)
    return families


def resolve_font_family(
    config: dict[str, Any],
    style: dict[str, Any],
    overrides: dict[str, Any] | None = None,
) -> str:
    overrides = overrides or {}
    requested = str(overrides.get("font_family") or style.get("font_family") or "").strip()
    if requested:
        return requested

    installed = installed_font_families()
    role = str(overrides.get("font_role") or style.get("font_role") or "clean_sans")
    role_config = (config.get("font_roles") or {}).get(role, {})
    candidates = list(role_config.get("preferred_families") or [])
    candidates.extend(config.get("fallback_families") or [])

    for candidate in candidates:
        exact = installed.get(normalize_family(str(candidate)))
        if exact:
            return exact

    return "Sans"


def available_caption_styles(config_path: Path | None = None) -> dict[str, Any]:
    config = load_style_config(config_path)
    styles = {}
    for style_id, style in (config.get("styles") or {}).items():
        styles[style_id] = {
            "label": style.get("label", style_id),
            "description": style.get("description", ""),
            "font_role": style.get("font_role", ""),
            "resolved_font": resolve_font_family(config, style),
            "chunk_words": style.get("chunk_words"),
            "case": style.get("case"),
        }
    return {
        "default_style": config.get("default_style"),
        "source_guidance": config.get("source_guidance", []),
        "styles": styles,
    }


def selected_style_id(edl: dict[str, Any], explicit: str | None = None) -> str | None:
    captions = edl.get("captions") if isinstance(edl.get("captions"), dict) else {}
    return (
        explicit
        or edl.get("caption_style")
        or edl.get("subtitle_style")
        or captions.get("style")
        or captions.get("style_id")
    )


def caption_overrides(edl: dict[str, Any]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for key in ("caption_options", "subtitle_options"):
        value = edl.get(key)
        if isinstance(value, dict):
            overrides.update(value)
    captions = edl.get("captions")
    if isinstance(captions, dict):
        options = captions.get("options")
        if isinstance(options, dict):
            overrides.update(options)
    return overrides


def resolve_style(
    edl: dict[str, Any],
    explicit_style_id: str | None = None,
    config_path: Path | None = None,
) -> tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = load_style_config(config_path)
    style_id = selected_style_id(edl, explicit_style_id) or config.get("default_style")
    styles = config.get("styles") or {}
    if style_id not in styles:
        valid = ", ".join(sorted(styles))
        raise KeyError(f"unknown caption style '{style_id}'. Valid styles: {valid}")
    overrides = caption_overrides(edl)
    style = dict(styles[style_id])
    style.update({k: v for k, v in overrides.items() if k in style or k.startswith("font_")})
    return str(style_id), style, config, overrides


def probe_video_dimensions(video_path: Path) -> tuple[int, int]:
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        width, height = proc.stdout.strip().split(",", 1)
        return int(width), int(height)
    except Exception:
        return 1080, 1920


def ass_time(seconds: float) -> str:
    cs = round(max(0.0, seconds) * 100)
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{c:02d}"


def ass_color(hex_rgb: str, alpha: str = "00") -> str:
    value = str(hex_rgb).strip().lstrip("#")
    if len(value) != 6:
        value = "FFFFFF"
    rr, gg, bb = value[0:2], value[2:4], value[4:6]
    return f"&H{alpha}{bb}{gg}{rr}"


def ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def clean_token(text: str) -> str:
    return re.sub(r"[^a-z0-9']+", "", text.lower())


def source_transcript_path(edit_dir: Path, sources: dict[str, str], source_id: str) -> Path:
    transcripts_dir = edit_dir / "transcripts"
    direct = transcripts_dir / f"{source_id}.json"
    if direct.exists():
        return direct
    source_path = Path(sources[source_id])
    by_stem = transcripts_dir / f"{source_path.stem}.json"
    return by_stem


def words_in_range(transcript: dict[str, Any], start: float, end: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for word in transcript.get("words", []):
        if word.get("type") != "word":
            continue
        ws = word.get("start")
        we = word.get("end")
        if ws is None or we is None:
            continue
        if float(we) <= start or float(ws) >= end:
            continue
        out.append(word)
    return out


def display_word(word: dict[str, Any]) -> str:
    return re.sub(r"\s+", " ", str(word.get("text") or "")).strip()


def output_words_for_edl(edl: dict[str, Any], edit_dir: Path) -> list[dict[str, Any]]:
    sources = edl["sources"]
    out_words: list[dict[str, Any]] = []
    offset = 0.0
    for segment in edl["ranges"]:
        source_id = segment["source"]
        start = float(segment["start"])
        end = float(segment["end"])
        duration = end - start
        transcript_path = source_transcript_path(edit_dir, sources, source_id)
        if not transcript_path.exists():
            print(f"  no transcript for {source_id}, skipping captions for this segment")
            offset += duration
            continue
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        for word in words_in_range(transcript, start, end):
            ws = float(word["start"])
            we = float(word["end"])
            mapped = dict(word)
            mapped["out_start"] = max(0.0, ws - start) + offset
            mapped["out_end"] = max(0.0, we - start) + offset
            out_words.append(mapped)
        offset += duration
    return out_words


def should_drop_word(word: dict[str, Any], style: dict[str, Any]) -> bool:
    token = clean_token(display_word(word))
    return bool(style.get("drop_fillers", True)) and token in FILLER_WORDS


def chunk_words(words: list[dict[str, Any]], style: dict[str, Any]) -> list[list[dict[str, Any]]]:
    target = max(1, int(style.get("chunk_words", 2)))
    max_words = max(target, int(style.get("max_words", target + 1)))
    max_chars = int(style.get("max_chars", 24))
    max_duration = float(style.get("max_duration_seconds", 1.5))
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    filtered: list[dict[str, Any]] = []
    previous_token = ""
    for word in words:
        token = clean_token(display_word(word))
        if not token or should_drop_word(word, style):
            continue
        if style.get("drop_repeated_words", True) and token == previous_token:
            previous_token = token
            continue
        filtered.append(word)
        previous_token = token
    for word in filtered:
        current.append(word)
        raw = display_word(word)
        token = clean_token(raw)
        phrase = " ".join(display_word(w) for w in current)
        compact_chars = len(re.sub(r"[^A-Za-z0-9]", "", phrase))
        duration = float(current[-1]["out_end"]) - float(current[0]["out_start"])
        sentence_end = raw.endswith((".", "?", "!"))
        should_close = len(current) >= target and token not in SOFT_ENDERS
        must_close = (
            len(current) >= max_words
            or compact_chars >= max_chars
            or duration >= max_duration
            or sentence_end
        )
        if should_close or must_close:
            chunks.append(current)
            current = []

    if current:
        chunks.append(current)

    balanced: list[list[dict[str, Any]]] = []
    for chunk in chunks:
        if balanced and len(chunk) == 1:
            prev_last_raw = display_word(balanced[-1][-1])
            prev_last = clean_token(prev_last_raw)
            combined_phrase = " ".join(display_word(w) for w in [*balanced[-1], *chunk])
            combined_chars = len(re.sub(r"[^A-Za-z0-9]", "", combined_phrase))
            prev_ended_sentence = prev_last_raw.rstrip().endswith((".", "?", "!"))
            can_merge = (
                not prev_ended_sentence
                and combined_chars <= max_chars
                and (prev_last in SOFT_ENDERS or len(balanced[-1]) < max_words)
            )
            if can_merge:
                balanced[-1].extend(chunk)
                continue
        balanced.append(chunk)
    return balanced


def apply_case(text: str, mode: str) -> str:
    if mode == "upper":
        return text.upper()
    if mode == "title":
        return text.title()
    return text


def collect_impact_words(
    edl: dict[str, Any], config: dict[str, Any], style: dict[str, Any]
) -> set[str]:
    words: set[str] = set()
    if style.get("highlight_keywords", False):
        words.update(clean_token(word) for word in config.get("impact_keywords", []))
    for value in (edl.get("caption_impact_words"), edl.get("impact_words")):
        if isinstance(value, str):
            words.update(clean_token(part) for part in re.split(r"[,|\n]", value))
        elif isinstance(value, list):
            words.update(clean_token(str(part)) for part in value)
    for segment in edl.get("ranges", []):
        value = segment.get("impact_words")
        if isinstance(value, str):
            words.update(clean_token(part) for part in re.split(r"[,|\n]", value))
        elif isinstance(value, list):
            words.update(clean_token(str(part)) for part in value)
    return {word for word in words if word}


def caption_word_replacements(edl: dict[str, Any]) -> dict[str, str]:
    value = edl.get("caption_word_replacements") or edl.get("caption_token_replacements")
    replacements: dict[str, str] = {}
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = []
        for item in value:
            if (
                isinstance(item, dict)
                and item.get("from") is not None
                and item.get("to") is not None
            ):
                items.append((item["from"], item["to"]))
    else:
        items = []
    for raw_from, raw_to in items:
        key = clean_token(str(raw_from))
        if key:
            replacements[key] = str(raw_to).strip()
    return replacements


def caption_text_replacements(edl: dict[str, Any]) -> list[tuple[str, str]]:
    value = edl.get("caption_text_replacements") or []
    replacements: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for raw_from, raw_to in value.items():
            replacements.append((str(raw_from), str(raw_to)))
    elif isinstance(value, list):
        for item in value:
            if (
                isinstance(item, dict)
                and item.get("from") is not None
                and item.get("to") is not None
            ):
                replacements.append((str(item["from"]), str(item["to"])))
    return replacements


def break_caption_lines(words: list[str], style: dict[str, Any]) -> list[list[str]]:
    if not style.get("allow_two_lines", True):
        return [words]
    threshold = max(2, int(style.get("line_break_after_words", 4)))
    if len(words) <= threshold:
        return [words]
    split_at = min(len(words) - 1, max(1, (len(words) + 1) // 2))
    while split_at < len(words) - 1 and clean_token(words[split_at - 1]) in SOFT_ENDERS:
        split_at += 1
    return [words[:split_at], words[split_at:]]


def format_chunk_text(
    chunk: list[dict[str, Any]],
    style: dict[str, Any],
    config: dict[str, Any],
    impact_words: set[str],
    word_replacements: dict[str, str],
    text_replacements: list[tuple[str, str]],
) -> str:
    case_mode = str(style.get("case", "natural"))
    primary = ass_color(str(style.get("primary_color", "#FFFFFF")))
    accent = ass_color(str(style.get("accent_color", "#F4C95D")))
    secondary = ass_color(
        str(style.get("secondary_accent_color", style.get("accent_color", "#F4C95D")))
    )
    rendered: list[str] = []
    for word in chunk:
        raw = display_word(word).strip()
        if not raw:
            continue
        stripped = raw.rstrip(",;:")
        token = clean_token(stripped)
        if token in word_replacements:
            stripped = word_replacements[token]
            token = clean_token(stripped)
        text = ass_escape(apply_case(stripped, case_mode))
        highlight = token in impact_words
        if style.get("highlight_numbers", False) and re.search(r"\d", stripped):
            highlight = True
        if highlight:
            color = secondary if re.search(r"\d", stripped) else accent
            text = rf"{{\c{color}\b1}}{text}{{\c{primary}\b1}}"
        rendered.append(text)

    if not rendered:
        return ""
    lines = break_caption_lines(rendered, style)
    text = r"\N".join(" ".join(line) for line in lines)
    for old, new in text_replacements:
        text = text.replace(old, new)
    return text


def orientation_value(
    style: dict[str, Any], base_key: str, portrait: bool, default: float
) -> float:
    suffix = "portrait" if portrait else "landscape"
    key = f"{base_key}_{suffix}"
    if key in style:
        return float(style[key])
    return float(style.get(base_key, default))


def ass_style_line(
    style: dict[str, Any],
    font_family: str,
    width: int,
    height: int,
) -> str:
    portrait = height >= width
    font_size = max(
        16, round(height * orientation_value(style, "font_size_ratio", portrait, 0.044))
    )
    outline = max(1, round(height * float(style.get("outline_ratio", 0.0032))))
    shadow = max(0, round(height * float(style.get("shadow_ratio", 0.0))))
    margin_v = max(0, round(height * orientation_value(style, "margin_v_ratio", portrait, 0.12)))
    margin_x = max(0, round(width * float(style.get("margin_x_ratio", 0.07))))
    bold = -1 if bool(style.get("bold", True)) else 0
    italic = -1 if bool(style.get("italic", False)) else 0
    spacing = float(style.get("tracking", 0))
    scale_x = float(style.get("scale_x", 100))
    scale_y = float(style.get("scale_y", 100))
    border_style = int(style.get("border_style", 1))
    primary = ass_color(str(style.get("primary_color", "#FFFFFF")))
    outline_color = ass_color(str(style.get("outline_color", "#000000")))
    back = ass_color(str(style.get("back_color", "#000000")), str(style.get("back_alpha", "90")))
    return (
        "Style: Caption,"
        f"{font_family},{font_size},{primary},&H00000000,{outline_color},{back},"
        f"{bold},{italic},0,0,{scale_x:g},{scale_y:g},{spacing:g},0,{border_style},{outline},{shadow},"
        f"2,{margin_x},{margin_x},{margin_v},1"
    )


def event_tags(style: dict[str, Any]) -> str:
    tags = [rf"\fad({int(style.get('fade_in_ms', 60))},{int(style.get('fade_out_ms', 80))})"]
    blur = float(style.get("blur", 0))
    if blur > 0:
        tags.append(rf"\blur{blur:g}")
    if style.get("scale_pop", False):
        pop_ms = int(style.get("pop_ms", 90))
        pop_x = int(style.get("pop_scale_x", 106))
        pop_y = int(style.get("pop_scale_y", 106))
        settle_ms = int(style.get("pop_settle_ms", 0))
        settle_x = int(style.get("scale_x", 100))
        settle_y = int(style.get("scale_y", 100))
        if settle_ms > 0:
            tags.append(
                rf"\fscx{settle_x}\fscy{settle_y}"
                rf"\t(0,{pop_ms},\fscx{pop_x}\fscy{pop_y})"
                rf"\t({pop_ms},{pop_ms + settle_ms},\fscx{settle_x}\fscy{settle_y})"
            )
        else:
            tags.append(rf"\t(0,{pop_ms},\fscx{pop_x}\fscy{pop_y})")
    return "{" + "".join(tags) + "}"


def caption_suppression_ranges(edl: dict[str, Any]) -> list[tuple[float, float]]:
    """Return output-timeline windows where normal captions should not render."""
    ranges: list[tuple[float, float]] = []

    for key in ("caption_suppressions", "suppress_caption_ranges"):
        value = edl.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            if not isinstance(item, dict):
                continue
            start = item.get("start_in_output", item.get("start"))
            end = item.get("end_in_output", item.get("end"))
            if end is None and item.get("duration") is not None and start is not None:
                end = float(start) + float(item["duration"])
            if start is None or end is None:
                continue
            start_f = max(0.0, float(start))
            end_f = max(start_f, float(end))
            if end_f > start_f:
                ranges.append((start_f, end_f))

    for overlay in edl.get("overlays", []):
        if not isinstance(overlay, dict) or not overlay.get("suppress_captions", False):
            continue
        start = float(overlay.get("start_in_output", overlay.get("start", 0.0)))
        duration = overlay.get("duration")
        end = overlay.get("end_in_output", overlay.get("end"))
        if end is None and duration is not None:
            end = start + float(duration)
        if end is None:
            continue
        end_f = max(start, float(end))
        if end_f > start:
            ranges.append((max(0.0, start), end_f))

    return sorted(ranges)


def cue_is_suppressed(start: float, end: float, suppressions: list[tuple[float, float]]) -> bool:
    return any(start < stop and end > begin for begin, stop in suppressions)


def build_master_ass(
    edl: dict[str, Any],
    edit_dir: Path,
    out_path: Path,
    base_video: Path,
    explicit_style_id: str | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    style_id, style, config, overrides = resolve_style(edl, explicit_style_id, config_path)
    width, height = probe_video_dimensions(base_video)
    font_family = resolve_font_family(config, style, overrides)
    impact_words = collect_impact_words(edl, config, style)
    word_replacements = caption_word_replacements(edl)
    text_replacements = caption_text_replacements(edl)
    words = output_words_for_edl(edl, edit_dir)
    chunks = chunk_words(words, style)
    min_duration = float(style.get("min_duration_seconds", 0.36))
    max_duration = float(style.get("max_duration_seconds", 1.6))
    suppressions = caption_suppression_ranges(edl)

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        ass_style_line(style, font_family, width, height),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    raw_cues: list[tuple[float, float, str]] = []
    tags = event_tags(style)
    for chunk in chunks:
        start = float(chunk[0]["out_start"])
        end = max(float(chunk[-1]["out_end"]), start + min_duration)
        end = min(end, start + max_duration)
        text = format_chunk_text(
            chunk, style, config, impact_words, word_replacements, text_replacements
        )
        if not text:
            continue
        if cue_is_suppressed(start, end, suppressions):
            continue
        raw_cues.append((start, end, text))

    cue_count = 0
    for idx, (start, end, text) in enumerate(raw_cues):
        if idx + 1 < len(raw_cues):
            next_start = raw_cues[idx + 1][0]
            if end >= next_start:
                end = max(start + 0.06, next_start - 0.02)
        if end <= start:
            continue
        lines.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{tags}{text}")
        cue_count += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "path": str(out_path),
        "style_id": style_id,
        "label": style.get("label", style_id),
        "font_family": font_family,
        "font_role": style.get("font_role", ""),
        "cues": cue_count,
        "source_guidance": config.get("source_guidance", []),
    }


def srt_force_style(
    edl: dict[str, Any],
    base_video: Path,
    explicit_style_id: str | None = None,
    config_path: Path | None = None,
) -> str:
    """Dynamic force_style fallback for user-supplied SRT/VTT files."""
    _style_id, style, config, overrides = resolve_style(edl, explicit_style_id, config_path)
    width, height = probe_video_dimensions(base_video)
    portrait = height >= width
    font_family = resolve_font_family(config, style, overrides)
    font_size = max(
        16, round(height * orientation_value(style, "font_size_ratio", portrait, 0.044))
    )
    outline = max(1, round(height * float(style.get("outline_ratio", 0.0032))))
    shadow = max(0, round(height * float(style.get("shadow_ratio", 0.0))))
    margin_v = max(0, round(height * orientation_value(style, "margin_v_ratio", portrait, 0.12)))
    primary = ass_color(str(style.get("primary_color", "#FFFFFF")))
    outline_color = ass_color(str(style.get("outline_color", "#000000")))
    back = ass_color(str(style.get("back_color", "#000000")), str(style.get("back_alpha", "90")))
    bold = 1 if bool(style.get("bold", True)) else 0
    italic = 1 if bool(style.get("italic", False)) else 0
    return (
        f"FontName={font_family},FontSize={font_size},Bold={bold},Italic={italic},"
        f"PrimaryColour={primary},OutlineColour={outline_color},BackColour={back},"
        f"BorderStyle={int(style.get('border_style', 1))},Outline={outline},Shadow={shadow},"
        f"Alignment=2,MarginV={margin_v}"
    )
