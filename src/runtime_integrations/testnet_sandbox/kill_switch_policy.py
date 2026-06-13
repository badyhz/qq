"""Kill switch policy. Defines rules for kill switch behavior."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class KillSwitchRule:
    rule_id: str
    description: str
    enforced: bool
    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "description": self.description, "enforced": self.enforced}

KILL_SWITCH_RULES = (
    KillSwitchRule("default_blocking", "Kill switch must default to ENABLED_BLOCKING", True),
    KillSwitchRule("no_auto_unlock", "Kill switch must not auto-unlock", True),
    KillSwitchRule("missing_config_blocks", "Missing kill switch config must block submit", True),
    KillSwitchRule("invalid_config_blocks", "Invalid kill switch config must block submit", True),
    KillSwitchRule("unlock_no_real_submit", "Unlock must not allow real submit", True),
    KillSwitchRule("unlock_no_testnet_submit", "Unlock must not allow testnet submit in this phase", True),
)

def get_rules() -> tuple[KillSwitchRule, ...]:
    return KILL_SWITCH_RULES

def write_rules(rules: tuple[KillSwitchRule, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in rules], indent=2), encoding="utf-8")
