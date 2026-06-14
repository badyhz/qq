"""Release blocker ledger: tracks all blockers for read-only discovery release."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class BlockerEntry:
    blocker_id: str
    category: str
    description: str
    severity: str
    status: str
    resolution: str
    def to_dict(self) -> dict:
        return {"blocker_id": self.blocker_id, "category": self.category,
                "description": self.description, "severity": self.severity,
                "status": self.status, "resolution": self.resolution}


@dataclass(frozen=True)
class ReleaseBlockerLedger:
    ledger_id: str
    created_at: str
    stage: str
    blockers: tuple[BlockerEntry, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"ledger_id": self.ledger_id, "created_at": self.created_at,
                "stage": self.stage,
                "blockers": [b.to_dict() for b in self.blockers],
                "final_verdict": self.final_verdict}


BLOCKERS = (
    BlockerEntry("BLK_R001", "NETWORK", "Real network calls not permitted", "CRITICAL", "ACTIVE", "Enforced by code scan"),
    BlockerEntry("BLK_R002", "SUBMIT", "Testnet submit not permitted", "CRITICAL", "ACTIVE", "Enforced by gate lock"),
    BlockerEntry("BLK_R003", "CREDENTIAL", "Real credentials not permitted", "CRITICAL", "ACTIVE", "Enforced by air-gap policy"),
    BlockerEntry("BLK_R004", "CANCEL", "Cancel submit not permitted", "CRITICAL", "ACTIVE", "Enforced by gate lock"),
    BlockerEntry("BLK_R005", "RECONCILIATION", "Reconciliation unlock not permitted", "CRITICAL", "ACTIVE", "Enforced by gate lock"),
    BlockerEntry("BLK_R006", "APPROVAL", "Human approval required for release", "HIGH", "PENDING", "Awaiting human review"),
    BlockerEntry("BLK_R007", "SIGNOFF", "Operator signoff draft not signed", "HIGH", "PENDING", "Draft prepared, awaiting signature"),
    BlockerEntry("BLK_R008", "LEGACY", "High-risk legacy files remain untracked", "MEDIUM", "ACTIVE", "Isolation maintained"),
)


def create_ledger() -> ReleaseBlockerLedger:
    return ReleaseBlockerLedger(
        ledger_id=f"RBL_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        stage="T260001-T275000",
        blockers=BLOCKERS,
        final_verdict="READONLY_DISCOVERY_RELEASE_BLOCKERS_READY|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def count_active(ledger: ReleaseBlockerLedger) -> int:
    return sum(1 for b in ledger.blockers if b.status == "ACTIVE")


def write_ledger(ledger: ReleaseBlockerLedger, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ledger.to_dict(), indent=2), encoding="utf-8")


def render_report(ledger: ReleaseBlockerLedger) -> str:
    lines = ["# Read-Only Discovery Release Blocker Ledger", "",
        f"**ledger_id={ledger.ledger_id}**",
        f"**stage={ledger.stage}**",
        f"**verdict={ledger.final_verdict}**", "",
        "## Blockers", "",
        "| ID | Category | Description | Severity | Status | Resolution |",
        "|----|----------|-------------|----------|--------|------------|"]
    for b in ledger.blockers:
        lines.append(f"| {b.blocker_id} | {b.category} | {b.description} | {b.severity} | {b.status} | {b.resolution} |")
    lines.extend(["", "## Conclusion", "",
        "READONLY_DISCOVERY_RELEASE_BLOCKERS_READY",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
