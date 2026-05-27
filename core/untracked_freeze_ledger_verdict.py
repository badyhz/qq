from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UntrackedFreezeLedgerVerdict:
    """Frozen verdict for the untracked freeze ledger."""

    verdict: str  # PASS, FAIL, BLOCKED, HOLD
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    notes: str

    VALID_VERDICTS = ("PASS", "FAIL", "BLOCKED", "HOLD")

    def is_pass(self) -> bool:
        return self.verdict == "PASS"

    def is_fail(self) -> bool:
        return self.verdict == "FAIL"

    def is_blocked(self) -> bool:
        return self.verdict == "BLOCKED"

    def is_hold(self) -> bool:
        return self.verdict == "HOLD"

    def total_risk_count(self) -> int:
        return self.high_risk_count + self.medium_risk_count + self.low_risk_count

    def verdict_to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "high_risk_count": self.high_risk_count,
            "medium_risk_count": self.medium_risk_count,
            "low_risk_count": self.low_risk_count,
            "notes": self.notes,
        }


def build_verdict(
    high_risk_count: int,
    medium_risk_count: int,
    low_risk_count: int,
    notes: str = "",
) -> UntrackedFreezeLedgerVerdict:
    """Build a verdict from risk counts.

    Rules:
    - high_risk_count > 0 -> BLOCKED
    - medium_risk_count > 0 and high_risk_count == 0 -> HOLD
    - all zero -> PASS
    - negative counts -> FAIL
    """
    if high_risk_count < 0 or medium_risk_count < 0 or low_risk_count < 0:
        return UntrackedFreezeLedgerVerdict(
            verdict="FAIL",
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            low_risk_count=low_risk_count,
            notes=notes or "Negative risk count detected",
        )

    if high_risk_count > 0:
        return UntrackedFreezeLedgerVerdict(
            verdict="BLOCKED",
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            low_risk_count=low_risk_count,
            notes=notes,
        )

    if medium_risk_count > 0:
        return UntrackedFreezeLedgerVerdict(
            verdict="HOLD",
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            low_risk_count=low_risk_count,
            notes=notes,
        )

    return UntrackedFreezeLedgerVerdict(
        verdict="PASS",
        high_risk_count=high_risk_count,
        medium_risk_count=medium_risk_count,
        low_risk_count=low_risk_count,
        notes=notes,
    )
