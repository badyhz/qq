"""Credential vault stub. No real credentials, no real loading."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class VaultCredential:
    credential_id: str
    label: str
    value_redacted: str  # always redacted
    vault_mode: str  # STUB_ONLY
    real_credentials_loaded: bool  # always False
    env_secret_read: bool  # always False
    submit_allowed: bool  # always False
    def to_dict(self) -> dict:
        return {"credential_id": self.credential_id, "label": self.label, "value_redacted": self.value_redacted, "vault_mode": self.vault_mode, "real_credentials_loaded": self.real_credentials_loaded, "env_secret_read": self.env_secret_read, "submit_allowed": self.submit_allowed}

STUB_CREDENTIALS = (
    VaultCredential("cred_api_key", "Exchange API Key", "***STUB_REDACTED***", "STUB_ONLY", False, False, False),
    VaultCredential("cred_api_secret", "Exchange API Secret", "***STUB_REDACTED***", "STUB_ONLY", False, False, False),
    VaultCredential("cred_webhook", "Feishu Webhook URL", "***STUB_REDACTED***", "STUB_ONLY", False, False, False),
)

@dataclass(frozen=True)
class VaultStubCheck:
    real_credentials_loaded: bool
    env_secret_read: bool
    vault_mode: str
    submit_allowed: bool
    credential_count: int
    all_redacted: bool
    def to_dict(self) -> dict:
        return {"real_credentials_loaded": self.real_credentials_loaded, "env_secret_read": self.env_secret_read, "vault_mode": self.vault_mode, "submit_allowed": self.submit_allowed, "credential_count": self.credential_count, "all_redacted": self.all_redacted}

def check_vault_stub() -> VaultStubCheck:
    return VaultStubCheck(
        real_credentials_loaded=False,
        env_secret_read=False,
        vault_mode="STUB_ONLY",
        submit_allowed=False,
        credential_count=len(STUB_CREDENTIALS),
        all_redacted=all("***STUB_REDACTED***" == c.value_redacted for c in STUB_CREDENTIALS),
    )

def write_vault_check(check: VaultStubCheck, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(check.to_dict(), indent=2), encoding="utf-8")

def render_vault_report(check: VaultStubCheck) -> str:
    lines = ["# Credential Vault Stub Report", "", "## Vault Status", ""]
    for k, v in check.to_dict().items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Conclusion", "", "CREDENTIAL_VAULT_STUB_VALID", "NO_REAL_CREDENTIALS_LOADED", ""])
    return "\n".join(lines)
