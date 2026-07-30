"""Deepgram word-timed transcription adapter.

The adapter is optional and imports ``httpx`` only when called. Provider
timestamps are converted immediately to exact microsecond rational time.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from editorial_brain.core.hashing import fingerprint
from editorial_brain.core.models import (
    Confidence,
    EvidenceKind,
    ProviderEvidence,
    ProviderUsage,
    SpeakerSegment,
    Transcript,
    TranscriptWord,
)
from editorial_brain.providers.base import (
    DiarizationOutput,
    DiarizationProvider,
    DiarizationRequest,
    ProviderResult,
    ProviderStatus,
    TranscriptionProvider,
    TranscriptionRequest,
)
from video_engine.api import RationalTime, TimeRange

DEEPGRAM_LISTEN_URL = "https://api.deepgram.com/v1/listen"


class DeepgramTranscriptionProvider(TranscriptionProvider):
    provider_name = "deepgram"

    def __init__(
        self,
        *,
        model: str = "nova-3",
        api_key_env: str = "DEEPGRAM_API_KEY",
        env_file: Path | None = None,
    ) -> None:
        self.model_name = model
        self.api_key_env = api_key_env
        self.env_file = env_file.resolve() if env_file is not None else None

    @property
    def credential_configured(self) -> bool:
        return self._api_key() is not None

    @property
    def credential_source(self) -> str | None:
        if os.environ.get(self.api_key_env):
            return "process_environment"
        if self.env_file is not None and self._api_key() is not None:
            return "project_env_file"
        return None

    @property
    def fingerprint(self) -> str:
        return fingerprint(
            {
                "provider": self.provider_name,
                "model": self.model_name,
                "adapter": "deepgram-listen-v1",
            }
        )

    def transcribe(self, request: TranscriptionRequest) -> ProviderResult[Transcript]:
        api_key = self._api_key()
        if not api_key:
            return ProviderResult(
                status=ProviderStatus.UNAVAILABLE,
                error_code="missing_api_key",
                error_message=f"{self.api_key_env} is not configured",
            )
        if not request.source_path.is_file():
            return ProviderResult(
                status=ProviderStatus.FAILED,
                error_code="source_missing",
                error_message="transcription source does not exist",
            )
        try:
            import httpx
        except ImportError:
            return ProviderResult(
                status=ProviderStatus.UNAVAILABLE,
                error_code="optional_dependency_missing",
                error_message="install the brain-cloud optional dependency",
            )

        params: dict[str, str] = {
            "model": self.model_name,
            "punctuate": "true",
            "smart_format": "true",
            "utterances": "true",
            "diarize": "true" if request.diarize else "false",
            "filler_words": "true" if request.detect_fillers else "false",
        }
        if request.language:
            params["language"] = request.language
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": _content_type(request.source_path),
        }
        last_status: int | None = None
        last_error = "provider request failed"
        response_json: dict[str, Any] | None = None
        response_headers: dict[str, str] = {}
        for attempt in range(request.retry.attempts):
            try:
                response = httpx.post(
                    DEEPGRAM_LISTEN_URL,
                    params=params,
                    headers=headers,
                    content=_file_chunks(request.source_path),
                    timeout=request.timeout_seconds,
                )
                last_status = response.status_code
                response_headers = dict(response.headers)
                if response.status_code == 200:
                    parsed = response.json()
                    if not isinstance(parsed, dict):
                        raise ValueError("Deepgram response root must be an object")
                    response_json = parsed
                    break
                last_error = f"Deepgram returned HTTP {response.status_code}"
                if response.status_code not in request.retry.retry_status_codes:
                    break
            except (httpx.HTTPError, ValueError) as exc:
                last_error = f"Deepgram request failed: {type(exc).__name__}"
            if attempt + 1 < request.retry.attempts:
                _backoff(request, attempt)
        if response_json is None:
            status = ProviderStatus.RATE_LIMITED if last_status == 429 else ProviderStatus.FAILED
            return ProviderResult(
                status=status,
                error_code=f"http_{last_status}" if last_status else "network_error",
                error_message=last_error,
                retryable=last_status in request.retry.retry_status_codes if last_status else True,
            )
        try:
            transcript = self._parse(request, response_json, response_headers)
        except (KeyError, TypeError, ValueError) as exc:
            return ProviderResult(
                status=ProviderStatus.FAILED,
                error_code="invalid_provider_response",
                error_message=f"Deepgram response validation failed: {exc}",
            )
        assert transcript.provider_evidence is not None
        return ProviderResult(
            status=ProviderStatus.SUCCESS,
            output=transcript,
            evidence=transcript.provider_evidence,
        )

    def _api_key(self) -> str | None:
        configured = os.environ.get(self.api_key_env)
        if configured:
            return configured
        if self.env_file is None or not self.env_file.is_file():
            return None
        from dotenv import dotenv_values

        value = dotenv_values(self.env_file).get(self.api_key_env)
        return value if isinstance(value, str) and value else None

    def _parse(
        self,
        request: TranscriptionRequest,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> Transcript:
        results = _object(payload.get("results"), "results")
        channels = _list(results.get("channels"), "results.channels")
        if not channels:
            raise ValueError("Deepgram response contains no channels")
        first_channel = _object(channels[0], "results.channels[0]")
        alternatives = _list(first_channel.get("alternatives"), "alternatives")
        if not alternatives:
            raise ValueError("Deepgram response contains no alternatives")
        alternative = _object(alternatives[0], "alternatives[0]")
        raw_words = _list(alternative.get("words"), "words")
        words: list[TranscriptWord] = []
        speaker_ranges: dict[str, list[TimeRange]] = defaultdict(list)
        for position, raw_word in enumerate(raw_words):
            item = _object(raw_word, f"words[{position}]")
            text = str(item.get("word", "")).strip()
            if not text:
                raise ValueError(f"words[{position}] has blank text")
            start = RationalTime.from_seconds(str(item["start"]), request.timescale)
            end = RationalTime.from_seconds(str(item["end"]), request.timescale)
            source_range = TimeRange.from_start_end(start, end)
            if source_range.is_empty:
                raise ValueError(f"words[{position}] has zero duration")
            speaker_value = item.get("speaker")
            speaker_id = f"speaker_{speaker_value}" if speaker_value is not None else None
            confidence_value = float(item.get("confidence", 0))
            confidence = Confidence(
                score=max(0, min(1, confidence_value)),
                basis=EvidenceKind.MODEL_INFERRED,
                calibration="provider_reported",
            )
            word = TranscriptWord(
                id=f"{request.media_id}:word:{position:08d}",
                text=text,
                punctuated_text=str(item.get("punctuated_word", text)),
                source_range=source_range,
                speaker_id=speaker_id,
                confidence=confidence,
            )
            words.append(word)
            if speaker_id:
                speaker_ranges[speaker_id].append(source_range)
        request_id = headers.get("dg-request-id") or _request_id(payload)
        metadata = _object(payload.get("metadata", {}), "metadata")
        duration = metadata.get("duration")
        evidence = ProviderEvidence(
            provider=self.provider_name,
            model=self.model_name,
            provider_fingerprint=self.fingerprint,
            prompt_fingerprint=fingerprint(
                {
                    "schema": request.schema_version,
                    "prompt": request.prompt_version,
                    "params": {
                        "language": request.language,
                        "diarize": request.diarize,
                        "detect_fillers": request.detect_fillers,
                    },
                }
            ),
            request_id=request_id,
            usage=ProviderUsage(
                audio_seconds=float(duration) if isinstance(duration, (int, float)) else None,
            ),
            confidence=Confidence(
                score=_mean_confidence(words),
                basis=EvidenceKind.MODEL_INFERRED,
                calibration="mean_provider_word_confidence",
                sample_size=len(words) or None,
            ),
        )
        speakers = [
            SpeakerSegment(
                id=f"{request.media_id}:speaker-segment:{position:04d}",
                speaker_id=speaker_id,
                source_range=TimeRange.from_start_end(ranges[0].start, ranges[-1].end),
                confidence=Confidence(
                    score=0.5,
                    basis=EvidenceKind.MODEL_INFERRED,
                    calibration="provider_diarization_unscored",
                ),
            )
            for position, (speaker_id, ranges) in enumerate(sorted(speaker_ranges.items()))
        ]
        return Transcript(
            id=f"transcript:{request.media_id}:{request.media_sha256[:12]}",
            media_id=request.media_id,
            media_sha256=request.media_sha256,
            language=request.language or str(alternative.get("detected_language", "und")),
            words=words,
            speakers=speakers,
            provider_evidence=evidence,
        )


class DeepgramDiarizationProvider(DiarizationProvider):
    """Typed diarization facade over the same Deepgram timed-speaker response."""

    provider_name = "deepgram"

    def __init__(self, *, model: str = "nova-3", api_key_env: str = "DEEPGRAM_API_KEY") -> None:
        self.model_name = model
        self._transcriber = DeepgramTranscriptionProvider(
            model=model,
            api_key_env=api_key_env,
        )

    @property
    def fingerprint(self) -> str:
        return fingerprint(
            {
                "provider": self.provider_name,
                "model": self.model_name,
                "adapter": "deepgram-diarization-v1",
            }
        )

    def diarize(self, request: DiarizationRequest) -> ProviderResult[DiarizationOutput]:
        result = self._transcriber.transcribe(
            TranscriptionRequest(
                request_id=request.request_id,
                timeout_seconds=request.timeout_seconds,
                retry=request.retry,
                schema_version=request.schema_version,
                prompt_version=request.prompt_version,
                media_id=request.media_id,
                media_sha256=request.media_sha256,
                source_path=request.source_path,
                timescale=request.timescale,
                diarize=True,
            )
        )
        if (
            result.status is not ProviderStatus.SUCCESS
            or result.output is None
            or result.evidence is None
        ):
            return ProviderResult(
                status=result.status,
                error_code=result.error_code,
                error_message=result.error_message,
                retryable=result.retryable,
            )
        return ProviderResult(
            status=ProviderStatus.SUCCESS,
            output=DiarizationOutput(speaker_segments=result.output.speakers),
            evidence=result.evidence,
        )


def _backoff(request: TranscriptionRequest, attempt: int) -> None:
    delay = min(
        request.retry.maximum_backoff_seconds,
        request.retry.initial_backoff_seconds * (2**attempt),
    )
    if delay:
        time.sleep(delay)


def _content_type(path: Path) -> str:
    suffixes = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
    }
    return suffixes.get(path.suffix.lower(), "application/octet-stream")


def _file_chunks(path: Path, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    """Stream long media without loading multi-hour sources into memory."""
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            yield chunk


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{path} must be an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{path} must be an array")
    return value


def _request_id(payload: dict[str, Any]) -> str | None:
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        request_id = metadata.get("request_id")
        if isinstance(request_id, str):
            return request_id
    return None


def _mean_confidence(words: list[TranscriptWord]) -> float:
    if not words:
        return 0
    return sum(word.confidence.score for word in words) / len(words)
