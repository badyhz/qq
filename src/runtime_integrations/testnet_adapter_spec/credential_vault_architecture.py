"""Credential vault architecture specification."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class VaultSection:
    section_id: str
    title: str
    content: str
    def to_dict(self) -> dict:
        return {"section_id": self.section_id, "title": self.title, "content": self.content}

SECTIONS = (
    VaultSection("secret_storage", "Secret Storage Backend", "AES-256-GCM encrypted file-based storage with master key derived from operator passphrase. Architecture-only."),
    VaultSection("encryption_at_rest", "Encryption at Rest", "All credential values encrypted at rest with AES-256-GCM. Master key never stored in plaintext."),
    VaultSection("encryption_in_transit", "Encryption in Transit", "TLS 1.2+ required for all credential access. Certificate pinning recommended."),
    VaultSection("access_control", "Access Control", "Role-based access: operator (read), reviewer (read), admin (read/write). No anonymous access."),
    VaultSection("operator_identity", "Operator Identity", "Operator must authenticate with MFA before accessing credentials. Identity logged."),
    VaultSection("reviewer_identity", "Reviewer Identity", "Reviewer must authenticate independently. Cannot be same person as operator."),
    VaultSection("least_privilege", "Least Privilege", "Each credential set scoped to minimum required permissions. No blanket access."),
    VaultSection("read_only_key", "Read-Only Key Class", "Separate key class for balance/position reads. Cannot submit orders."),
    VaultSection("trade_key", "Trade Key Class", "Trade-scoped key class. Can submit/cancel orders. Cannot withdraw."),
    VaultSection("no_withdraw", "Withdraw Permission Forbidden", "Withdraw permission must be explicitly forbidden on all keys. Any key with withdraw permission must be revoked immediately."),
    VaultSection("rotation_policy", "Rotation Policy", "Keys rotated every 90 days. Rotation requires human approval. Old keys revoked after rotation."),
    VaultSection("revocation_policy", "Revocation Policy", "Emergency revocation available 24/7. Revocation logged and requires post-incident review."),
    VaultSection("redaction_policy", "Redaction Policy", "All credential values redacted in logs, reports, and outputs. Only last 4 chars visible."),
    VaultSection("audit_trail", "Audit Trail", "Every credential access logged with timestamp, operator, action, and result. Tamper-evident."),
    VaultSection("incident_response", "Incident Response", "Credential compromise triggers immediate revocation, audit review, and stakeholder notification."),
    VaultSection("env_isolation", "Environment Isolation", "Testnet and production credentials stored in separate vaults. No cross-environment access."),
    VaultSection("approval_dep", "Manual Approval Dependency", "Credential creation, rotation, and revocation require human approval. No automated credential lifecycle."),
)

def get_sections() -> tuple[VaultSection, ...]:
    return SECTIONS

def write_architecture(sections: tuple[VaultSection, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([s.to_dict() for s in sections], indent=2), encoding="utf-8")

def render_report(sections: tuple[VaultSection, ...]) -> str:
    lines = ["# Credential Vault Architecture", "",
        "**credential_vault_mode=ARCHITECTURE_ONLY**",
        "**real_credentials_enabled=false**",
        "**env_secret_read=false**",
        "**submit_allowed=false**", ""]
    for s in sections:
        lines.extend([f"## {s.title}", "", s.content, ""])
    lines.extend(["## Conclusion", "", "CREDENTIAL_VAULT_ARCHITECTURE_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
