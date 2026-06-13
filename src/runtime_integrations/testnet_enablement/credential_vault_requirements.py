"""Real credential vault requirement checklist."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class Requirement:
    req_id: str
    category: str
    description: str
    status: str  # REQUIRED, DOCUMENTED, DESIGNED, STUB_ONLY
    def to_dict(self) -> dict:
        return {"req_id": self.req_id, "category": self.category, "description": self.description, "status": self.status}

REQUIREMENTS = (
    Requirement("cv_secret_storage", "storage", "Encrypted secret storage backend", "REQUIRED"),
    Requirement("cv_encryption_at_rest", "encryption", "Encryption at rest for all credentials", "REQUIRED"),
    Requirement("cv_access_control", "access", "Role-based access control for credentials", "REQUIRED"),
    Requirement("cv_operator_identity", "identity", "Operator identity verification", "REQUIRED"),
    Requirement("cv_reviewer_identity", "identity", "Reviewer identity verification", "REQUIRED"),
    Requirement("cv_audit_logging", "audit", "Audit logging for all credential access", "REQUIRED"),
    Requirement("cv_key_rotation", "rotation", "Automated key rotation support", "REQUIRED"),
    Requirement("cv_key_revocation", "revocation", "Emergency key revocation", "REQUIRED"),
    Requirement("cv_permission_split", "permissions", "Read-only vs trade permission split", "REQUIRED"),
    Requirement("cv_no_withdraw", "permissions", "Withdraw permission forbidden", "REQUIRED"),
    Requirement("cv_env_isolation", "isolation", "Environment isolation for testnet vs production", "REQUIRED"),
    Requirement("cv_redaction", "redaction", "Credential value redaction in all outputs", "STUB_ONLY"),
    Requirement("cv_incident_response", "incident", "Credential compromise incident response", "REQUIRED"),
)

def get_requirements() -> tuple[Requirement, ...]:
    return REQUIREMENTS

def write_requirements(reqs: tuple[Requirement, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in reqs], indent=2), encoding="utf-8")

def render_report(reqs: tuple[Requirement, ...]) -> str:
    lines = ["# Real Credential Vault Requirement Checklist", "", "**Status: REAL_CREDENTIAL_VAULT_NOT_IMPLEMENTED**", "**Credentials: REAL_CREDENTIALS_NOT_ALLOWED**", "", "| Requirement | Category | Status |", "|-------------|----------|--------|"]
    for r in reqs:
        lines.append(f"| {r.description} | {r.category} | {r.status} |")
    lines.extend(["", "## Conclusion", "", "REAL_CREDENTIAL_VAULT_NOT_IMPLEMENTED", "REAL_CREDENTIALS_NOT_ALLOWED", ""])
    return "\n".join(lines)
