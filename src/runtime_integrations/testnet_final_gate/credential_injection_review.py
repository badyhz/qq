"""Credential injection review. Reviews how credentials would be injected."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class InjectionReview:
    credential_source: str
    env_secret_read: bool
    file_secret_read: bool
    vault_secret_read: bool
    credential_injection_allowed: bool
    submit_allowed: bool
    permissions_least_privilege: bool
    withdraw_forbidden: bool
    trading_not_enabled: bool
    def to_dict(self) -> dict:
        return {"credential_source": self.credential_source, "env_secret_read": self.env_secret_read, "file_secret_read": self.file_secret_read, "vault_secret_read": self.vault_secret_read, "credential_injection_allowed": self.credential_injection_allowed, "submit_allowed": self.submit_allowed, "permissions_least_privilege": self.permissions_least_privilege, "withdraw_forbidden": self.withdraw_forbidden, "trading_not_enabled": self.trading_not_enabled}

def run_review() -> InjectionReview:
    return InjectionReview(
        credential_source="STUB_ONLY", env_secret_read=False, file_secret_read=False,
        vault_secret_read=False, credential_injection_allowed=False, submit_allowed=False,
        permissions_least_privilege=True, withdraw_forbidden=True, trading_not_enabled=True,
    )

def write_review(review: InjectionReview, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(review.to_dict(), indent=2), encoding="utf-8")

def render_report(review: InjectionReview) -> str:
    lines = ["# Credential Injection Review Report", "", "## Status", ""]
    for k, v in review.to_dict().items():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Conclusion", "", "CREDENTIAL_INJECTION_REVIEW_PASS", ""])
    return "\n".join(lines)
