"""T1316 — Medium operational no-credential policy model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumOperationalNoCredential:
    """Forbids credential patterns from appearing in medium-risk scripts."""

    policy_id: str
    forbidden_credential_patterns: tuple[str, ...]
    check_function_name: str

    def pattern_count(self) -> int:
        return len(self.forbidden_credential_patterns)

    def pattern_set(self) -> frozenset[str]:
        return frozenset(self.forbidden_credential_patterns)

    def matches_forbidden(self, text: str) -> bool:
        return any(p in text for p in self.forbidden_credential_patterns)

    def get_check_function(self) -> str:
        return self.check_function_name

    def has_patterns(self) -> bool:
        return len(self.forbidden_credential_patterns) > 0
