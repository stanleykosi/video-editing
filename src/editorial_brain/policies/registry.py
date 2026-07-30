"""Policy registry."""

from editorial_brain.policies.dialogue import dialogue_policy
from editorial_brain.policies.models import EditorialPolicy
from editorial_brain.policies.montage import montage_policy
from editorial_brain.policies.narration import narration_policy
from editorial_brain.policies.neutral import neutral_policy


class PolicyRegistry:
    def __init__(self) -> None:
        self._policies = {
            policy.id: policy
            for policy in [
                neutral_policy(),
                dialogue_policy(),
                narration_policy(),
                montage_policy(),
            ]
        }

    def get(self, policy_id: str) -> EditorialPolicy:
        try:
            return self._policies[policy_id].model_copy(deep=True)
        except KeyError as exc:
            raise KeyError(f"unknown editorial policy {policy_id!r}") from exc

    def register(self, policy: EditorialPolicy) -> None:
        if policy.id in self._policies:
            raise ValueError(f"editorial policy already exists: {policy.id!r}")
        self._policies[policy.id] = policy.model_copy(deep=True)

    def ids(self) -> list[str]:
        return sorted(self._policies)
