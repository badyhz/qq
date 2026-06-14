"""Credential handling SOP."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class SOPSection:
    section_id: str
    title: str
    content: str
    def to_dict(self) -> dict:
        return {"section_id": self.section_id, "title": self.title, "content": self.content}


@dataclass(frozen=True)
class CredentialHandlingSOP:
    sop_id: str
    created_at: str
    sections: tuple[SOPSection, ...]
    def to_dict(self) -> dict:
        return {"sop_id": self.sop_id, "created_at": self.created_at,
                "sections": [s.to_dict() for s in self.sections]}


SECTIONS = (
    SOPSection("SEC_001", "Placeholder Credential Policy",
        "All credentials in current stage are PLACEHOLDER_ONLY. No real API keys, secrets, or tokens are loaded or used. "
        "Credential references use redacted format: KEY_READ_****, KEY_TRADE_****."),
    SOPSection("SEC_002", "Redaction Rules",
        "All credential values must be redacted in logs, reports, and artifacts. "
        "Redaction format: first 4 chars + ****. "
        "Never log raw API keys, secrets, or tokens. "
        "All output files must contain only placeholder or redacted values."),
    SOPSection("SEC_003", "Forbidden Raw Secret Patterns",
        "The following patterns are forbidden in all modules: "
        "RAW_API_KEY, RAW_SECRET, LIVE_TRADING_KEY, WITHDRAWAL_KEY, PRODUCTION_KEY. "
        "No module may read environment variables for exchange credentials. "
        "No module may load dotenv files. "
        "No module may use getpass or input() for credential entry."),
    SOPSection("SEC_004", "Storage Policy",
        "Placeholder credentials are stored in vault_stub_contract.py as frozen dataclasses. "
        "No real credential storage exists. "
        "Future real credentials must use encrypted vault with audit logging."),
    SOPSection("SEC_005", "Rotation Policy Placeholder",
        "Rotation policy is placeholder: 90-day rotation cycle. "
        "Not enforced in current stage. "
        "Real rotation requires vault integration and automated key rollover."),
    SOPSection("SEC_006", "Access Control Placeholder",
        "Access control is placeholder: all modules have equal access to placeholder credentials. "
        "Future real access control requires role-based permission and audit trail."),
    SOPSection("SEC_007", "Audit Logging Requirement",
        "All credential access must be logged with redaction. "
        "Audit log must include: timestamp, module, credential_ref_id, access_type, redacted_value."),
    SOPSection("SEC_008", "Reviewer Checklist",
        "Reviewer must verify: "
        "1) No raw secrets in any module. "
        "2) All credential values are placeholder or redacted. "
        "3) No environment variable or dotenv access for credentials. "
        "4) No real endpoint references. "
        "5) Audit logging is in place."),
    SOPSection("SEC_009", "Operator Prohibition List",
        "Operators are prohibited from: "
        "1) Loading real API keys into the system. "
        "2) Modifying credential stubs to use real values. "
        "3) Disabling redaction in logs. "
        "4) Bypassing human approval for credential changes. "
        "5) Using production credentials in testnet context."),
)


def create_sop() -> CredentialHandlingSOP:
    return CredentialHandlingSOP(
        sop_id=f"SOP_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        sections=SECTIONS,
    )


def write_sop(sop: CredentialHandlingSOP, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sop.to_dict(), indent=2), encoding="utf-8")


def render_report(sop: CredentialHandlingSOP) -> str:
    lines = ["# Credential Handling SOP", "",
        f"**sop_id={sop.sop_id}**",
        "**RAW_SECRET_NOT_ALLOWED**",
        "**REAL_CREDENTIALS_NOT_ALLOWED**",
        "**ENV_SECRET_LOAD_NOT_ALLOWED**", ""]
    for s in sop.sections:
        lines.extend([f"## {s.title}", "", s.content, ""])
    lines.extend(["## Conclusion", "",
        "CREDENTIAL_HANDLING_SOP_READY",
        "REAL_CREDENTIALS_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
