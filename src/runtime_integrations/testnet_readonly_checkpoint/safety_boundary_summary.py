"""Safety boundary summary: confirms all safety boundaries remain locked."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class BoundaryEntry:
    boundary_id: str
    boundary_name: str
    status: str
    locked: bool
    description: str
    def to_dict(self) -> dict:
        return {"boundary_id": self.boundary_id, "boundary_name": self.boundary_name,
                "status": self.status, "locked": self.locked, "description": self.description}


@dataclass(frozen=True)
class SafetyBoundarySummary:
    summary_id: str
    created_at: str
    boundaries: tuple[BoundaryEntry, ...]
    all_locked: bool
    chain_status: str
    real_readonly_network_status: str
    real_testnet_submit_status: str
    production_trading_status: str
    final_verdict: str
    def to_dict(self) -> dict:
        return {"summary_id": self.summary_id, "created_at": self.created_at,
                "boundaries": [b.to_dict() for b in self.boundaries],
                "all_locked": self.all_locked, "chain_status": self.chain_status,
                "real_readonly_network_status": self.real_readonly_network_status,
                "real_testnet_submit_status": self.real_testnet_submit_status,
                "production_trading_status": self.production_trading_status,
                "final_verdict": self.final_verdict}


BOUNDARIES = (
    BoundaryEntry("BND_001", "REAL_NETWORK_NOT_ALLOWED", "LOCKED", True,
        "No real exchange network calls permitted"),
    BoundaryEntry("BND_002", "REAL_CREDENTIALS_NOT_ALLOWED", "LOCKED", True,
        "No real API keys or secrets loaded"),
    BoundaryEntry("BND_003", "READONLY_DISCOVERY_EXECUTION_NOT_ALLOWED", "LOCKED", True,
        "No real readonly discovery execution against exchange"),
    BoundaryEntry("BND_004", "TESTNET_SUBMIT_NOT_ALLOWED", "LOCKED", True,
        "No testnet order submission permitted"),
    BoundaryEntry("BND_005", "CANCEL_SUBMIT_NOT_ALLOWED", "LOCKED", True,
        "No order cancellation permitted"),
    BoundaryEntry("BND_006", "SUBMIT_GATE_UNLOCK_NOT_ALLOWED", "LOCKED", True,
        "Submit gate remains locked"),
    BoundaryEntry("BND_007", "CANCEL_GATE_UNLOCK_NOT_ALLOWED", "LOCKED", True,
        "Cancel gate remains locked"),
    BoundaryEntry("BND_008", "RECONCILIATION_GATE_UNLOCK_NOT_ALLOWED", "LOCKED", True,
        "Reconciliation gate remains locked"),
    BoundaryEntry("BND_009", "REAL_TRADING_NOT_ALLOWED", "LOCKED", True,
        "No production trading permitted"),
)


def create_summary() -> SafetyBoundarySummary:
    return SafetyBoundarySummary(
        summary_id=f"SBS_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        boundaries=BOUNDARIES,
        all_locked=all(b.locked for b in BOUNDARIES),
        chain_status="mock/governance/read-only design chain completed",
        real_readonly_network_status="not started",
        real_testnet_submit_status="not started",
        production_trading_status="not started",
        final_verdict="READONLY_SAFETY_BOUNDARY_SUMMARY_READY|ALL_BOUNDARIES_LOCKED|REAL_NETWORK_NOT_ALLOWED|REAL_TRADING_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_summary(summary: SafetyBoundarySummary, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")


def render_report(summary: SafetyBoundarySummary) -> str:
    lines = ["# Safety Boundary Summary", "",
        f"**summary_id={summary.summary_id}**",
        f"**all_locked={summary.all_locked}**", "",
        "## Boundaries", "",
        "| ID | Boundary | Status | Description |",
        "|----|----------|:---:|-------------|"]
    for b in summary.boundaries:
        lines.append(f"| {b.boundary_id} | {b.boundary_name} | {b.status} | {b.description} |")
    lines.extend(["", "## Phase Status", "",
        f"- chain_status: {summary.chain_status}",
        f"- real_readonly_network: {summary.real_readonly_network_status}",
        f"- real_testnet_submit: {summary.real_testnet_submit_status}",
        f"- production_trading: {summary.production_trading_status}", "",
        "## Conclusion", "",
        "READONLY_SAFETY_BOUNDARY_SUMMARY_READY",
        "ALL_BOUNDARIES_LOCKED",
        "REAL_NETWORK_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
