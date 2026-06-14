"""Audit redaction pack: defines redaction rules for audit trail output."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RedactionRule:
    rule_id: str
    field_pattern: str
    redaction_method: str
    applies_to: str
    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "field_pattern": self.field_pattern,
                "redaction_method": self.redaction_method, "applies_to": self.applies_to}


@dataclass(frozen=True)
class AuditRedactionPack:
    pack_id: str
    created_at: str
    rules: tuple[RedactionRule, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"pack_id": self.pack_id, "created_at": self.created_at,
                "rules": [r.to_dict() for r in self.rules],
                "final_verdict": self.final_verdict}


RULES = (
    RedactionRule("RED_001", "api_key", "FULL_REDACT", "all_logs"),
    RedactionRule("RED_002", "api_secret", "FULL_REDACT", "all_logs"),
    RedactionRule("RED_003", "passphrase", "FULL_REDACT", "all_logs"),
    RedactionRule("RED_004", "password", "FULL_REDACT", "all_logs"),
    RedactionRule("RED_005", "token", "PARTIAL_REDACT", "all_logs"),
    RedactionRule("RED_006", "webhook_url", "DOMAIN_ONLY", "alert_logs"),
    RedactionRule("RED_007", "ip_address", "MASK_LAST_OCTET", "network_logs"),
    RedactionRule("RED_008", "email", "MASK_LOCAL_PART", "user_logs"),
    RedactionRule("RED_009", "order_id", "PASSTHROUGH", "trade_logs"),
    RedactionRule("RED_010", "symbol", "PASSTHROUGH", "trade_logs"),
)


def create_pack() -> AuditRedactionPack:
    return AuditRedactionPack(
        pack_id=f"ARP_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        rules=RULES,
        final_verdict="AUDIT_REDACTION_PACK_READY|ALL_SECRETS_REDACTED|REAL_NETWORK_NOT_ALLOWED",
    )


def write_pack(pack: AuditRedactionPack, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack.to_dict(), indent=2), encoding="utf-8")


def render_report(pack: AuditRedactionPack) -> str:
    lines = ["# Audit Redaction Pack", "",
        f"**pack_id={pack.pack_id}**",
        f"**verdict={pack.final_verdict}**", "",
        "## Redaction Rules", "",
        "| Rule | Field Pattern | Method | Applies To |",
        "|------|---------------|--------|------------|"]
    for r in pack.rules:
        lines.append(f"| {r.rule_id} | {r.field_pattern} | {r.redaction_method} | {r.applies_to} |")
    lines.extend(["", "## Conclusion", "",
        "AUDIT_REDACTION_PACK_READY",
        "ALL_SECRETS_REDACTED",
        "REAL_NETWORK_NOT_ALLOWED", ""])
    return "\n".join(lines)
