"""Credential policy. Defines rules for credential handling."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class CredentialRule:
    rule_id: str
    description: str
    enforced: bool
    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "description": self.description, "enforced": self.enforced}

CREDENTIAL_RULES = (
    CredentialRule("no_real_keys", "Real API keys must never be loaded", True),
    CredentialRule("no_env_secrets", "Environment secrets must not be read", True),
    CredentialRule("stub_only", "Vault must operate in STUB_ONLY mode", True),
    CredentialRule("redacted_output", "All credential output must be redacted", True),
    CredentialRule("no_submit_with_creds", "Credentials must never enable submit", True),
    CredentialRule("no_file_write_creds", "Credentials must never be written to files", True),
)

def get_rules() -> tuple[CredentialRule, ...]:
    return CREDENTIAL_RULES

def write_rules(rules: tuple[CredentialRule, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in rules], indent=2), encoding="utf-8")
