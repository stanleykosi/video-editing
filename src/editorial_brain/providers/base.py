"""Provider-neutral strict contracts and retry semantics."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import Field, model_validator

from editorial_brain.core.models import (
    BrainModel,
    Confidence,
    ProviderEvidence,
    SpeakerSegment,
    Transcript,
)


class ProviderStatus(StrEnum):
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


class RetryPolicy(BrainModel):
    attempts: int = Field(default=3, ge=1, le=10)
    initial_backoff_seconds: float = Field(default=0.5, ge=0, le=60)
    maximum_backoff_seconds: float = Field(default=8, ge=0, le=300)
    retry_status_codes: tuple[int, ...] = (408, 409, 429, 500, 502, 503, 504)


class ProviderRequest(BrainModel):
    request_id: str = Field(min_length=1)
    timeout_seconds: float = Field(default=120, gt=0, le=3600)
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    schema_version: str = Field(default="1.0.0", min_length=1)
    prompt_version: str = Field(default="1.0.0", min_length=1)


class TranscriptionRequest(ProviderRequest):
    media_id: str = Field(min_length=1)
    media_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_path: Path
    language: str | None = None
    timescale: int = Field(default=1_000_000, gt=0)
    diarize: bool = True
    detect_fillers: bool = True

    @model_validator(mode="after")
    def absolute_safe_source(self) -> TranscriptionRequest:
        if not self.source_path.is_absolute():
            raise ValueError("provider source path must be absolute")
        return self


class CandidateInput(BrainModel):
    candidate_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    attributes: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class SemanticRequest(ProviderRequest):
    task: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    candidates: list[CandidateInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_candidate_ids(self) -> SemanticRequest:
        ids = [candidate.candidate_id for candidate in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("semantic candidate IDs must be unique")
        return self


class FrameInput(BrainModel):
    candidate_id: str = Field(min_length=1)
    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str = Field(default="image/jpeg", pattern=r"^image/[a-zA-Z0-9.+-]+$")
    caption: str = ""

    @model_validator(mode="after")
    def absolute_frame(self) -> FrameInput:
        if not self.path.is_absolute():
            raise ValueError("frame path must be absolute")
        return self


class VisionRequest(ProviderRequest):
    task: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    frames: list[FrameInput] = Field(min_length=1, max_length=64)


class EmbeddingRequest(ProviderRequest):
    texts: dict[str, str] = Field(min_length=1)


class DiarizationRequest(ProviderRequest):
    media_id: str = Field(min_length=1)
    media_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_path: Path
    timescale: int = Field(default=1_000_000, gt=0)


OutputT = TypeVar("OutputT")


class ProviderResult(BrainModel, Generic[OutputT]):
    status: ProviderStatus
    output: OutputT | None = None
    evidence: ProviderEvidence | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    cache_hit: bool = False

    @model_validator(mode="after")
    def coherent_status(self) -> ProviderResult[OutputT]:
        if self.status is ProviderStatus.SUCCESS:
            if self.output is None or self.evidence is None:
                raise ValueError("successful provider result requires output and evidence")
        elif self.output is not None:
            raise ValueError("failed provider result cannot carry output")
        return self


class SemanticJudgment(BrainModel):
    candidate_id: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    labels: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list, max_length=8)
    confidence: Confidence


class SemanticOutput(BrainModel):
    judgments: list[SemanticJudgment]


class VisionJudgment(BrainModel):
    candidate_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    labels: list[str] = Field(default_factory=list)
    score: float = Field(ge=0, le=1)
    observable_cues: list[str] = Field(default_factory=list)
    confidence: Confidence


class VisionOutput(BrainModel):
    judgments: list[VisionJudgment]


class EmbeddingOutput(BrainModel):
    vectors: dict[str, list[float]]


class DiarizationOutput(BrainModel):
    speaker_segments: list[SpeakerSegment]


class Provider(ABC, Generic[OutputT]):
    provider_name: str
    model_name: str

    @property
    @abstractmethod
    def fingerprint(self) -> str:
        raise NotImplementedError


class TranscriptionProvider(Provider[Transcript]):
    @abstractmethod
    def transcribe(self, request: TranscriptionRequest) -> ProviderResult[Transcript]:
        raise NotImplementedError


class SemanticProvider(Provider[SemanticOutput]):
    @abstractmethod
    def judge(self, request: SemanticRequest) -> ProviderResult[SemanticOutput]:
        raise NotImplementedError


class VisionProvider(Provider[VisionOutput]):
    @abstractmethod
    def inspect(self, request: VisionRequest) -> ProviderResult[VisionOutput]:
        raise NotImplementedError


class EmbeddingProvider(Provider[EmbeddingOutput]):
    @abstractmethod
    def embed(self, request: EmbeddingRequest) -> ProviderResult[EmbeddingOutput]:
        raise NotImplementedError


class DiarizationProvider(Provider[DiarizationOutput]):
    @abstractmethod
    def diarize(self, request: DiarizationRequest) -> ProviderResult[DiarizationOutput]:
        raise NotImplementedError
