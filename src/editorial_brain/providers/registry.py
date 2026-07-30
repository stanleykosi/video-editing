"""Explicit provider registry with capability checks."""

from __future__ import annotations

from editorial_brain.providers.base import Provider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[tuple[str, str], Provider[object]] = {}

    def register(self, capability: str, provider: Provider[object]) -> None:
        key = (capability, provider.provider_name)
        if key in self._providers:
            raise ValueError(
                f"provider already registered for {capability!r}: {provider.provider_name!r}"
            )
        self._providers[key] = provider

    def get(self, capability: str, name: str) -> Provider[object]:
        try:
            return self._providers[(capability, name)]
        except KeyError as exc:
            raise KeyError(f"provider is not registered for {capability!r}: {name!r}") from exc

    def available(self, capability: str) -> list[str]:
        return sorted(
            name
            for (registered_capability, name) in self._providers
            if registered_capability == capability
        )
