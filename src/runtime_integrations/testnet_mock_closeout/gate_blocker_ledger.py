"""Gate blocker ledger."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class GateBlocker:
    blocker_id: str
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM
    description: str
    current_status: str  # BLOCKED, NOT_STARTED, IN_PROGRESS
    required_evidence: str
    unlock_dependency: str
    owner_placeholder: str
    final_decision: str
    def to_dict(self) -> dict:
        return {"blocker_id": self.blocker_id, "category": self.category, "severity": self.severity, "description": self.description, "current_status": self.current_status, "required_evidence": self.required_evidence, "unlock_dependency": self.unlock_dependency, "owner_placeholder": self.owner_placeholder, "final_decision": self.final_decision}


@dataclass(frozen=True)
class GateBlockerLedger:
    ledger_id: str
    created_at: str
    blockers: tuple[GateBlocker, ...]
    def to_dict(self) -> dict:
        return {"ledger_id": self.ledger_id, "created_at": self.created_at, "blockers": [b.to_dict() for b in self.blockers]}


BLOCKERS = (
    GateBlocker("BLK_001", "credential", "CRITICAL", "No real credential review completed", "BLOCKED", "Credential vault audit with real key rotation plan", "submit_unlock", "security_team", "BLOCKER_ACTIVE"),
    GateBlocker("BLK_002", "permission", "CRITICAL", "No exchange permission review completed", "BLOCKED", "Exchange account permission audit report", "submit_unlock", "compliance_team", "BLOCKER_ACTIVE"),
    GateBlocker("BLK_003", "approval", "CRITICAL", "No human approval for testnet submit", "BLOCKED", "Signed human approval with scope and date", "submit_unlock", "operator", "BLOCKER_ACTIVE"),
    GateBlocker("BLK_004", "safety", "HIGH", "No kill switch field validation", "BLOCKED", "Kill switch tested in live-like environment", "submit_unlock", "engineering", "BLOCKER_ACTIVE"),
    GateBlocker("BLK_005", "safety", "HIGH", "No rollback field validation", "BLOCKED", "Rollback procedure tested end-to-end", "submit_unlock", "engineering", "BLOCKER_ACTIVE"),
    GateBlocker("BLK_006", "risk", "HIGH", "No notional limit field validation", "BLOCKED", "Notional limits enforced in real execution path", "submit_unlock", "risk_team", "BLOCKER_ACTIVE"),
    GateBlocker("BLK_007", "discovery", "HIGH", "No read-only discovery completed", "BLOCKED", "Read-only testnet API discovery report", "submit_unlock", "engineering", "BLOCKER_ACTIVE"),
    GateBlocker("BLK_008", "adapter", "CRITICAL", "No real adapter implementation approved", "BLOCKED", "Real adapter code reviewed and approved", "submit_unlock", "engineering", "BLOCKER_ACTIVE"),
    GateBlocker("BLK_009", "submit", "CRITICAL", "No testnet submit approval", "BLOCKED", "Testnet submit approval with risk assessment", "submit_unlock", "operator", "BLOCKER_ACTIVE"),
    GateBlocker("BLK_010", "cancel", "HIGH", "No cancel safety live validation", "BLOCKED", "Cancel safety validated in testnet", "cancel_unlock", "engineering", "BLOCKER_ACTIVE"),
    GateBlocker("BLK_011", "reconciliation", "HIGH", "No reconciliation live validation", "BLOCKED", "Reconciliation validated in testnet", "recon_unlock", "engineering", "BLOCKER_ACTIVE"),
)


def create_ledger() -> GateBlockerLedger:
    return GateBlockerLedger(
        ledger_id=f"GLD_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        blockers=BLOCKERS,
    )


def count_by_severity(ledger: GateBlockerLedger) -> dict[str, int]:
    counts: dict[str, int] = {}
    for b in ledger.blockers:
        counts[b.severity] = counts.get(b.severity, 0) + 1
    return counts


def count_by_category(ledger: GateBlockerLedger) -> dict[str, int]:
    counts: dict[str, int] = {}
    for b in ledger.blockers:
        counts[b.category] = counts.get(b.category, 0) + 1
    return counts


def write_ledger(ledger: GateBlockerLedger, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ledger.to_dict(), indent=2), encoding="utf-8")


def render_report(ledger: GateBlockerLedger) -> str:
    lines = ["# Gate Blocker Ledger", "",
        f"**ledger_id={ledger.ledger_id}**",
        f"**total_blockers={len(ledger.blockers)}**",
        "**SUBMIT_UNLOCK_BLOCKED**",
        "**REAL_TRADING_NOT_ALLOWED**", "",
        "## Blockers", "",
        "| ID | Category | Severity | Status | Decision |",
        "|----|----------|----------|--------|----------|"]
    for b in ledger.blockers:
        lines.append(f"| {b.blocker_id} | {b.category} | {b.severity} | {b.current_status} | {b.final_decision} |")
    by_sev = count_by_severity(ledger)
    lines.extend(["", "## Severity Summary", ""])
    for sev, count in sorted(by_sev.items()):
        lines.append(f"- {sev}: {count}")
    lines.extend(["", "## Conclusion", "",
        "GATE_BLOCKER_LEDGER_READY",
        "SUBMIT_UNLOCK_BLOCKED",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
