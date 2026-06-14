"""Request signing architecture specification."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class SigningSection:
    section_id: str
    title: str
    content: str
    def to_dict(self) -> dict:
        return {"section_id": self.section_id, "title": self.title, "content": self.content}

SECTIONS = (
    SigningSection("canonical_format", "Canonical Request Format", "METHOD\\nPATH\\nTIMESTAMP\\nNONCE\\nPAYLOAD_HASH. Architecture-only."),
    SigningSection("timestamp_policy", "Timestamp Policy", "Unix epoch milliseconds. Must be within 5 seconds of server time. Clock skew handling required."),
    SigningSection("nonce_policy", "Nonce Policy", "UUID v4 per request. Never reused within timestamp window."),
    SigningSection("payload_hash", "Payload Hashing", "SHA-256 of request body. Empty string for GET requests."),
    SigningSection("signature_algorithm", "Signature Algorithm Placeholder", "HMAC-SHA256 of canonical string with API secret. Placeholder only — no real signing."),
    SigningSection("redaction", "Redaction Requirement", "Secret never logged. Signature redacted in audit logs. Only last 4 chars of key visible."),
    SigningSection("replay_protection", "Replay Protection", "Timestamp + nonce combination prevents replay. Server-side nonce cache recommended."),
    SigningSection("clock_skew", "Clock Skew Handling", "Requests outside 5-second window rejected. NTP sync recommended."),
    SigningSection("signing_failure", "Signing Failure Handling", "Signing failure aborts request. No fallback to unsigned. Incident logged."),
    SigningSection("audit_event", "Audit Event Requirement", "Every signing attempt logged: timestamp, key_id (redacted), success/failure, reason."),
    SigningSection("credential_dep", "Credential Dependency", "Signing requires credential vault with API secret. Not implemented."),
    SigningSection("no_submit_dep", "No-Submit Dependency", "Signing does not grant submit permission. Submit gate remains locked."),
)

def get_sections() -> tuple[SigningSection, ...]:
    return SECTIONS

def write_architecture(sections: tuple[SigningSection, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([s.to_dict() for s in sections], indent=2), encoding="utf-8")

def render_report(sections: tuple[SigningSection, ...]) -> str:
    lines = ["# Request Signing Architecture", "",
        "**signing_mode=ARCHITECTURE_ONLY**",
        "**real_secret_used=false**",
        "**request_sendable=false**",
        "**network_called=false**",
        "**submit_allowed=false**", ""]
    for s in sections:
        lines.extend([f"## {s.title}", "", s.content, ""])
    lines.extend(["## Conclusion", "", "REQUEST_SIGNING_ARCHITECTURE_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
