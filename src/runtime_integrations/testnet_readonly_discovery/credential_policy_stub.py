"""Credential policy stub."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class CredentialPolicy:
    policy_id: str
    created_at: str
    credential_reference_id: str
    credential_class: str
    allowed_permission_scope: tuple[str, ...]
    prohibited_permission_scope: tuple[str, ...]
    storage_policy: str
    rotation_policy: str
    redaction_policy: str
    audit_policy: str
    human_review_required: bool
    final_decision: str
    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id, "created_at": self.created_at,
            "credential_reference_id": self.credential_reference_id,
            "credential_class": self.credential_class,
            "allowed_permission_scope": list(self.allowed_permission_scope),
            "prohibited_permission_scope": list(self.prohibited_permission_scope),
            "storage_policy": self.storage_policy, "rotation_policy": self.rotation_policy,
            "redaction_policy": self.redaction_policy, "audit_policy": self.audit_policy,
            "human_review_required": self.human_review_required,
            "final_decision": self.final_decision,
        }


VALID_CLASSES = ("PLACEHOLDER_ONLY", "READ_ONLY_TESTNET_CANDIDATE", "REDACTED_REFERENCE")


def create_policy() -> CredentialPolicy:
    return CredentialPolicy(
        policy_id=f"CRP_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        credential_reference_id="CRED_REF_PLACEHOLDER",
        credential_class="PLACEHOLDER_ONLY",
        allowed_permission_scope=("READ_ONLY_TESTNET", "MARKET_DATA_READ", "ACCOUNT_INFO_READ"),
        prohibited_permission_scope=("TRADE", "WITHDRAW", "TRANSFER", "MARGIN", "FUTURES_WRITE"),
        storage_policy="ENCRYPTED_VAULT_PLACEHOLDER",
        rotation_policy="PLACEHOLDER_90_DAY_ROTATION",
        redaction_policy="ALL_VALUES_REDACTED_IN_LOGS",
        audit_policy="ALL_ACCESS_LOGGED_WITH_REDATION",
        human_review_required=True,
        final_decision="CREDENTIAL_POLICY_STUB_READY",
    )


def validate_policy(policy: CredentialPolicy) -> list[dict]:
    errors = []
    if policy.credential_class not in VALID_CLASSES:
        errors.append(f"Invalid credential class: {policy.credential_class}")
    if not policy.human_review_required:
        errors.append("Human review must be required")
    for forbidden in ("RAW_API_KEY", "RAW_SECRET", "LIVE_TRADING_KEY", "WITHDRAWAL_KEY", "PRODUCTION_KEY"):
        if forbidden in policy.credential_class:
            errors.append(f"Forbidden credential class: {forbidden}")
    return [{"valid": len(errors) == 0, "errors": errors}]


def write_policy(policy: CredentialPolicy, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(policy.to_dict(), indent=2), encoding="utf-8")


def render_report(policy: CredentialPolicy) -> str:
    lines = ["# Credential Policy Stub", "",
        f"**policy_id={policy.policy_id}**",
        f"**credential_class={policy.credential_class}**",
        f"**human_review_required={policy.human_review_required}**",
        f"**final_decision={policy.final_decision}**",
        "**REAL_CREDENTIALS_NOT_ALLOWED**", "",
        "## Allowed Scope", ""]
    for s in policy.allowed_permission_scope:
        lines.append(f"- {s}")
    lines.extend(["", "## Prohibited Scope", ""])
    for s in policy.prohibited_permission_scope:
        lines.append(f"- {s}")
    lines.extend(["", "## Policies", "",
        f"- Storage: {policy.storage_policy}",
        f"- Rotation: {policy.rotation_policy}",
        f"- Redaction: {policy.redaction_policy}",
        f"- Audit: {policy.audit_policy}", "",
        "## Conclusion", "",
        "CREDENTIAL_POLICY_STUB_READY",
        "REAL_CREDENTIALS_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
