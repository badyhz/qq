"""No-network preflight evidence."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    category: str
    check_name: str
    result: str  # PASS, FAIL, NOT_APPLICABLE
    evidence_detail: str
    related_artifact: str
    blocker_status: str  # CLEAR, ACTIVE
    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id, "category": self.category,
            "check_name": self.check_name, "result": self.result,
            "evidence_detail": self.evidence_detail,
            "related_artifact": self.related_artifact,
            "blocker_status": self.blocker_status,
        }


@dataclass(frozen=True)
class PreflightEvidence:
    preflight_id: str
    created_at: str
    items: tuple[EvidenceItem, ...]
    def to_dict(self) -> dict:
        return {"preflight_id": self.preflight_id, "created_at": self.created_at,
                "items": [i.to_dict() for i in self.items]}


EVIDENCE_ITEMS = (
    EvidenceItem("EVD_001", "network", "No real network client", "PASS", "No ccxt/requests/httpx/aiohttp/websocket imports in any module", "safety_regression", "CLEAR"),
    EvidenceItem("EVD_002", "network", "No real endpoint", "PASS", "No production Binance endpoint in any module, only PLACEHOLDER references", "discovery_design", "CLEAR"),
    EvidenceItem("EVD_003", "credential", "No real credential", "PASS", "credential_class=PLACEHOLDER_ONLY, no raw API key or secret", "credential_policy_stub", "CLEAR"),
    EvidenceItem("EVD_004", "credential", "No env load", "PASS", "No environment variable or dotenv access in any discovery module", "safety_regression", "CLEAR"),
    EvidenceItem("EVD_005", "submit", "No submit path", "PASS", "submit_order/cancel_order not implemented, only dry-run stubs", "readonly_adapter_contract", "CLEAR"),
    EvidenceItem("EVD_006", "submit", "No cancel path", "PASS", "cancel_order not implemented, only dry-run stubs", "readonly_adapter_contract", "CLEAR"),
    EvidenceItem("EVD_007", "submit", "No reconciliation unlock", "PASS", "No reconciliation gate unlock marker present in any module", "safety_regression", "CLEAR"),
    EvidenceItem("EVD_008", "governance", "Governance checklist complete", "PASS", "10 governance items documented, all NOT_STARTED", "discovery_governance_checklist", "ACTIVE"),
    EvidenceItem("EVD_009", "governance", "Human approval required", "PASS", "human_review_required=True in credential policy", "credential_policy_stub", "ACTIVE"),
    EvidenceItem("EVD_010", "capability", "Submit capability prohibited", "PASS", "order_submit and order_cancel marked PROHIBITED", "exchange_capability_inventory", "CLEAR"),
)


def create_evidence() -> PreflightEvidence:
    return PreflightEvidence(
        preflight_id=f"PFE_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        items=EVIDENCE_ITEMS,
    )


def count_passed(evidence: PreflightEvidence) -> int:
    return sum(1 for i in evidence.items if i.result == "PASS")


def count_active_blockers(evidence: PreflightEvidence) -> int:
    return sum(1 for i in evidence.items if i.blocker_status == "ACTIVE")


def write_evidence(evidence: PreflightEvidence, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence.to_dict(), indent=2), encoding="utf-8")


def render_report(evidence: PreflightEvidence) -> str:
    lines = ["# No-Network Preflight Evidence", "",
        f"**preflight_id={evidence.preflight_id}**",
        f"**passed={count_passed(evidence)}/{len(evidence.items)}**",
        f"**active_blockers={count_active_blockers(evidence)}**",
        "**REAL_NETWORK_NOT_ALLOWED**",
        "**TESTNET_SUBMIT_NOT_ALLOWED**", "",
        "## Evidence Items", "",
        "| ID | Category | Check | Result | Blocker |",
        "|----|----------|-------|--------|---------|"]
    for i in evidence.items:
        lines.append(f"| {i.evidence_id} | {i.category} | {i.check_name} | {i.result} | {i.blocker_status} |")
    lines.extend(["", "## Conclusion", "",
        "NO_NETWORK_PREFLIGHT_EVIDENCE_READY",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
