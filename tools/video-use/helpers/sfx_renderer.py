"""Synthesize and mix frame-locked SFX for knowledge-driven timelines."""

from __future__ import annotations

import math
import random
import shlex
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any


SAMPLE_RATE = 48_000


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def run(cmd: list[str]) -> None:
    print(f"  $ {' '.join(shlex.quote(c) for c in cmd[:8])}{' ...' if len(cmd) > 8 else ''}")
    subprocess.run(cmd, check=True)


def timeline_duration(timeline: dict[str, Any]) -> float:
    return max((float(beat.get("end", 0)) for beat in timeline.get("beats", [])), default=0.0)


def normalize_kind(value: str) -> str:
    value = value.lower().strip()
    if "glitch" in value or "font" in value:
        return "glitch"
    if "tick" in value or "marker" in value or "diagram" in value:
        return "tick"
    if "shimmer" in value or "highlight" in value or "wipe" in value:
        return "shimmer"
    if "reverse" in value or "riser" in value:
        return "reverse_hit"
    if "whoosh" in value or "transition" in value:
        return "whoosh"
    if "resolve" in value or "hit" in value or "impact" in value or "pop" in value:
        return "pop"
    return "tick"


def event_gain(kind: str, level: str) -> float:
    base = {
        "tick": 0.09,
        "shimmer": 0.075,
        "glitch": 0.07,
        "whoosh": 0.08,
        "reverse_hit": 0.07,
        "pop": 0.10,
    }.get(kind, 0.07)
    level = level.lower()
    if "very low" in level:
        base *= 0.62
    elif "low" in level:
        base *= 0.78
    elif "under" in level:
        base *= 0.7
    return base


def collect_sfx_events(timeline: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for beat_index, beat in enumerate(timeline.get("beats", [])):
        beat_id = beat.get("beat_id", f"B{beat_index + 1:02d}")
        beat_start = float(beat.get("start", 0))
        beat_end = float(beat.get("end", beat_start + 1))
        for layer in beat.get("layers", []):
            if not isinstance(layer, dict):
                continue
            if layer.get("type") == "sound_cue":
                layer_level = str(layer.get("level", "low_under_voice"))
                for event in layer.get("events", []) or []:
                    if not isinstance(event, dict):
                        continue
                    events.append(
                        {
                            "beat_id": beat_id,
                            "time": float(event.get("time", layer.get("start", beat_start))),
                            "kind": normalize_kind(str(event.get("kind", layer.get("effect", "")))),
                            "level": str(event.get("level", layer_level)),
                            "description": event.get("description", ""),
                        }
                    )
                if not layer.get("events"):
                    events.append(
                        {
                            "beat_id": beat_id,
                            "time": float(layer.get("start", beat_start)),
                            "kind": normalize_kind(str(layer.get("effect", ""))),
                            "level": layer_level,
                            "description": "compiled sound cue",
                        }
                    )
            elif layer.get("type") == "emphasis_text" and not layer.get("suppressed"):
                effect = str(layer.get("effect", ""))
                if "glitch" in effect or "font_shift" in effect:
                    kind = "glitch"
                elif "highlight" in effect or "wipe" in effect:
                    kind = "shimmer"
                else:
                    kind = "pop"
                events.append(
                    {
                        "beat_id": beat_id,
                        "time": float(layer.get("start", beat_start)),
                        "kind": kind,
                        "level": "very low_under_voice",
                        "description": f"text effect sync: {effect}",
                    }
                )
        if beat_index and beat_start < beat_end:
            events.append(
                {
                    "beat_id": beat_id,
                    "time": beat_start,
                    "kind": "whoosh",
                    "level": "very low_under_voice",
                    "description": "beat transition motion support",
                }
            )
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for event in sorted(events, key=lambda item: float(item["time"])):
        key = (str(event["beat_id"]), int(round(float(event["time"]) * 30)), str(event["kind"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    return deduped


def synth_sample(kind: str, i: int, n: int, rng: random.Random) -> float:
    t = i / SAMPLE_RATE
    p = i / max(1, n - 1)
    if kind == "tick":
        env = math.exp(-p * 18)
        return math.sin(2 * math.pi * 2100 * t) * env
    if kind == "shimmer":
        env = math.sin(math.pi * min(p, 1)) * math.exp(-p * 3)
        return (math.sin(2 * math.pi * (1250 + 900 * p) * t) + 0.28 * rng.uniform(-1, 1)) * env
    if kind == "glitch":
        env = math.exp(-p * 5)
        gate = 1.0 if int(p * 18) % 2 == 0 else -0.4
        freq = 380 + 920 * ((int(p * 12) % 5) / 5)
        return (math.sin(2 * math.pi * freq * t) * 0.8 + rng.uniform(-0.7, 0.7) * 0.35) * env * gate
    if kind == "whoosh":
        env = math.sin(math.pi * p) ** 0.75
        sweep = 120 + 780 * p
        noise = rng.uniform(-1, 1) * (0.4 + 0.6 * p)
        return (math.sin(2 * math.pi * sweep * t) * 0.32 + noise * 0.68) * env
    if kind == "reverse_hit":
        env = p**2
        return (rng.uniform(-1, 1) * 0.55 + math.sin(2 * math.pi * (180 + 400 * p) * t) * 0.45) * env
    env = math.exp(-p * 8)
    return (math.sin(2 * math.pi * 130 * t) * 0.9 + rng.uniform(-1, 1) * 0.35) * env


def duration_for_kind(kind: str) -> float:
    return {
        "tick": 0.08,
        "shimmer": 0.22,
        "glitch": 0.18,
        "whoosh": 0.38,
        "reverse_hit": 0.42,
        "pop": 0.16,
    }.get(kind, 0.12)


def render_sfx_mix(timeline: dict[str, Any], output: Path) -> tuple[Path | None, list[dict[str, Any]]]:
    events = collect_sfx_events(timeline)
    duration = timeline_duration(timeline)
    if not events or duration <= 0:
        return None, []
    total_samples = int((duration + 0.5) * SAMPLE_RATE)
    buffer = [0.0] * total_samples
    for idx, event in enumerate(events):
        kind = str(event["kind"])
        start_sample = max(0, int(float(event["time"]) * SAMPLE_RATE))
        event_samples = int(duration_for_kind(kind) * SAMPLE_RATE)
        gain = event_gain(kind, str(event.get("level", "")))
        rng = random.Random(f"{event.get('beat_id', '')}-{event.get('time', 0)}-{kind}-{idx}")
        for i in range(event_samples):
            pos = start_sample + i
            if pos >= total_samples:
                break
            buffer[pos] += synth_sample(kind, i, event_samples, rng) * gain
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        frames = b"".join(struct.pack("<h", int(clamp(sample, -0.92, 0.92) * 32767)) for sample in buffer)
        wav.writeframes(frames)
    return output, events


def mix_sfx_into_video(video: Path, timeline: dict[str, Any], output: Path, sfx_mix_path: Path) -> tuple[Path, list[dict[str, Any]]]:
    sfx_path, events = render_sfx_mix(timeline, sfx_mix_path)
    if not sfx_path:
        output.write_bytes(video.read_bytes())
        return output, events
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-nostats",
            "-i",
            str(video),
            "-i",
            str(sfx_path),
            "-filter_complex",
            "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.93[a]",
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output),
        ]
    )
    return output, events
