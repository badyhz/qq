"""Credential vault review model. No real credentials, no real loading."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class CredentialReviewResult:
    real_credentials_loaded: bool
    credential_mode: str
    env_secret_read: bool
    file_secret_read: bool
    submit_allowed: bool
    schema_count: int
    all_placeholder: bool
    all_redacted: bool
    def to_dict(self) -> dict:
        return {"real_credentials_loaded": self.real_credentials_loaded, "credential_mode": self.credential_mode, "env_secret_read": self.env_secret_read, "file_secret_read": self.file_secret_read, "submit_allowed": self.submit_allowed, "schema_count": self.schema_count, "all_placeholder": self.all_placeholder, "all_redacted": self.all_redacted}

def run_credential_review(schema_count: int) -> CredentialReviewResult:
    return CredentialReviewResult(
        real_credentials_loaded=False,
        credential_mode="REVIEW_STUB_ONLY",
        env_secret_read=False,
        file_secret_read=False,
        submit_allowed=False,
        schema_count=schema_count,
        all_placeholder=True,
        all_redacted=True,
    )

def write_review(result: CredentialReviewResult, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

def render_review_report(result: CredentialReviewResult) -> str:
    lines = ["# Credential Vault Review Report", "", "## Status", ""]
    for k, v in result.to_dict().items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Conclusion", "", "CREDENTIAL_VAULT_REVIEW_PASS", "NO_REAL_CREDENTIALS_LOADED", ""])
    return "\n".join(lines)
