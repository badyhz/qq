"""T1322 — Verification script import policy model."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationScriptImportPolicy:
    """Immutable policy governing imports allowed in verification scripts."""

    policy_id: str
    allowed_imports: tuple[str, ...]
    forbidden_imports: tuple[str, ...]
    high_risk_patterns: tuple[str, ...]

    def is_allowed(self, module_name: str) -> bool:
        """Pure: check if module is in allowed list and not forbidden."""
        if module_name in self.forbidden_imports:
            return False
        if not self.allowed_imports:
            return True
        return module_name in self.allowed_imports

    def is_forbidden(self, module_name: str) -> bool:
        """Pure: check if module is explicitly forbidden."""
        return module_name in self.forbidden_imports

    def is_high_risk(self, module_name: str) -> bool:
        """Pure: check if module matches any high-risk pattern."""
        return module_name in self.high_risk_patterns

    def allowed_count(self) -> int:
        """Pure: return count of allowed imports."""
        return len(self.allowed_imports)

    def forbidden_count(self) -> int:
        """Pure: return count of forbidden imports."""
        return len(self.forbidden_imports)

    def validate_import(self, module_name: str) -> str:
        """Pure: return 'allowed', 'forbidden', or 'high_risk'."""
        if module_name in self.forbidden_imports:
            return "forbidden"
        if module_name in self.high_risk_patterns:
            return "high_risk"
        return "allowed"
