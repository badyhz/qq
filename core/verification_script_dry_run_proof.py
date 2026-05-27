"""T1323 — Verification script dry-run proof model."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationScriptDryRunProof:
    """Immutable proof that a script ran in dry-run mode."""

    proof_id: str
    script_name: str
    proof_type: str
    evidence_refs: tuple[str, ...]

    def has_evidence(self) -> bool:
        """Pure: return True if any evidence refs exist."""
        return len(self.evidence_refs) > 0

    def evidence_count(self) -> int:
        """Pure: return count of evidence refs."""
        return len(self.evidence_refs)

    def is_stdout_proof(self) -> bool:
        """Pure: return True if proof type is stdout."""
        return self.proof_type == "stdout"

    def is_log_proof(self) -> bool:
        """Pure: return True if proof type is log."""
        return self.proof_type == "log"

    def is_file_proof(self) -> bool:
        """Pure: return True if proof type is file artifact."""
        return self.proof_type == "file"

    def is_composite(self) -> bool:
        """Pure: return True if proof type is composite."""
        return self.proof_type == "composite"

    def summary(self) -> dict[str, str | int]:
        """Pure: return summary dict."""
        return {
            "proof_id": self.proof_id,
            "script_name": self.script_name,
            "proof_type": self.proof_type,
            "evidence_count": self.evidence_count(),
        }
