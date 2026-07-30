"""Deterministic run metrics."""

from __future__ import annotations

from collections import defaultdict
from time import perf_counter

from pydantic import Field

from editorial_brain.core.models import BrainModel


class StageMetric(BrainModel):
    stage: str
    elapsed_seconds: float = Field(ge=0)
    counters: dict[str, int] = Field(default_factory=dict)


class MetricsCollector:
    def __init__(self) -> None:
        self._counters: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._started: dict[str, float] = {}
        self.metrics: list[StageMetric] = []

    def start(self, stage: str) -> None:
        if stage in self._started:
            raise ValueError(f"stage is already running: {stage}")
        self._started[stage] = perf_counter()

    def increment(self, stage: str, name: str, amount: int = 1) -> None:
        self._counters[stage][name] += amount

    def finish(self, stage: str) -> StageMetric:
        started = self._started.pop(stage)
        metric = StageMetric(
            stage=stage,
            elapsed_seconds=perf_counter() - started,
            counters=dict(sorted(self._counters.pop(stage, {}).items())),
        )
        self.metrics.append(metric)
        return metric
