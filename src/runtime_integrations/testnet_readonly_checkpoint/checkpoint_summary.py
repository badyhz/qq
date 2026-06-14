"""Checkpoint summary: total overview of T155001-T335000 governance chain."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class StageRecord:
    stage_id: str
    stage_name: str
    milestone: str
    commit: str
    tag: str
    suite_runner: str
    qa_summary: str
    safety_summary: str
    current_status: str
    def to_dict(self) -> dict:
        return {"stage_id": self.stage_id, "stage_name": self.stage_name,
                "milestone": self.milestone, "commit": self.commit, "tag": self.tag,
                "suite_runner": self.suite_runner, "qa_summary": self.qa_summary,
                "safety_summary": self.safety_summary, "current_status": self.current_status}


@dataclass(frozen=True)
class CheckpointSummary:
    checkpoint_id: str
    created_at: str
    phase_range: str
    total_stages: int
    latest_commit: str
    latest_tag: str
    tracked_diff_status: str
    old_untracked_preserved: bool
    real_network_enabled: bool
    real_credentials_enabled: bool
    testnet_submit_allowed: bool
    real_trading_allowed: bool
    stages: tuple[StageRecord, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"checkpoint_id": self.checkpoint_id, "created_at": self.created_at,
                "phase_range": self.phase_range, "total_stages": self.total_stages,
                "latest_commit": self.latest_commit, "latest_tag": self.latest_tag,
                "tracked_diff_status": self.tracked_diff_status,
                "old_untracked_preserved": self.old_untracked_preserved,
                "real_network_enabled": self.real_network_enabled,
                "real_credentials_enabled": self.real_credentials_enabled,
                "testnet_submit_allowed": self.testnet_submit_allowed,
                "real_trading_allowed": self.real_trading_allowed,
                "stages": [s.to_dict() for s in self.stages],
                "final_verdict": self.final_verdict}


STAGES = (
    StageRecord("STG_EXT_001", "external testnet adapter spec", "T155001-T170000",
        "54b73e5", "external-testnet-adapter-spec-complete",
        "run_external_testnet_adapter_spec_suite.py",
        "9/9 passed", "sandbox design safety PASS", "COMPLETE"),
    StageRecord("STG_EXT_002", "external testnet mock transport", "T170001-T185000",
        "712db6e", "external-testnet-mock-transport-complete",
        "run_external_testnet_mock_transport_suite.py",
        "9/9 passed", "mock transport safety PASS", "COMPLETE"),
    StageRecord("STG_EXT_003", "external testnet mock replay", "T185001-T200000",
        "65c5a13", "external-testnet-mock-replay-complete",
        "run_external_testnet_mock_replay_suite.py",
        "9/9 passed", "mock replay safety PASS", "COMPLETE"),
    StageRecord("STG_EXT_004", "external testnet mock review", "T200001-T215000",
        "f95955e", "external-testnet-mock-review-complete",
        "run_external_testnet_mock_review_suite.py",
        "6/6 passed", "mock review safety PASS", "COMPLETE"),
    StageRecord("STG_EXT_005", "external testnet mock closeout", "T215001-T230000",
        "21ce25e", "external-testnet-mock-closeout-complete",
        "run_external_testnet_mock_closeout_suite.py",
        "7/7 passed", "mock closeout safety PASS", "COMPLETE"),
    StageRecord("STG_RO_001", "read-only discovery design", "T230001-T245000",
        "909ed61", "testnet-readonly-discovery-design-complete",
        "run_testnet_readonly_discovery_suite.py",
        "7/7 passed", "discovery safety PASS", "COMPLETE"),
    StageRecord("STG_RO_002", "read-only preapproval", "T245001-T260000",
        "2a4d4c1", "testnet-readonly-preapproval-complete",
        "run_testnet_readonly_preapproval_suite.py",
        "7/7 passed", "preapproval safety PASS", "COMPLETE"),
    StageRecord("STG_RO_003", "read-only release gate", "T260001-T275000",
        "3ec4501", "testnet-readonly-release-gate-complete",
        "run_testnet_readonly_release_gate_suite.py",
        "6/6 passed", "release gate safety PASS", "COMPLETE"),
    StageRecord("STG_RO_004", "final approval simulator", "T275001-T290000",
        "fb778db", "testnet-readonly-final-approval-simulator-complete",
        "run_testnet_readonly_final_approval_simulator_suite.py",
        "7/7 passed (19 blocker drill scenarios)", "final approval safety PASS", "COMPLETE"),
    StageRecord("STG_RO_005", "dry execution rehearsal", "T290001-T305000",
        "2e9a676", "testnet-readonly-dry-execution-rehearsal-complete",
        "run_testnet_readonly_dry_execution_rehearsal_suite.py",
        "8/8 passed (per-module tests split)", "dry execution safety PASS", "COMPLETE"),
    StageRecord("STG_RO_006", "final governance freeze", "T305001-T320000",
        "0f12810", "testnet-readonly-final-governance-freeze-complete",
        "run_testnet_readonly_final_governance_freeze_suite.py",
        "9/9 passed (per-module tests split)", "governance freeze safety PASS", "COMPLETE"),
    StageRecord("STG_RO_007", "scope audit", "T320001-T325000",
        "9803199", "testnet-readonly-scope-audit-complete",
        "run_testnet_readonly_scope_audit_suite.py",
        "12/12 passed (de facto spec registry added)", "scope audit safety PASS", "COMPLETE"),
    StageRecord("STG_RO_008", "PRD compliance correction", "T325001-T335000",
        "2256cfc", "testnet-readonly-prd-compliance-correction-complete",
        "run_testnet_readonly_prd_compliance_correction_suite.py",
        "9/9 passed (blocker drill 19 scenarios, test splits, de facto registry)", "correction safety PASS", "COMPLETE"),
)


def create_summary() -> CheckpointSummary:
    return CheckpointSummary(
        checkpoint_id=f"CHK_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        phase_range="T155001-T335000",
        total_stages=len(STAGES),
        latest_commit="2256cfc",
        latest_tag="testnet-readonly-prd-compliance-correction-complete",
        tracked_diff_status="clean",
        old_untracked_preserved=True,
        real_network_enabled=False,
        real_credentials_enabled=False,
        testnet_submit_allowed=False,
        real_trading_allowed=False,
        stages=STAGES,
        final_verdict="READONLY_CHECKPOINT_SUMMARY_READY|ALL_STAGES_COMPLETE|REAL_NETWORK_NOT_ALLOWED|REAL_TRADING_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_summary(summary: CheckpointSummary, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")


def render_report(summary: CheckpointSummary) -> str:
    lines = ["# Read-Only Checkpoint Summary", "",
        f"**checkpoint_id={summary.checkpoint_id}**",
        f"**phase_range={summary.phase_range}**",
        f"**total_stages={summary.total_stages}**",
        f"**latest_commit={summary.latest_commit}**",
        f"**latest_tag={summary.latest_tag}**", "",
        "## Stage Chain", "",
        "| ID | Stage | Milestone | Commit | Tag | Status |",
        "|----|-------|-----------|--------|-----|--------|"]
    for s in summary.stages:
        lines.append(f"| {s.stage_id} | {s.stage_name} | {s.milestone} | {s.commit} | {s.tag} | {s.current_status} |")
    lines.extend(["", "## Safety Invariants", "",
        f"- real_network_enabled: {summary.real_network_enabled}",
        f"- real_credentials_enabled: {summary.real_credentials_enabled}",
        f"- testnet_submit_allowed: {summary.testnet_submit_allowed}",
        f"- real_trading_allowed: {summary.real_trading_allowed}",
        f"- tracked_diff_status: {summary.tracked_diff_status}",
        f"- old_untracked_preserved: {summary.old_untracked_preserved}", "",
        "## Conclusion", "",
        "READONLY_CHECKPOINT_SUMMARY_READY",
        "ALL_STAGES_COMPLETE",
        "REAL_NETWORK_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
