"""T1325 — Verification script side-effect policy model."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationScriptSideEffectPolicy:
    """Immutable policy for detecting forbidden side effects in scripts."""

    policy_id: str
    forbidden_side_effects: tuple[str, ...]
    check_function_name: str

    def is_forbidden(self, side_effect: str) -> bool:
        """Pure: check if a side effect is forbidden."""
        return side_effect in self.forbidden_side_effects

    def forbidden_count(self) -> int:
        """Pure: return count of forbidden side effects."""
        return len(self.forbidden_side_effects)

    def includes_network(self) -> bool:
        """Pure: return True if network I/O is forbidden."""
        return "network" in self.forbidden_side_effects

    def includes_filesystem(self) -> bool:
        """Pure: return True if filesystem writes are forbidden."""
        return "filesystem_write" in self.forbidden_side_effects

    def includes_database(self) -> bool:
        """Pure: return True if database writes are forbidden."""
        return "database_write" in self.forbidden_side_effects

    def includes_subprocess(self) -> bool:
        """Pure: return True if subprocess execution is forbidden."""
        return "subprocess" in self.forbidden_side_effects

    def summary(self) -> dict[str, str | int | list[str]]:
        """Pure: return summary dict."""
        return {
            "policy_id": self.policy_id,
            "check_function_name": self.check_function_name,
            "forbidden_count": self.forbidden_count(),
            "forbidden_list": list(self.forbidden_side_effects),
        }
