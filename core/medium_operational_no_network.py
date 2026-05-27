"""T1317 — Medium operational no-network policy model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumOperationalNoNetwork:
    """Forbids network calls from medium-risk scripts."""

    policy_id: str
    forbidden_network_calls: tuple[str, ...]
    check_function_name: str

    def call_count(self) -> int:
        return len(self.forbidden_network_calls)

    def call_set(self) -> frozenset[str]:
        return frozenset(self.forbidden_network_calls)

    def is_call_forbidden(self, call_name: str) -> bool:
        return call_name in self.forbidden_network_calls

    def get_check_function(self) -> str:
        return self.check_function_name

    def has_restrictions(self) -> bool:
        return len(self.forbidden_network_calls) > 0
