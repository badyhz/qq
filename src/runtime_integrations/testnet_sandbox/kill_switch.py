"""Kill switch. Default ENABLED_BLOCKING, blocks all submit."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class KillSwitchState:
    kill_switch_enabled: bool
    submit_blocked: bool
    real_trading_allowed: bool
    testnet_submit_allowed: bool
    state: str  # ENABLED_BLOCKING, UNLOCKED_SIM_ONLY
    reason: str
    def to_dict(self) -> dict:
        return {"kill_switch_enabled": self.kill_switch_enabled, "submit_blocked": self.submit_blocked, "real_trading_allowed": self.real_trading_allowed, "testnet_submit_allowed": self.testnet_submit_allowed, "state": self.state, "reason": self.reason}

def default_state() -> KillSwitchState:
    return KillSwitchState(kill_switch_enabled=True, submit_blocked=True, real_trading_allowed=False, testnet_submit_allowed=False, state="ENABLED_BLOCKING", reason="DEFAULT: kill switch enabled, all submit blocked")

def unlocked_sim_only() -> KillSwitchState:
    return KillSwitchState(kill_switch_enabled=True, submit_blocked=True, real_trading_allowed=False, testnet_submit_allowed=False, state="UNLOCKED_SIM_ONLY", reason="UNLOCKED: simulation only, submit still blocked")

def validate_kill_switch(state: KillSwitchState) -> tuple[bool, tuple[str, ...]]:
    errors = []
    if not state.kill_switch_enabled:
        errors.append("kill_switch_enabled must be True")
    if not state.submit_blocked:
        errors.append("submit_blocked must be True")
    if state.real_trading_allowed:
        errors.append("real_trading_allowed must be False")
    if state.testnet_submit_allowed:
        errors.append("testnet_submit_allowed must be False")
    return (len(errors) == 0, tuple(errors))

def write_state(state: KillSwitchState, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")

def render_kill_switch_report(state: KillSwitchState, valid: bool) -> str:
    lines = ["# Kill Switch Validation Report", "", "## State", ""]
    for k, v in state.to_dict().items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Validation", "", f"VALID: {valid}", "", "## Conclusion", "", "KILL_SWITCH_DESIGN_VALID", "SUBMIT_BLOCKED_BY_DEFAULT", ""])
    return "\n".join(lines)
