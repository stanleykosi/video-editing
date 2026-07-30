"""Decision trace construction."""

from __future__ import annotations

from pydantic import Field

from editorial_brain.core.models import (
    DecisionTrace,
    EditorialDecision,
    JsonValue,
    ProviderUsage,
    VersionedModel,
)


class RunTrace(VersionedModel):
    run_id: str
    stage: str
    elapsed_seconds: float = Field(ge=0)
    counters: dict[str, int] = Field(default_factory=dict)
    provider_usage: ProviderUsage = Field(default_factory=ProviderUsage)
    provider_failures: list[str] = Field(default_factory=list)
    cache_hit: bool = False
    chosen_candidate: str | None = None
    rejected_alternatives: list[str] = Field(default_factory=list)
    details: dict[str, JsonValue] = Field(default_factory=dict)


class TraceBuilder:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._decisions: list[EditorialDecision] = []
        self._stage_metrics: dict[str, JsonValue] = {}

    def decision(self, value: EditorialDecision) -> None:
        if any(existing.id == value.id for existing in self._decisions):
            raise ValueError(f"duplicate decision id {value.id!r}")
        self._decisions.append(value)

    def stage(self, name: str, metrics: JsonValue) -> None:
        self._stage_metrics[name] = metrics

    def build(self) -> DecisionTrace:
        return DecisionTrace(
            run_id=self.run_id,
            decisions=list(self._decisions),
            stage_metrics=dict(sorted(self._stage_metrics.items())),
        )
