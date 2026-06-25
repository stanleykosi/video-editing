"""Generate from-scratch narration with Deepgram Aura TTS.

Reads a script or text file, chunks it under Deepgram's REST input limit, calls
`POST https://api.deepgram.com/v1/speak`, and writes a single voiceover file.

Examples:
    python tools/video-use/helpers/voiceover_generator.py --project-dir edit/demo --script script.md
    python tools/video-use/helpers/voiceover_generator.py --text "Hello world" --output voiceover.mp3
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import requests

from asset_manifest import add_asset_entry, load_env, utc_now


DEEPGRAM_SPEAK_URL = "https://api.deepgram.com/v1/speak"
MAX_DEEPGRAM_CHARS = 2000
SAFE_CHUNK_CHARS = 1800


def clean_script_markdown(text: str) -> str:
    """Extract likely voiceover text from markdown without copying table chrome."""
    lines: list[str] = []
    in_table = False
    headers: list[str] = []
    voice_col: int | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if not in_table:
                lines.append("")
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= {"-", ":", " "} for c in cells):
                continue
            if not in_table:
                headers = [c.lower() for c in cells]
                voice_col = next(
                    (idx for idx, c in enumerate(headers) if c in {"voiceover", "line", "script", "text"}),
                    None,
                )
                in_table = True
                continue
            if voice_col is not None and voice_col < len(cells):
                value = cells[voice_col].strip()
                if value and not value.startswith("<"):
                    lines.append(value)
            continue
        in_table = False
        if line.startswith("#") or line.startswith("- ") or line.startswith(">"):
            continue
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def split_text(text: str, limit: int = SAFE_CHUNK_CHARS) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) <= limit:
        return [text] if text else []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > MAX_DEEPGRAM_CHARS:
            words = sentence.split()
            for word in words:
                candidate = f"{current} {word}".strip()
                if len(candidate) > limit and current:
                    chunks.append(current)
                    current = word
                else:
                    current = candidate
            continue
        candidate = f"{current} {sentence}".strip()
        if len(candidate) > limit and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def deepgram_params(args: argparse.Namespace) -> dict[str, Any]:
    params: dict[str, Any] = {"model": args.model}
    if args.speed:
        params["speed"] = args.speed
    if args.container:
        params["container"] = args.container
    if args.encoding:
        params["encoding"] = args.encoding
    if args.sample_rate:
        params["sample_rate"] = args.sample_rate
    if args.bit_rate:
        params["bit_rate"] = args.bit_rate
    if args.mip_opt_out:
        params["mip_opt_out"] = "true"
    if args.tag:
        params["tag"] = args.tag
    return params


def synthesize_chunk(text: str, output: Path, api_key: str, params: dict[str, Any], timeout: int) -> dict[str, str]:
    response = requests.post(
        DEEPGRAM_SPEAK_URL,
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        },
        params=params,
        json={"text": text},
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Deepgram TTS failed ({response.status_code}): {response.text[:500]}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)
    return {
        "dg_request_id": response.headers.get("dg-request-id", ""),
        "dg_model_name": response.headers.get("dg-model-name", ""),
        "dg_char_count": response.headers.get("dg-char-count", ""),
        "content_type": response.headers.get("content-type", ""),
    }


def concat_audio(parts: list[Path], output: Path) -> None:
    if len(parts) == 1:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(parts[0].read_bytes())
        return
    with tempfile.TemporaryDirectory() as tmp:
        concat_file = Path(tmp) / "concat.txt"
        concat_file.write_text(
            "".join(f"file '{part.resolve()}'\n" for part in parts),
            encoding="utf-8",
        )
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-nostats", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output)],
            check=True,
        )


def write_voiceover_plan(project_dir: Path, text: str, output: Path, chunks: list[str], params: dict[str, Any]) -> Path:
    words = len(re.findall(r"\b\w+\b", text))
    plan_path = project_dir / "voiceover_plan.md"
    plan_path.write_text(
        "\n".join(
            [
                "# Voiceover Plan",
                "",
                f"- Generated at: {utc_now()}",
                f"- Output: `{output}`",
                f"- Model: `{params.get('model', '')}`",
                f"- Container: `{params.get('container', 'default')}`",
                f"- Estimated words: {words}",
                f"- Chunks: {len(chunks)}",
                "",
                "## Timing Notes",
                "",
                "- Review generated pacing against `visual_plan.md` before final render.",
                "- If the voiceover feels rushed, revise the script before stretching audio.",
                "- Use this file as the source of truth for VO asset location and model choice.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return plan_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate voiceover audio with Deepgram Aura TTS.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--script", type=Path, help="Markdown script file. Defaults to <project-dir>/script.md.")
    parser.add_argument("--text", help="Inline text to synthesize.")
    parser.add_argument("--output", type=Path, help="Output audio path. Defaults under <project-dir>/assets/audio.")
    parser.add_argument("--model")
    parser.add_argument("--speed", help="Deepgram Aura-2 speaking-rate multiplier, e.g. 1.15.")
    parser.add_argument("--container")
    parser.add_argument("--encoding")
    parser.add_argument("--sample-rate")
    parser.add_argument("--bit-rate")
    parser.add_argument("--mip-opt-out", action="store_true")
    parser.add_argument("--tag", default="video-editing-agent")
    parser.add_argument("--chunk-chars", type=int, default=SAFE_CHUNK_CHARS)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true", help="Write plan/metadata without calling Deepgram.")
    args = parser.parse_args()

    load_env()
    args.model = args.model or os.environ.get("DEEPGRAM_TTS_MODEL", "aura-2-thalia-en")
    args.speed = args.speed or os.environ.get("DEEPGRAM_TTS_SPEED", "")
    args.container = args.container or os.environ.get("DEEPGRAM_TTS_CONTAINER", "")
    args.encoding = args.encoding or os.environ.get("DEEPGRAM_TTS_ENCODING", "mp3")
    args.sample_rate = args.sample_rate or os.environ.get("DEEPGRAM_TTS_SAMPLE_RATE", "")
    args.bit_rate = args.bit_rate or os.environ.get("DEEPGRAM_TTS_BIT_RATE", "")
    args.mip_opt_out = args.mip_opt_out or os.environ.get("DEEPGRAM_TTS_MIP_OPT_OUT", "").lower() == "true"

    project_dir = args.project_dir.resolve()
    script_path = args.script or (project_dir / "script.md")
    if args.text:
        text = args.text.strip()
    else:
        if not script_path.exists():
            raise SystemExit(f"script not found: {script_path}")
        text = clean_script_markdown(script_path.read_text(encoding="utf-8"))
    if not text:
        raise SystemExit("no voiceover text found")

    chunks = split_text(text, min(args.chunk_chars, SAFE_CHUNK_CHARS))
    suffix = ".wav" if args.container == "wav" else ".mp3"
    output = (args.output or (project_dir / "assets" / "audio" / f"voiceover{suffix}")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    params = deepgram_params(args)

    headers: list[dict[str, str]] = []
    if not args.dry_run:
        api_key = os.environ.get("DEEPGRAM_API_KEY", "")
        if not api_key:
            raise SystemExit("DEEPGRAM_API_KEY is missing in .env or environment")
        with tempfile.TemporaryDirectory() as tmp:
            parts: list[Path] = []
            for idx, chunk in enumerate(chunks, start=1):
                part = Path(tmp) / f"voiceover_part_{idx:03d}{suffix}"
                headers.append(synthesize_chunk(chunk, part, api_key, params, args.timeout))
                parts.append(part)
            concat_audio(parts, output)

    plan_path = write_voiceover_plan(project_dir, text, output, chunks, params)
    metadata = {
        "source_platform": "deepgram",
        "asset_type": "voiceover",
        "asset_id": output.stem,
        "asset_title": "Generated voiceover",
        "creator": "Deepgram Aura TTS",
        "local_path": str(output),
        "downloaded_at": utc_now(),
        "generation_provider": "deepgram",
        "model": args.model,
        "prompt": text[:500],
        "generation_date": utc_now(),
        "policy_or_license_notes": "Synthetic voiceover generated for this project; verify Deepgram account terms before publishing.",
        "metadata": {
            "chunks": len(chunks),
                "headers": headers,
                "dry_run": args.dry_run,
                "voiceover_plan": str(plan_path),
                "speed": args.speed,
            },
        "used_in_timeline": True,
    }
    manifest_path, asset = add_asset_entry(project_dir, metadata)
    print(json.dumps({"output": str(output), "plan": str(plan_path), "manifest": str(manifest_path), "asset": asset}, indent=2))


if __name__ == "__main__":
    main()
