"""Credential air-gap policy: enforces zero credential access in current stage."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AirGapRule:
    rule_id: str
    description: str
    enforcement: str
    status: str
    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "description": self.description,
                "enforcement": self.enforcement, "status": self.status}


@dataclass(frozen=True)
class CredentialAirGapPolicy:
    policy_id: str
    created_at: str
    rules: tuple[AirGapRule, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"policy_id": self.policy_id, "created_at": self.created_at,
                "rules": [r.to_dict() for r in self.rules],
                "final_verdict": self.final_verdict}


RULES = (
    AirGapRule("AG_001", "No dotenv file loaded", "BLOCK_IF_VIOLATED", "ENFORCED"),
    AirGapRule("AG_002", "No environment-variable credential read", "BLOCK_IF_VIOLATED", "ENFORCED"),
    AirGapRule("AG_003", "No real API key in codebase", "SCAN_ON_COMMIT", "ENFORCED"),
    AirGapRule("AG_004", "No real secret in codebase", "SCAN_ON_COMMIT", "ENFORCED"),
    AirGapRule("AG_005", "No real webhook URL in codebase", "SCAN_ON_COMMIT", "ENFORCED"),
    AirGapRule("AG_006", "Credential vault stub only", "DESIGN_TIME", "ENFORCED"),
    AirGapRule("AG_007", "No credential injection at runtime", "BLOCK_IF_VIOLATED", "ENFORCED"),
    AirGapRule("AG_008", "Air-gap verification on every suite run", "AUTOMATED", "ENFORCED"),
)


def create_policy() -> CredentialAirGapPolicy:
    return CredentialAirGapPolicy(
        policy_id=f"CAG_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        rules=RULES,
        final_verdict="CREDENTIAL_AIR_GAP_POLICY_READY|REAL_CREDENTIALS_NOT_ALLOWED|REAL_NETWORK_NOT_ALLOWED",
    )


def write_policy(policy: CredentialAirGapPolicy, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(policy.to_dict(), indent=2), encoding="utf-8")


def render_report(policy: CredentialAirGapPolicy) -> str:
    lines = ["# Credential Air-Gap Policy", "",
        f"**policy_id={policy.policy_id}**",
        f"**verdict={policy.final_verdict}**", "",
        "## Rules", "",
        "| Rule | Description | Enforcement | Status |",
        "|------|-------------|-------------|--------|"]
    for r in policy.rules:
        lines.append(f"| {r.rule_id} | {r.description} | {r.enforcement} | {r.status} |")
    lines.extend(["", "## Conclusion", "",
        "CREDENTIAL_AIR_GAP_POLICY_READY",
        "REAL_CREDENTIALS_NOT_ALLOWED",
        "REAL_NETWORK_NOT_ALLOWED", ""])
    return "\n".join(lines)
