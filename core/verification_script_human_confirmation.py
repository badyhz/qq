"""T1327 — Verification script human confirmation model."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationScriptHumanConfirmation:
    """Immutable record of human review confirmation."""

    confirmation_id: str
    reviewer: str
    decision: str
    evidence_refs: tuple[str, ...]

    def is_approved(self) -> bool:
        """Pure: return True if decision is approved."""
        return self.decision == "approved"

    def is_rejected(self) -> bool:
        """Pure: return True if decision is rejected."""
        return self.decision == "rejected"

    def is_deferred(self) -> bool:
        """Pure: return True if decision is deferred."""
        return self.decision == "deferred"

    def has_evidence(self) -> bool:
        """Pure: return True if any evidence refs exist."""
        return len(self.evidence_refs) > 0

    def evidence_count(self) -> int:
        """Pure: return count of evidence refs."""
        return len(self.evidence_refs)

    def summary(self) -> dict[str, str | int]:
        """Pure: return summary dict."""
        return {
            "confirmation_id": self.confirmation_id,
            "reviewer": self.reviewer,
            "decision": self.decision,
            "evidence_count": self.evidence_count(),
        }
