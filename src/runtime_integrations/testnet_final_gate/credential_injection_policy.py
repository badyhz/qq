"""Credential injection policy."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class InjectionRule:
    rule_id: str
    description: str
    enforced: bool
    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "description": self.description, "enforced": self.enforced}

INJECTION_RULES = (
    InjectionRule("stub_only", "Only stub credential objects allowed", True),
    InjectionRule("all_redacted", "All credential values must be redacted", True),
    InjectionRule("env_disabled", "Environment loading disabled", True),
    InjectionRule("file_disabled", "File loading disabled", True),
    InjectionRule("vault_disabled", "Vault loading disabled", True),
    InjectionRule("least_privilege", "Permissions must be least-privilege", True),
    InjectionRule("no_withdraw", "Withdraw permission forbidden", True),
    InjectionRule("no_trading_yet", "Trading permission not enabled in this task", True),
)

def get_rules() -> tuple[InjectionRule, ...]:
    return INJECTION_RULES

def write_rules(rules: tuple[InjectionRule, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in rules], indent=2), encoding="utf-8")
