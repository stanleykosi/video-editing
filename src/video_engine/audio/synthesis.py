"""Deterministic, sample-accurate synthesis for timeline-authored sound cues."""

from __future__ import annotations

import hashlib
import math
import random
import sys
import wave
from array import array
from dataclasses import dataclass

from video_engine.render.cache import sha256_file

from .models import (
    SynthEffectEvent,
    SynthEffectKind,
    SynthesisRequest,
    SynthesisResult,
)

_DEFAULT_DURATIONS = {
    SynthEffectKind.TICK: 0.08,
    SynthEffectKind.SHIMMER: 0.22,
    SynthEffectKind.GLITCH: 0.18,
    SynthEffectKind.WHOOSH: 0.38,
    SynthEffectKind.REVERSE_HIT: 0.42,
    SynthEffectKind.POP: 0.16,
}


@dataclass(frozen=True, slots=True)
class _PreparedEvent:
    start: int
    samples: array[float]


def _sample(
    kind: SynthEffectKind,
    index: int,
    length: int,
    sample_rate: int,
    rng: random.Random,
) -> float:
    time = index / sample_rate
    progress = index / max(1, length - 1)
    if kind is SynthEffectKind.TICK:
        return math.sin(2 * math.pi * 2100 * time) * math.exp(-progress * 18)
    if kind is SynthEffectKind.SHIMMER:
        envelope = math.sin(math.pi * progress) * math.exp(-progress * 3)
        tone = math.sin(2 * math.pi * (1250 + 900 * progress) * time)
        return (tone + 0.28 * rng.uniform(-1, 1)) * envelope
    if kind is SynthEffectKind.GLITCH:
        envelope = math.exp(-progress * 5)
        gate = 1.0 if int(progress * 18) % 2 == 0 else -0.4
        frequency = 380 + 920 * ((int(progress * 12) % 5) / 5)
        tone = math.sin(2 * math.pi * frequency * time) * 0.8
        return (tone + rng.uniform(-0.7, 0.7) * 0.35) * envelope * gate
    if kind is SynthEffectKind.WHOOSH:
        envelope = math.pow(max(0.0, math.sin(math.pi * progress)), 0.75)
        sweep = 120 + 780 * progress
        noise = rng.uniform(-1, 1) * (0.4 + 0.6 * progress)
        return (math.sin(2 * math.pi * sweep * time) * 0.32 + noise * 0.68) * envelope
    if kind is SynthEffectKind.REVERSE_HIT:
        envelope = progress**2
        tone = math.sin(2 * math.pi * (180 + 400 * progress) * time) * 0.45
        return (rng.uniform(-1, 1) * 0.55 + tone) * envelope
    envelope = math.exp(-progress * 8)
    return (math.sin(2 * math.pi * 130 * time) * 0.9 + rng.uniform(-1, 1) * 0.35) * envelope


def _prepare(
    event: SynthEffectEvent,
    sample_rate: int,
    *,
    legacy_recipe: bool,
) -> _PreparedEvent:
    length = event.duration_samples or round(_DEFAULT_DURATIONS[event.kind] * sample_rate)
    if legacy_recipe:
        rng = random.Random(event.seed_key or event.id)
    else:
        seed = hashlib.sha256(
            f"{event.id}:{event.start.samples}:{event.kind.value}:{length}".encode()
        ).digest()
        rng = random.Random(int.from_bytes(seed[:16], "big"))
    samples = array(
        "d",
        (
            _sample(event.kind, index, length, sample_rate, rng) * event.gain
            for index in range(length)
        ),
    )
    return _PreparedEvent(start=event.start.samples, samples=samples)


def synthesize_effects(request: SynthesisRequest) -> SynthesisResult:
    """Write a mono 16-bit WAV without allocating a timeline-sized audio buffer."""
    output = request.output_path.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    legacy_recipe = request.recipe_version == "legacy-video-use-v1"
    prepared = [
        _prepare(event, request.duration.sample_rate, legacy_recipe=legacy_recipe)
        for event in request.events
    ]
    chunk_size = 8192
    with wave.open(str(output), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(request.duration.sample_rate)
        for chunk_start in range(0, request.duration.samples, chunk_size):
            chunk_end = min(request.duration.samples, chunk_start + chunk_size)
            mixed = array("d", [0.0]) * (chunk_end - chunk_start)
            for event in prepared:
                event_end = event.start + len(event.samples)
                overlap_start = max(chunk_start, event.start)
                overlap_end = min(chunk_end, event_end)
                if overlap_end <= overlap_start:
                    continue
                for absolute in range(overlap_start, overlap_end):
                    mixed[absolute - chunk_start] += event.samples[absolute - event.start]
            pcm_values = (
                int(max(-0.92, min(0.92, value)) * 32767)
                if legacy_recipe
                else round(max(-0.92, min(0.92, value)) * 32767)
                for value in mixed
            )
            pcm = array("h", pcm_values)
            if sys.byteorder != "little":
                pcm.byteswap()
            stream.writeframes(pcm.tobytes())
    return SynthesisResult(
        output_path=output,
        sha256=sha256_file(output),
        sample_rate=request.duration.sample_rate,
        sample_count=request.duration.samples,
        event_count=len(request.events),
    )
