"""T1326 — Verification script regression requirement model."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationScriptRegressionRequirement:
    """Immutable regression test requirement for verification scripts."""

    requirement_id: str
    test_name: str
    expected_result: Any
    mandatory: bool

    def is_mandatory(self) -> bool:
        """Pure: return True if requirement is mandatory."""
        return self.mandatory

    def is_optional(self) -> bool:
        """Pure: return True if requirement is optional."""
        return not self.mandatory

    def check_result(self, actual_result: Any) -> bool:
        """Pure: compare actual result against expected."""
        return actual_result == self.expected_result

    def result_status(self, actual_result: Any) -> str:
        """Pure: return 'pass', 'fail', or 'skip'."""
        if not self.mandatory:
            return "skip"
        return "pass" if self.check_result(actual_result) else "fail"

    def summary(self) -> dict[str, Any]:
        """Pure: return summary dict."""
        return {
            "requirement_id": self.requirement_id,
            "test_name": self.test_name,
            "mandatory": self.mandatory,
            "expected_result": repr(self.expected_result),
        }
