"""Submit gate final lock. Remains locked by default."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class SubmitGateState:
    submit_gate_state: str  # LOCKED, UNLOCKED_SIM_ONLY
    real_submit_allowed: bool
    testnet_submit_allowed: bool
    dry_run_review_ready: bool
    blocking_reasons: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"submit_gate_state": self.submit_gate_state, "real_submit_allowed": self.real_submit_allowed, "testnet_submit_allowed": self.testnet_submit_allowed, "dry_run_review_ready": self.dry_run_review_ready, "blocking_reasons": list(self.blocking_reasons)}

def default_locked() -> SubmitGateState:
    return SubmitGateState(
        submit_gate_state="LOCKED", real_submit_allowed=False, testnet_submit_allowed=False,
        dry_run_review_ready=True,
        blocking_reasons=("MISSING_REAL_CREDENTIAL_VAULT", "MISSING_REAL_EXCHANGE_ADAPTER", "MISSING_HUMAN_APPROVAL_WORKFLOW", "MISSING_KILL_SWITCH_OPERATIONAL_TEST", "MISSING_RECONCILIATION_IMPLEMENTATION"),
    )

def validate_gate(state: SubmitGateState) -> tuple[bool, tuple[str, ...]]:
    errors = []
    if state.submit_gate_state != "LOCKED":
        errors.append("submit_gate_state must be LOCKED")
    if state.real_submit_allowed:
        errors.append("real_submit_allowed must be False")
    if state.testnet_submit_allowed:
        errors.append("testnet_submit_allowed must be False")
    return (len(errors) == 0, tuple(errors))

def write_state(state: SubmitGateState, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")

def render_report(state: SubmitGateState, valid: bool) -> str:
    lines = ["# Submit Gate Final Lock Report", "", "## State", ""]
    for k, v in state.to_dict().items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Validation", "", f"VALID: {valid}", "", "## Conclusion", "", "SUBMIT_GATE_FINAL_LOCKED", ""])
    return "\n".join(lines)
