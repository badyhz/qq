"""T1329 — Verification script review verdict model."""
from __future__ import annotations
from dataclasses import dataclass

VALID_VERDICTS = ("pass", "fail", "hold")


@dataclass(frozen=True)
class VerificationScriptReviewVerdict:
    """Immutable verdict produced by a verification script review."""

    verdict: str
    notes: str
    failed_checks: tuple[str, ...]

    def is_pass(self) -> bool:
        """Pure: return True if verdict is pass."""
        return self.verdict == "pass"

    def is_fail(self) -> bool:
        """Pure: return True if verdict is fail."""
        return self.verdict == "fail"

    def is_hold(self) -> bool:
        """Pure: return True if verdict is hold."""
        return self.verdict == "hold"

    def has_failures(self) -> bool:
        """Pure: return True if any failed checks exist."""
        return len(self.failed_checks) > 0

    def failure_count(self) -> int:
        """Pure: return count of failed checks."""
        return len(self.failed_checks)

    def summary(self) -> dict[str, str | int | list[str]]:
        """Pure: return summary dict."""
        return {
            "verdict": self.verdict,
            "failure_count": self.failure_count(),
            "failed_checks": list(self.failed_checks),
            "notes": self.notes,
        }


def build_verdict(
    verdict: str,
    notes: str,
    failed_checks: tuple[str, ...],
) -> VerificationScriptReviewVerdict:
    """Pure: construct a validated verdict. Raises ValueError on invalid verdict."""
    if verdict not in VALID_VERDICTS:
        raise ValueError(
            f"Invalid verdict '{verdict}', must be one of {VALID_VERDICTS}"
        )
    if verdict == "pass" and len(failed_checks) > 0:
        raise ValueError("Verdict 'pass' cannot have failed checks")
    if verdict == "fail" and len(failed_checks) == 0:
        raise ValueError("Verdict 'fail' must have at least one failed check")
    return VerificationScriptReviewVerdict(
        verdict=verdict,
        notes=notes,
        failed_checks=failed_checks,
    )
