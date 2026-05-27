"""T1321 — Verification script review model."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationScriptReview:
    """Immutable review record for a verification script."""

    review_id: str
    script_name: str
    checks: tuple[str, ...]
    verdict: str

    def has_check(self, check_name: str) -> bool:
        """Pure: return whether a named check exists."""
        return check_name in self.checks

    def check_count(self) -> int:
        """Pure: return number of checks."""
        return len(self.checks)

    def is_pass(self) -> bool:
        """Pure: return True if verdict is 'pass'."""
        return self.verdict == "pass"

    def is_hold(self) -> bool:
        """Pure: return True if verdict is 'hold'."""
        return self.verdict == "hold"

    def is_fail(self) -> bool:
        """Pure: return True if verdict is 'fail'."""
        return self.verdict == "fail"

    def summary(self) -> dict[str, Any]:
        """Pure: return summary dict."""
        return {
            "review_id": self.review_id,
            "script_name": self.script_name,
            "check_count": self.check_count(),
            "verdict": self.verdict,
        }
