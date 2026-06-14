"""Vault stub contract for external testnet adapter."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class CredentialReference:
    ref_id: str
    key_id: str
    key_class: str  # read_only, trade, admin
    environment: str  # testnet, production
    redacted: bool
    placeholder: bool
    def to_dict(self) -> dict:
        return {"ref_id": self.ref_id, "key_id": self.key_id, "key_class": self.key_class, "environment": self.environment, "redacted": self.redacted, "placeholder": self.placeholder}

@dataclass(frozen=True)
class VaultStubState:
    mode: str  # STUB_ONLY
    real_credentials_enabled: bool
    env_secret_read: bool
    submit_allowed: bool
    credential_references: tuple[CredentialReference, ...]
    def to_dict(self) -> dict:
        return {"mode": self.mode, "real_credentials_enabled": self.real_credentials_enabled, "env_secret_read": self.env_secret_read, "submit_allowed": self.submit_allowed, "credential_references": [r.to_dict() for r in self.credential_references]}

STUB_CREDENTIALS = (
    CredentialReference("ref_read_only", "KEY_READ_****", "read_only", "testnet", True, True),
    CredentialReference("ref_trade", "KEY_TRADE_****", "trade", "testnet", True, True),
)

def create_stub_state() -> VaultStubState:
    return VaultStubState(
        mode="STUB_ONLY",
        real_credentials_enabled=False,
        env_secret_read=False,
        submit_allowed=False,
        credential_references=STUB_CREDENTIALS,
    )

def write_stub(state: VaultStubState, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")

def render_report(state: VaultStubState) -> str:
    lines = ["# Vault Stub Contract", "",
        f"**vault_mode={state.mode}**",
        f"**real_credentials_enabled={state.real_credentials_enabled}**",
        f"**env_secret_read={state.env_secret_read}**",
        f"**submit_allowed={state.submit_allowed}**", "",
        "## Credential References", ""]
    for ref in state.credential_references:
        lines.append(f"- {ref.ref_id}: key_id={ref.key_id}, class={ref.key_class}, env={ref.environment}, redacted={ref.redacted}, placeholder={ref.placeholder}")
    lines.extend(["", "## Conclusion", "", "VAULT_STUB_CONTRACT_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
