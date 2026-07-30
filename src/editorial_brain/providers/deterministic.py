"""Network-free deterministic providers for baselines and reproducible tests."""

from __future__ import annotations

import math
import re
from collections import Counter

from editorial_brain.core.hashing import fingerprint
from editorial_brain.core.models import (
    Confidence,
    EvidenceKind,
    ProviderEvidence,
    ProviderUsage,
    Transcript,
)
from editorial_brain.providers.base import (
    EmbeddingOutput,
    EmbeddingProvider,
    EmbeddingRequest,
    FrameInput,
    ProviderResult,
    ProviderStatus,
    SemanticJudgment,
    SemanticOutput,
    SemanticProvider,
    SemanticRequest,
    TranscriptionProvider,
    TranscriptionRequest,
    VisionJudgment,
    VisionOutput,
    VisionProvider,
    VisionRequest,
)

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> list[str]:
    return TOKEN_PATTERN.findall(value.lower())


def _evidence(provider: str, model: str, request: object) -> ProviderEvidence:
    return ProviderEvidence(
        provider=provider,
        model=model,
        provider_fingerprint=fingerprint({"provider": provider, "model": model, "version": 1}),
        prompt_fingerprint=fingerprint(request),
        usage=ProviderUsage(requests=0),
        confidence=Confidence(
            score=1,
            basis=EvidenceKind.DERIVED,
            calibration="deterministic_fixture",
        ),
    )


class DeterministicTranscriptionProvider(TranscriptionProvider):
    provider_name = "deterministic"
    model_name = "fixture-transcript-v1"

    def __init__(self, transcripts_by_sha256: dict[str, Transcript] | None = None) -> None:
        self._transcripts = transcripts_by_sha256 or {}

    @property
    def fingerprint(self) -> str:
        return fingerprint(
            {
                "provider": self.provider_name,
                "model": self.model_name,
                "fixtures": sorted(self._transcripts),
            }
        )

    def transcribe(self, request: TranscriptionRequest) -> ProviderResult[Transcript]:
        transcript = self._transcripts.get(request.media_sha256)
        if transcript is None:
            return ProviderResult(
                status=ProviderStatus.UNAVAILABLE,
                error_code="fixture_missing",
                error_message=f"no deterministic transcript for {request.media_sha256}",
            )
        if (
            transcript.media_id != request.media_id
            or transcript.media_sha256 != request.media_sha256
        ):
            return ProviderResult(
                status=ProviderStatus.FAILED,
                error_code="fixture_identity_mismatch",
                error_message="fixture transcript identity does not match request",
            )
        evidence = _evidence(self.provider_name, self.model_name, request)
        output = transcript.model_copy(update={"provider_evidence": evidence}, deep=True)
        return ProviderResult(status=ProviderStatus.SUCCESS, output=output, evidence=evidence)


class DeterministicSemanticProvider(SemanticProvider):
    provider_name = "deterministic"
    model_name = "lexical-semantic-v1"

    @property
    def fingerprint(self) -> str:
        return fingerprint({"provider": self.provider_name, "model": self.model_name})

    def judge(self, request: SemanticRequest) -> ProviderResult[SemanticOutput]:
        query = Counter(_tokens(f"{request.task} {request.instruction}"))
        judgments: list[SemanticJudgment] = []
        for candidate in sorted(request.candidates, key=lambda value: value.candidate_id):
            candidate_tokens = Counter(_tokens(candidate.summary))
            intersection = sum((query & candidate_tokens).values())
            denominator = max(1, sum(query.values()))
            score = min(1.0, intersection / denominator)
            judgments.append(
                SemanticJudgment(
                    candidate_id=candidate.candidate_id,
                    score=score,
                    labels=sorted(set(query) & set(candidate_tokens)),
                    reasons=(
                        ["lexical overlap with requested editorial need"]
                        if intersection
                        else ["no lexical overlap"]
                    ),
                    confidence=Confidence(
                        score=1,
                        basis=EvidenceKind.DERIVED,
                        calibration="deterministic_lexical",
                    ),
                )
            )
        evidence = _evidence(self.provider_name, self.model_name, request)
        return ProviderResult(
            status=ProviderStatus.SUCCESS,
            output=SemanticOutput(judgments=judgments),
            evidence=evidence,
        )


class DeterministicVisionProvider(VisionProvider):
    provider_name = "deterministic"
    model_name = "caption-vision-v1"

    def __init__(self, labels_by_sha256: dict[str, list[str]] | None = None) -> None:
        self._labels = labels_by_sha256 or {}

    @property
    def fingerprint(self) -> str:
        return fingerprint(
            {"provider": self.provider_name, "model": self.model_name, "labels": self._labels}
        )

    def inspect(self, request: VisionRequest) -> ProviderResult[VisionOutput]:
        query = set(_tokens(f"{request.task} {request.instruction}"))
        judgments: list[VisionJudgment] = []
        for frame in sorted(request.frames, key=lambda value: value.candidate_id):
            labels = self._frame_labels(frame)
            overlap = query & set(_tokens(" ".join(labels)))
            score = len(overlap) / max(1, len(query))
            judgments.append(
                VisionJudgment(
                    candidate_id=frame.candidate_id,
                    summary=frame.caption or ", ".join(labels) or "unlabeled fixture frame",
                    labels=labels,
                    score=min(1, score),
                    observable_cues=labels,
                    confidence=Confidence(
                        score=1,
                        basis=EvidenceKind.DERIVED,
                        calibration="deterministic_fixture",
                    ),
                )
            )
        evidence = _evidence(self.provider_name, self.model_name, request)
        return ProviderResult(
            status=ProviderStatus.SUCCESS,
            output=VisionOutput(judgments=judgments),
            evidence=evidence,
        )

    def _frame_labels(self, frame: FrameInput) -> list[str]:
        return sorted(set(self._labels.get(frame.sha256, [])))


class DeterministicEmbeddingProvider(EmbeddingProvider):
    provider_name = "deterministic"
    model_name = "hashed-bow-v1"

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions <= 0:
            raise ValueError("embedding dimensions must be positive")
        self.dimensions = dimensions

    @property
    def fingerprint(self) -> str:
        return fingerprint(
            {
                "provider": self.provider_name,
                "model": self.model_name,
                "dimensions": self.dimensions,
            }
        )

    def embed(self, request: EmbeddingRequest) -> ProviderResult[EmbeddingOutput]:
        vectors = {key: self._vector(text) for key, text in sorted(request.texts.items())}
        evidence = _evidence(self.provider_name, self.model_name, request)
        return ProviderResult(
            status=ProviderStatus.SUCCESS,
            output=EmbeddingOutput(vectors=vectors),
            evidence=evidence,
        )

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _tokens(text):
            bucket = int(fingerprint(token)[:16], 16) % self.dimensions
            vector[bucket] += 1
        norm = math.sqrt(sum(value * value for value in vector)) or 1
        return [value / norm for value in vector]
