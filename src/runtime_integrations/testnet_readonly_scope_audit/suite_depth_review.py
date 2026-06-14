"""Suite depth review."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ReviewItem:
    review_id: str
    stage_id: str
    suite_runner: str
    observed_steps: int
    expected_steps: int
    has_previous_suites: bool
    has_safety_regression: bool
    coverage_notes: str
    depth_rating: str  # ACCEPTABLE, SIMPLIFIED_ACCEPTABLE, NEEDS_FOLLOWUP
    required_followup: str
    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id, "stage_id": self.stage_id,
            "suite_runner": self.suite_runner,
            "observed_steps": self.observed_steps, "expected_steps": self.expected_steps,
            "has_previous_suites": self.has_previous_suites,
            "has_safety_regression": self.has_safety_regression,
            "coverage_notes": self.coverage_notes,
            "depth_rating": self.depth_rating,
            "required_followup": self.required_followup,
        }


@dataclass(frozen=True)
class SuiteDepthReview:
    review_id: str
    created_at: str
    items: tuple[ReviewItem, ...]
    def to_dict(self) -> dict:
        return {"review_id": self.review_id, "created_at": self.created_at,
                "items": [i.to_dict() for i in self.items]}


REVIEWS = (
    ReviewItem("SDR_001", "STG_RO_001", "run_testnet_readonly_discovery_suite.py",
        7, 7, True, True,
        "7 steps: discovery_design, credential_policy, capability_inventory, adapter_contract, governance_checklist, dry_run_packet, safety_regression. Chains mock_closeout_suite.",
        "ACCEPTABLE", ""),
    ReviewItem("SDR_002", "STG_RO_002", "run_testnet_readonly_preapproval_suite.py",
        6, 6, True, True,
        "6 steps: approval_packet, preflight_evidence, credential_sop, operator_checklist, manual_review_queue, safety_regression. Chains discovery_suite.",
        "ACCEPTABLE", ""),
    ReviewItem("SDR_003", "STG_RO_003", "run_testnet_readonly_release_gate_suite.py",
        6, 6, True, True,
        "6 steps: release_gate, network_off_execution_packet, credential_air_gap_policy, release_blocker_ledger, operator_signoff_draft, safety_regression. Chains discovery+preapproval.",
        "ACCEPTABLE", ""),
    ReviewItem("SDR_004", "STG_RO_004", "run_testnet_readonly_final_approval_simulator_suite.py",
        4, 4, True, True,
        "4 steps: final_approval_simulator, network_on_blocker_drill, human_signoff_archive, safety_regression. Chains 3 prior suites.",
        "SIMPLIFIED_ACCEPTABLE", "Consider adding more drill scenarios beyond 3 basic ones"),
    ReviewItem("SDR_005", "STG_RO_005", "run_testnet_readonly_dry_execution_rehearsal_suite.py",
        4, 4, True, True,
        "4 steps: dry_execution_rehearsal, endpoint_allowlist_stub, audit_redaction_pack, safety_regression. Chains 4 prior suites.",
        "SIMPLIFIED_ACCEPTABLE", "Integration test covers all 3 modules in 1 file; consider per-module tests"),
    ReviewItem("SDR_006", "STG_RO_006", "run_testnet_readonly_final_governance_freeze_suite.py",
        4, 4, True, True,
        "4 steps: final_governance_freeze, operator_handoff_packet, no_submit_release_archive, safety_regression. Chains 5 prior suites.",
        "SIMPLIFIED_ACCEPTABLE", "Integration test covers all 3 modules in 1 file; consider per-module tests"),
)


def create_review() -> SuiteDepthReview:
    return SuiteDepthReview(
        review_id=f"SDR_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        items=REVIEWS,
    )


def count_by_rating(review: SuiteDepthReview) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in review.items:
        counts[item.depth_rating] = counts.get(item.depth_rating, 0) + 1
    return counts


def write_review(review: SuiteDepthReview, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(review.to_dict(), indent=2), encoding="utf-8")


def render_report(review: SuiteDepthReview) -> str:
    lines = ["# Suite Depth Review", "",
        f"**review_id={review.review_id}**",
        f"**total_reviews={len(review.items)}**", "",
        "## Rating Summary", ""]
    by_rating = count_by_rating(review)
    for rating, count in sorted(by_rating.items()):
        lines.append(f"- {rating}: {count}")
    lines.extend(["", "## Reviews", "",
        "| ID | Stage | Steps | Rating | Followup |",
        "|----|-------|-------|--------|----------|"])
    for item in review.items:
        followup = item.required_followup[:50] + "..." if len(item.required_followup) > 50 else item.required_followup
        lines.append(f"| {item.review_id} | {item.stage_id} | {item.observed_steps}/{item.expected_steps} | {item.depth_rating} | {followup} |")
    lines.extend(["", "## Conclusion", "", "READONLY_SUITE_DEPTH_REVIEW_READY", ""])
    return "\n".join(lines)
