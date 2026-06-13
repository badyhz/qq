"""Cancel gate policy."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class CancelGateRule:
    rule_id: str
    description: str
    enforced: bool
    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "description": self.description, "enforced": self.enforced}

CANCEL_GATE_RULES = (
    CancelGateRule("default_locked", "Cancel gate defaults to LOCKED", True),
    CancelGateRule("unknown_order_blocks", "Unknown order cancel blocks", True),
    CancelGateRule("terminal_order_blocks", "Terminal order cancel blocks", True),
    CancelGateRule("missing_approval_blocks", "Missing approval blocks cancel", True),
    CancelGateRule("kill_switch_blocks", "Kill switch blocks cancel", True),
    CancelGateRule("no_real_cancel", "No real cancel allowed", True),
)

def get_rules() -> tuple[CancelGateRule, ...]:
    return CANCEL_GATE_RULES

def write_rules(rules: tuple[CancelGateRule, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in rules], indent=2), encoding="utf-8")
