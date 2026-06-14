"""Final governance freeze: locks all governance decisions for read-only discovery phase."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class GovernanceDecision:
    decision_id: str
    category: str
    description: str
    status: str
    def to_dict(self) -> dict:
        return {"decision_id": self.decision_id, "category": self.category,
                "description": self.description, "status": self.status}


@dataclass(frozen=True)
class FinalGovernanceFreeze:
    freeze_id: str
    created_at: str
    stage: str
    decisions: tuple[GovernanceDecision, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"freeze_id": self.freeze_id, "created_at": self.created_at,
                "stage": self.stage, "decisions": [d.to_dict() for d in self.decisions],
                "final_verdict": self.final_verdict}


DECISIONS = (
    GovernanceDecision("GOV_001", "NETWORK", "Real network calls permanently blocked in read-only phase", "FROZEN"),
    GovernanceDecision("GOV_002", "SUBMIT", "Testnet submit permanently blocked in read-only phase", "FROZEN"),
    GovernanceDecision("GOV_003", "CANCEL", "Cancel submit permanently blocked in read-only phase", "FROZEN"),
    GovernanceDecision("GOV_004", "RECONCILIATION", "Reconciliation unlock permanently blocked in read-only phase", "FROZEN"),
    GovernanceDecision("GOV_005", "CREDENTIAL", "Real credentials permanently blocked in read-only phase", "FROZEN"),
    GovernanceDecision("GOV_006", "APPROVAL", "Human approval required to advance beyond read-only phase", "FROZEN"),
    GovernanceDecision("GOV_007", "GATE_LOCK", "All submit/cancel/recon gates locked", "FROZEN"),
    GovernanceDecision("GOV_008", "RELEASE", "Release governed by no-network no-submit policy", "FROZEN"),
    GovernanceDecision("GOV_009", "AUDIT", "All audit trails preserved and redacted", "FROZEN"),
    GovernanceDecision("GOV_010", "HANDOFF", "Operator handoff document prepared", "FROZEN"),
)


def create_freeze() -> FinalGovernanceFreeze:
    return FinalGovernanceFreeze(
        freeze_id=f"FGF_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        stage="T305001-T320000",
        decisions=DECISIONS,
        final_verdict="READONLY_FINAL_GOVERNANCE_FREEZE_READY|ALL_DECISIONS_FROZEN|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_freeze(freeze: FinalGovernanceFreeze, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(freeze.to_dict(), indent=2), encoding="utf-8")


def render_report(freeze: FinalGovernanceFreeze) -> str:
    lines = ["# Read-Only Final Governance Freeze", "",
        f"**freeze_id={freeze.freeze_id}**",
        f"**stage={freeze.stage}**",
        f"**verdict={freeze.final_verdict}**", "",
        "## Governance Decisions", "",
        "| Decision | Category | Description | Status |",
        "|----------|----------|-------------|--------|"]
    for d in freeze.decisions:
        lines.append(f"| {d.decision_id} | {d.category} | {d.description} | {d.status} |")
    lines.extend(["", "## Conclusion", "",
        "READONLY_FINAL_GOVERNANCE_FREEZE_READY",
        "ALL_DECISIONS_FROZEN",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
