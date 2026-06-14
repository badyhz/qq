"""Manual review queue."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ReviewItem:
    review_id: str
    review_type: str
    artifact_reference: str
    required_reviewer: str
    status: str  # PENDING_HUMAN_REVIEW, APPROVED, REJECTED
    blocker_count: int
    required_evidence: str
    final_decision: str
    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id, "review_type": self.review_type,
            "artifact_reference": self.artifact_reference,
            "required_reviewer": self.required_reviewer,
            "status": self.status, "blocker_count": self.blocker_count,
            "required_evidence": self.required_evidence,
            "final_decision": self.final_decision,
        }


@dataclass(frozen=True)
class ManualReviewQueue:
    queue_id: str
    created_at: str
    items: tuple[ReviewItem, ...]
    def to_dict(self) -> dict:
        return {"queue_id": self.queue_id, "created_at": self.created_at,
                "items": [i.to_dict() for i in self.items]}


REVIEW_ITEMS = (
    ReviewItem("RVW_001", "CREDENTIAL_POLICY_REVIEW", "credential_policy_stub.json", "security_team", "PENDING_HUMAN_REVIEW", 2, "Credential audit report", "DO_NOT_ENABLE_REAL_NETWORK"),
    ReviewItem("RVW_002", "EXCHANGE_PERMISSION_REVIEW", "exchange_capability_inventory.json", "compliance_team", "PENDING_HUMAN_REVIEW", 1, "Permission audit report", "DO_NOT_ENABLE_REAL_NETWORK"),
    ReviewItem("RVW_003", "READ_ONLY_DISCOVERY_REVIEW", "discovery_design.json", "engineering", "PENDING_HUMAN_REVIEW", 1, "Discovery design approval", "DO_NOT_ENABLE_REAL_NETWORK"),
    ReviewItem("RVW_004", "NO_NETWORK_PREFLIGHT_REVIEW", "no_network_preflight_evidence.json", "engineering", "PENDING_HUMAN_REVIEW", 0, "Preflight evidence review", "DO_NOT_ENABLE_REAL_NETWORK"),
    ReviewItem("RVW_005", "GOVERNANCE_REVIEW", "discovery_governance_checklist.json", "operator", "PENDING_HUMAN_REVIEW", 3, "Governance checklist sign-off", "DO_NOT_UNLOCK_SUBMIT"),
    ReviewItem("RVW_006", "OPERATOR_ACK_REVIEW", "operator_checklist.json", "operator", "PENDING_HUMAN_REVIEW", 2, "Operator acknowledgement", "DO_NOT_UNLOCK_SUBMIT"),
)


def create_queue() -> ManualReviewQueue:
    return ManualReviewQueue(
        queue_id=f"MRQ_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        items=REVIEW_ITEMS,
    )


def count_pending(queue: ManualReviewQueue) -> int:
    return sum(1 for i in queue.items if i.status == "PENDING_HUMAN_REVIEW")


def write_queue(queue: ManualReviewQueue, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(queue.to_dict(), indent=2), encoding="utf-8")


def render_report(queue: ManualReviewQueue) -> str:
    lines = ["# Manual Review Queue", "",
        f"**queue_id={queue.queue_id}**",
        f"**pending={count_pending(queue)}**",
        "**REAL_NETWORK_NOT_ALLOWED**",
        "**TESTNET_SUBMIT_NOT_ALLOWED**", "",
        "## Review Items", "",
        "| ID | Type | Reviewer | Status | Blockers | Decision |",
        "|----|------|----------|--------|----------|----------|"]
    for i in queue.items:
        lines.append(f"| {i.review_id} | {i.review_type} | {i.required_reviewer} | {i.status} | {i.blocker_count} | {i.final_decision} |")
    lines.extend(["", "## Conclusion", "",
        "READONLY_DISCOVERY_MANUAL_REVIEW_QUEUE_READY",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
