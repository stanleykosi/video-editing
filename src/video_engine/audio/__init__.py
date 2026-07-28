"""Canonical multitrack-audio types and synthesis helpers."""

from video_engine.core.schema import (
    AudioBus,
    AudioClip,
    AudioRole,
    AudioTrack,
    Effect,
    EffectKind,
    LoudnessProfile,
)
from video_engine.core.time import AudioSampleTime

from .models import SynthEffectEvent, SynthEffectKind, SynthesisRequest, SynthesisResult
from .synthesis import synthesize_effects

__all__ = [
    "AudioBus",
    "AudioClip",
    "AudioRole",
    "AudioSampleTime",
    "AudioTrack",
    "Effect",
    "EffectKind",
    "LoudnessProfile",
    "SynthEffectEvent",
    "SynthEffectKind",
    "SynthesisRequest",
    "SynthesisResult",
    "synthesize_effects",
]
