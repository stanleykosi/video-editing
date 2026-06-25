"""Transcribe audio or video locally with faster-whisper.

This avoids paid APIs and writes:
  - <source_stem>.txt
  - <source_stem>.segments.txt

Usage:
    python tools/video-use/helpers/transcribe_local.py "audio.mp3"
    python tools/video-use/helpers/transcribe_local.py "audio.mp3" --model turbo
    python tools/video-use/helpers/transcribe_local.py "audio.mp3" --output-dir transcripts
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# Hugging Face's Xet downloader can stall in some WSL/proxy setups. Disable it
# before importing faster-whisper so model downloads use the normal HTTP path.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from faster_whisper import WhisperModel  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]


def fmt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def transcribe(args: argparse.Namespace) -> tuple[Path, Path, int]:
    source = args.source.resolve()
    if not source.exists():
        sys.exit(f"source not found: {source}")

    output_dir = (args.output_dir or source.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    out_txt = output_dir / f"{source.stem}.txt"
    out_segments = output_dir / f"{source.stem}.segments.txt"

    model_dir = args.model_dir.resolve()
    model_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"loading {args.model} on {args.device} "
        f"({args.compute_type}, threads={args.threads})",
        flush=True,
    )
    model = WhisperModel(
        args.model,
        device=args.device,
        compute_type=args.compute_type,
        cpu_threads=args.threads,
        num_workers=1,
        download_root=str(model_dir),
    )

    segments, info = model.transcribe(
        str(source),
        language=args.language,
        task="transcribe",
        beam_size=args.beam_size,
        best_of=args.best_of,
        temperature=args.temperature,
        condition_on_previous_text=args.condition_on_previous_text,
        vad_filter=args.vad_filter,
    )

    duration = getattr(info, "duration", 0.0)
    print(f"audio duration: {duration:.1f}s | language: {info.language}", flush=True)

    count = 0
    with out_txt.open("w", encoding="utf-8") as plain, out_segments.open(
        "w", encoding="utf-8"
    ) as stamped:
        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue

            count += 1
            stamped_line = (
                f"[{fmt_timestamp(segment.start)} --> "
                f"{fmt_timestamp(segment.end)}] {text}"
            )
            print(stamped_line, flush=True)
            plain.write(text + "\n")
            stamped.write(stamped_line + "\n")
            plain.flush()
            stamped.flush()

    return out_txt, out_segments, count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Free local transcription with faster-whisper"
    )
    parser.add_argument("source", type=Path, help="Audio or video file to transcribe")
    parser.add_argument(
        "--model",
        default="base",
        help="Model name: base, small, medium, turbo, large-v3-turbo, etc.",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=REPO_ROOT / ".whisper-models" / "faster",
        help="Where faster-whisper models are cached",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output folder (default: same folder as source)",
    )
    parser.add_argument("--language", default="en", help="Language code, or omit with ''")
    parser.add_argument("--device", default="cpu", help="cpu or cuda")
    parser.add_argument("--compute-type", default="int8", help="int8 is best for CPU")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--beam-size", type=int, default=1)
    parser.add_argument("--best-of", type=int, default=1)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--condition-on-previous-text",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable for more context; disabling reduces repetition on long files",
    )
    parser.add_argument(
        "--vad-filter",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip non-speech sections to reduce hallucinations",
    )
    args = parser.parse_args()

    if args.language == "":
        args.language = None

    out_txt, out_segments, count = transcribe(args)
    print(f"done: wrote {count} segments")
    print(f"text: {out_txt}")
    print(f"segments: {out_segments}")


if __name__ == "__main__":
    main()
