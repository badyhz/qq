"""Cancel gate final lock. Remains simulation-only."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class CancelGateState:
    cancel_gate_state: str  # LOCKED
    real_cancel_allowed: bool
    testnet_cancel_allowed: bool
    simulated_cancel_only: bool
    blocking_reasons: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"cancel_gate_state": self.cancel_gate_state, "real_cancel_allowed": self.real_cancel_allowed, "testnet_cancel_allowed": self.testnet_cancel_allowed, "simulated_cancel_only": self.simulated_cancel_only, "blocking_reasons": list(self.blocking_reasons)}

def default_locked() -> CancelGateState:
    return CancelGateState(
        cancel_gate_state="LOCKED", real_cancel_allowed=False, testnet_cancel_allowed=False,
        simulated_cancel_only=True,
        blocking_reasons=("MISSING_REAL_CANCEL_API", "MISSING_REAL_ORDER_TRACKING", "CANCEL_GATE_LOCKED"),
    )

def validate_gate(state: CancelGateState) -> tuple[bool, tuple[str, ...]]:
    errors = []
    if state.cancel_gate_state != "LOCKED":
        errors.append("cancel_gate_state must be LOCKED")
    if state.real_cancel_allowed:
        errors.append("real_cancel_allowed must be False")
    if state.testnet_cancel_allowed:
        errors.append("testnet_cancel_allowed must be False")
    if not state.simulated_cancel_only:
        errors.append("simulated_cancel_only must be True")
    return (len(errors) == 0, tuple(errors))

def write_state(state: CancelGateState, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")

def render_report(state: CancelGateState, valid: bool) -> str:
    lines = ["# Cancel Gate Final Lock Report", "", "## State", ""]
    for k, v in state.to_dict().items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Validation", "", f"VALID: {valid}", "", "## Conclusion", "", "CANCEL_GATE_FINAL_LOCKED", ""])
    return "\n".join(lines)
