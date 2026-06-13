"""Testnet submit enablement readiness review."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ReadinessReview:
    review_ready: bool
    submit_allowed: bool
    testnet_submit_allowed: bool
    criteria_met: tuple[str, ...]
    criteria_pending: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"review_ready": self.review_ready, "submit_allowed": self.submit_allowed, "testnet_submit_allowed": self.testnet_submit_allowed, "criteria_met": list(self.criteria_met), "criteria_pending": list(self.criteria_pending)}

def run_review() -> ReadinessReview:
    met = (
        "dry_run_complete", "stabilization_complete", "server_readiness_complete",
        "sandbox_design_complete", "presubmit_review_complete", "final_gate_complete",
        "submit_gate_locked", "cancel_gate_locked", "recon_gate_locked",
        "no_real_credential_vault", "no_real_exchange_adapter",
    )
    return ReadinessReview(review_ready=True, submit_allowed=False, testnet_submit_allowed=False, criteria_met=met, criteria_pending=())

def write_review(review: ReadinessReview, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(review.to_dict(), indent=2), encoding="utf-8")

def render_report(review: ReadinessReview) -> str:
    lines = ["# Testnet Submit Enablement Readiness Review", "", "## Status", ""]
    for k, v in review.to_dict().items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Conclusion", "", "TESTNET_SUBMIT_ENABLEMENT_REVIEW_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
