"""Reconciliation gate final lock."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ReconciliationGateState:
    reconciliation_gate_state: str  # LOCKED
    reconciliation_mode: str  # SIMULATED_ONLY
    network_called: bool
    submit_allowed: bool
    blocking_reasons: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"reconciliation_gate_state": self.reconciliation_gate_state, "reconciliation_mode": self.reconciliation_mode, "network_called": self.network_called, "submit_allowed": self.submit_allowed, "blocking_reasons": list(self.blocking_reasons)}

def default_locked() -> ReconciliationGateState:
    return ReconciliationGateState(
        reconciliation_gate_state="LOCKED", reconciliation_mode="SIMULATED_ONLY",
        network_called=False, submit_allowed=False,
        blocking_reasons=("POSITION_RECON_SIMULATED_ONLY", "BALANCE_RECON_SIMULATED_ONLY", "NO_REAL_EXCHANGE_FETCH"),
    )

def validate_gate(state: ReconciliationGateState) -> tuple[bool, tuple[str, ...]]:
    errors = []
    if state.reconciliation_gate_state != "LOCKED":
        errors.append("reconciliation_gate_state must be LOCKED")
    if state.network_called:
        errors.append("network_called must be False")
    if state.submit_allowed:
        errors.append("submit_allowed must be False")
    return (len(errors) == 0, tuple(errors))

def write_state(state: ReconciliationGateState, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")

def render_report(state: ReconciliationGateState, valid: bool) -> str:
    lines = ["# Reconciliation Gate Final Lock Report", "", "## State", ""]
    for k, v in state.to_dict().items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Validation", "", f"VALID: {valid}", "", "## Conclusion", "", "RECONCILIATION_GATE_FINAL_LOCKED", ""])
    return "\n".join(lines)
