"""Transcribe videos with Deepgram prerecorded speech-to-text.

Writes two cached artifacts:
- <edit_dir>/transcripts/<video_stem>.deepgram.raw.json
- <edit_dir>/transcripts/<video_stem>.json

The second file is converted into the Scribe-like word list expected by
pack_transcripts.py: root-level `words` entries with word-level timestamps and
speaker_id fields.

Usage:
    python helpers/transcribe_deepgram.py <video_path>
    python helpers/transcribe_deepgram.py <video_path> --edit-dir /custom/edit
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests


DEEPGRAM_LISTEN_URL = "https://api.deepgram.com/v1/listen"


def load_api_key() -> str:
    for candidate in [Path(__file__).resolve().parents[2] / ".env", Path(".env")]:
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() == "DEEPGRAM_API_KEY":
                    return value.strip().strip('"').strip("'")
    value = os.environ.get("DEEPGRAM_API_KEY", "")
    if not value:
        sys.exit("DEEPGRAM_API_KEY not found in .env or environment")
    return value


def extract_audio(video_path: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "64k",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def call_deepgram(audio_path: Path, api_key: str, language: str = "en") -> dict[str, Any]:
    params = {
        "model": "nova-3",
        "language": language,
        "smart_format": "false",
        "punctuate": "true",
        "diarize": "true",
        "utterances": "true",
        "filler_words": "true",
    }
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/mpeg",
    }
    with audio_path.open("rb") as handle:
        response = requests.post(
            DEEPGRAM_LISTEN_URL,
            params=params,
            headers=headers,
            data=handle,
            timeout=3600,
        )
    if response.status_code != 200:
        raise RuntimeError(f"Deepgram returned {response.status_code}: {response.text[:500]}")
    return response.json()


def convert_to_scribe_like(raw: dict[str, Any]) -> dict[str, Any]:
    alternative = (
        raw.get("results", {})
        .get("channels", [{}])[0]
        .get("alternatives", [{}])[0]
    )
    dg_words = alternative.get("words", [])
    words: list[dict[str, Any]] = []
    for item in dg_words:
        start = item.get("start")
        end = item.get("end")
        if start is None or end is None:
            continue
        speaker = item.get("speaker")
        speaker_id = f"speaker_{speaker}" if speaker is not None else None
        text = item.get("punctuated_word") or item.get("word") or ""
        words.append(
            {
                "type": "word",
                "text": text,
                "start": float(start),
                "end": float(end),
                "speaker_id": speaker_id,
                "confidence": item.get("confidence"),
            }
        )
    return {
        "text": alternative.get("transcript", ""),
        "words": words,
        "metadata": {
            "provider": "deepgram",
            "model": raw.get("metadata", {}).get("model_info", {}),
            "request_id": raw.get("metadata", {}).get("request_id"),
            "duration": raw.get("metadata", {}).get("duration"),
        },
    }


def transcribe_one(video: Path, edit_dir: Path, api_key: str, language: str = "en") -> Path:
    transcripts_dir = edit_dir / "transcripts"
    raw_dir = edit_dir / "transcripts_raw"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    converted_path = transcripts_dir / f"{video.stem}.json"
    raw_path = raw_dir / f"{video.stem}.deepgram.raw.json"

    if converted_path.exists() and raw_path.exists():
        print(f"cached: {converted_path}")
        return converted_path

    started = time.time()
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / f"{video.stem}.mp3"
        print(f"extracting 16 kHz mono MP3 from {video.name}", flush=True)
        extract_audio(video, audio_path)
        print(f"uploading {audio_path.stat().st_size / (1024 * 1024):.1f} MB to Deepgram", flush=True)
        raw = call_deepgram(audio_path, api_key, language=language)

    raw_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    converted = convert_to_scribe_like(raw)
    converted_path.write_text(json.dumps(converted, indent=2), encoding="utf-8")
    print(
        f"saved {converted_path} with {len(converted['words'])} words in {time.time() - started:.1f}s",
        flush=True,
    )
    return converted_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe a video with Deepgram.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--edit-dir", type=Path, default=None)
    parser.add_argument("--language", default="en")
    args = parser.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")
    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()
    transcribe_one(video, edit_dir, load_api_key(), language=args.language)


if __name__ == "__main__":
    main()
