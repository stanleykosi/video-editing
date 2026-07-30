"""Structured phrase semantics over verified phrase candidates."""

from __future__ import annotations

from editorial_brain.core.models import MediaUnderstandingIndex, Transcript
from editorial_brain.providers.base import (
    CandidateInput,
    ProviderStatus,
    SemanticProvider,
    SemanticRequest,
)

PHRASE_KINDS = {
    "question",
    "claim",
    "punchline",
    "topic_change",
    "false_start",
    "repeated_attempt",
}


def enrich_speech_semantics(
    index: MediaUnderstandingIndex, provider: SemanticProvider
) -> MediaUnderstandingIndex:
    candidates = [
        CandidateInput(
            candidate_id=phrase.id,
            summary=phrase.text,
            attributes={"speaker_id": phrase.speaker_id},
        )
        for transcript in index.transcripts
        for phrase in transcript.phrases
    ]
    if not candidates:
        return index
    result = provider.judge(
        SemanticRequest(
            request_id=f"speech-semantics:{index.project_id}:{index.analysis_version}",
            task="speech_semantics",
            instruction=(
                "Classify each phrase only when supported as question, claim, punchline, "
                "topic_change, false_start, or repeated_attempt; score editorial emphasis."
            ),
            candidates=candidates,
        )
    )
    if result.status is ProviderStatus.UNAVAILABLE:
        current = index.extensions.get("editorial_brain:provider_unavailable", [])
        previous = [str(item) for item in current] if isinstance(current, list) else []
        unavailable = [
            *previous,
            f"{provider.provider_name}:{result.error_code or 'unavailable'}",
        ]
        return index.model_copy(
            update={
                "extensions": {
                    **index.extensions,
                    "editorial_brain:provider_unavailable": unavailable,
                }
            },
            deep=True,
        )
    if (
        result.status is not ProviderStatus.SUCCESS
        or result.output is None
        or result.evidence is None
    ):
        raise RuntimeError(result.error_message or "semantic provider failed")
    judgments = {judgment.candidate_id: judgment for judgment in result.output.judgments}
    transcripts: list[Transcript] = []
    for transcript in index.transcripts:
        phrases = []
        for phrase in transcript.phrases:
            judgment = judgments[phrase.id]
            kinds = sorted(PHRASE_KINDS & {label.lower() for label in judgment.labels})
            phrases.append(
                phrase.model_copy(
                    update={
                        "kind": kinds[0] if kinds else phrase.kind,
                        "emphasis": judgment.score,
                        "confidence": judgment.confidence,
                    }
                )
            )
        transcripts.append(transcript.model_copy(update={"phrases": phrases}))
    return index.model_copy(
        update={
            "transcripts": transcripts,
            "provider_evidence": [*index.provider_evidence, result.evidence],
        }
    )
