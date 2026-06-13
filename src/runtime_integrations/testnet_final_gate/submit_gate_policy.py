"""Submit gate policy."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class SubmitGateRule:
    rule_id: str
    description: str
    enforced: bool
    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "description": self.description, "enforced": self.enforced}

SUBMIT_GATE_RULES = (
    SubmitGateRule("default_locked", "Submit gate defaults to LOCKED", True),
    SubmitGateRule("missing_approval_blocks", "Missing approval blocks submit", True),
    SubmitGateRule("stale_approval_blocks", "Stale approval blocks submit", True),
    SubmitGateRule("missing_credential_review_blocks", "Missing credential review blocks submit", True),
    SubmitGateRule("missing_kill_switch_blocks", "Missing kill switch check blocks submit", True),
    SubmitGateRule("missing_reconciliation_blocks", "Missing reconciliation blocks submit", True),
    SubmitGateRule("missing_audit_log_blocks", "Missing audit log blocks submit", True),
)

def get_rules() -> tuple[SubmitGateRule, ...]:
    return SUBMIT_GATE_RULES

def write_rules(rules: tuple[SubmitGateRule, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in rules], indent=2), encoding="utf-8")
