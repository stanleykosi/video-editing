"""Provider usage and cost aggregation."""

from __future__ import annotations

from editorial_brain.core.models import ProviderEvidence, ProviderUsage


def aggregate_usage(evidence: list[ProviderEvidence]) -> ProviderUsage:
    input_tokens = sum(item.usage.input_tokens or 0 for item in evidence)
    output_tokens = sum(item.usage.output_tokens or 0 for item in evidence)
    audio_seconds = sum(item.usage.audio_seconds or 0 for item in evidence)
    cost_values = [item.usage.cost_usd for item in evidence if item.usage.cost_usd is not None]
    return ProviderUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        audio_seconds=audio_seconds,
        requests=sum(item.usage.requests for item in evidence),
        cost_usd=sum(cost_values) if cost_values else None,
    )
