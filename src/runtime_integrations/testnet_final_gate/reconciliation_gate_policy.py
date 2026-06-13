"""Reconciliation gate policy."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ReconciliationGateRule:
    rule_id: str
    description: str
    enforced: bool
    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "description": self.description, "enforced": self.enforced}

RECON_GATE_RULES = (
    ReconciliationGateRule("position_recon_required", "Position reconciliation required", True),
    ReconciliationGateRule("balance_recon_required", "Balance reconciliation required", True),
    ReconciliationGateRule("warn_blocks", "WARN status blocks submit", True),
    ReconciliationGateRule("blocked_blocks", "BLOCKED status blocks submit", True),
    ReconciliationGateRule("stale_snapshot_blocks", "Stale snapshot blocks submit", True),
    ReconciliationGateRule("no_real_fetch", "No real exchange fetch allowed", True),
)

def get_rules() -> tuple[ReconciliationGateRule, ...]:
    return RECON_GATE_RULES

def write_rules(rules: tuple[ReconciliationGateRule, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in rules], indent=2), encoding="utf-8")
