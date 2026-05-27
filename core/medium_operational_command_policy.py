"""T1312 — Medium operational command policy model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumOperationalCommandPolicy:
    """Defines allowed and forbidden shell commands for medium-risk scripts."""

    policy_id: str
    allowed_commands: tuple[str, ...]
    forbidden_commands: tuple[str, ...]
    dry_run_only: bool

    def is_command_allowed(self, command: str) -> bool:
        if command in self.forbidden_commands:
            return False
        if self.allowed_commands and command not in self.allowed_commands:
            return False
        return True

    def is_command_forbidden(self, command: str) -> bool:
        return command in self.forbidden_commands

    def allowed_count(self) -> int:
        return len(self.allowed_commands)

    def forbidden_count(self) -> int:
        return len(self.forbidden_commands)

    def allowed_set(self) -> frozenset[str]:
        return frozenset(self.allowed_commands)

    def forbidden_set(self) -> frozenset[str]:
        return frozenset(self.forbidden_commands)

    def requires_dry_run(self) -> bool:
        return self.dry_run_only
