"""Tests for T17001 — Frozen Cleanup Governance Finalization.

Covers:
- Final inventory: archive/retain/review/reject classification
- Decision matrix: safety flags, forbidden decisions
- Dry-run executor: no real operations, precondition checks
- Evidence recorder: simulation-only records
- Report generator: summary correctness
- Handoff pack: artifact completeness
- Frozen file protection: no modification allowed
- Missing approval rejection
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_cleanup_final_inventory import (
    FORBIDDEN_CLEANUP_ACTIONS,
    VALID_CLEANUP_CLASSIFICATIONS,
    FrozenCleanupInventoryItem,
    build_final_inventory,
    build_inventory_item_from_backlog,
    build_inventory_item_from_external,
    build_inventory_item_from_untracked,
    compute_inventory_hash,
)
from core.frozen_cleanup_decision_matrix import (
    FORBIDDEN_DECISIONS,
    VALID_DECISIONS,
    CleanupDecision,
    build_decision,
    build_decision_matrix,
    compute_decision_hash,
)
from core.frozen_cleanup_dry_run_executor import (
    FORBIDDEN_OUTCOMES,
    CleanupDryRunResult,
    execute_cleanup_dry_run,
    execute_dry_run,
    compute_dry_run_hash,
)
from core.frozen_cleanup_evidence_recorder import (
    FORBIDDEN_EVIDENCE_TYPES,
    CleanupEvidenceRecord,
    build_all_evidence,
    build_evidence_from_decisions,
    build_evidence_from_dry_run,
    build_evidence_from_inventory,
    compute_evidence_hash,
)
from core.frozen_cleanup_report import CleanupReportSummary, build_cleanup_report, compute_report_hash
from core.frozen_cleanup_handoff_pack import CleanupHandoffPack, build_handoff_pack, compute_handoff_hash


# --- Fixtures ---

@pytest.fixture
def sample_backlog_records():
    return [
        {
            "file_path": "core/live_runner.py",
            "risk_class": "HIGH",
            "category": "LIVE_RUNNER",
            "required_evidence": ("dry_run_log", "risk_review"),
            "unlock_recommendation": "HOLD",
        },
        {
            "file_path": "scripts/run_daily_shadow_scan_pipeline.py",
            "risk_class": "MEDIUM",
            "category": "OPERATIONAL_SHADOW",
            "required_evidence": ("dry_run_log",),
            "unlock_recommendation": "HOLD",
        },
    ]


@pytest.fixture
def sample_untracked_paths():
    return [
        "scripts/run_shadow_universe_collector.py",
        "docs/octopusycc_mouse_trade_plan_2026-05-23_2026-05-30.md",
    ]


@pytest.fixture
def sample_external_paths():
    return [
        "research/some_analysis.md",
    ]


@pytest.fixture
def sample_inventory_items(sample_backlog_records, sample_untracked_paths, sample_external_paths):
    return build_final_inventory(
        sample_backlog_records,
        sample_untracked_paths,
        sample_external_paths,
        release_hold="HOLD",
    )


@pytest.fixture
def sample_decision_items(sample_inventory_items):
    return build_decision_matrix(
        [item.to_dict() for item in sample_inventory_items],
        release_hold="HOLD",
    )


@pytest.fixture
def sample_dry_run_items(sample_decision_items):
    return execute_cleanup_dry_run(
        [item.to_dict() for item in sample_decision_items],
        release_hold="HOLD",
    )


# --- Final Inventory Tests ---

class TestFinalInventory:
    def test_build_inventory_from_backlog(self, sample_backlog_records):
        items = build_final_inventory(sample_backlog_records, [], [], release_hold="HOLD")
        assert len(items) == 2
        assert items[0].path == "core/live_runner.py"
        assert items[0].is_tracked_in_backlog is True
        assert items[0].is_untracked is False

    def test_build_inventory_from_untracked(self, sample_untracked_paths):
        items = build_final_inventory([], sample_untracked_paths, [], release_hold="HOLD")
        assert len(items) == 2
        assert items[0].is_untracked is True
        assert items[0].is_tracked_in_backlog is False

    def test_build_inventory_from_external(self, sample_external_paths):
        items = build_final_inventory([], [], sample_external_paths, release_hold="HOLD")
        assert len(items) == 1
        assert items[0].is_external is True

    def test_combined_inventory(self, sample_inventory_items):
        assert len(sample_inventory_items) == 5

    def test_deduplication(self, sample_backlog_records):
        duped = sample_backlog_records + [{"file_path": "core/live_runner.py", "risk_class": "HIGH", "category": "LIVE_RUNNER"}]
        items = build_final_inventory(duped, [], [], release_hold="HOLD")
        paths = [i.path for i in items]
        assert paths.count("core/live_runner.py") == 1

    def test_release_hold_mismatch(self, sample_backlog_records):
        with pytest.raises(ValueError, match="release_hold"):
            build_final_inventory(sample_backlog_records, [], [], release_hold="WRONG")


class TestInventorySafetyFlags:
    def test_simulation_only(self, sample_inventory_items):
        for item in sample_inventory_items:
            assert item.simulation_only is True

    def test_no_touch(self, sample_inventory_items):
        for item in sample_inventory_items:
            assert item.no_touch_required is True

    def test_human_approval_required(self, sample_inventory_items):
        for item in sample_inventory_items:
            assert item.human_approval_required is True

    def test_would_flags_false(self, sample_inventory_items):
        for item in sample_inventory_items:
            assert item.would_copy is False
            assert item.would_move is False
            assert item.would_delete is False
            assert item.would_modify is False


class TestInventoryClassification:
    def test_high_risk_retain(self, sample_inventory_items):
        high = [i for i in sample_inventory_items if i.risk_class == "HIGH"]
        for item in high:
            assert item.cleanup_classification in ("RETAIN", "REVIEW")

    def test_operational_shadow_retain(self, sample_inventory_items):
        shadow = [i for i in sample_inventory_items if i.category == "OPERATIONAL_SHADOW"]
        for item in shadow:
            assert item.cleanup_classification == "RETAIN"

    def test_untracked_review(self, sample_inventory_items):
        untracked = [i for i in sample_inventory_items if i.is_untracked]
        for item in untracked:
            assert item.cleanup_classification == "REVIEW"

    def test_external_retain(self, sample_inventory_items):
        external = [i for i in sample_inventory_items if i.is_external]
        for item in external:
            assert item.cleanup_classification in ("RETAIN", "REVIEW")

    def test_valid_classifications_only(self, sample_inventory_items):
        for item in sample_inventory_items:
            assert item.cleanup_classification in VALID_CLEANUP_CLASSIFICATIONS


class TestInventoryDeterministic:
    def test_hash_stable(self, sample_inventory_items):
        h1 = compute_inventory_hash(sample_inventory_items)
        h2 = compute_inventory_hash(sample_inventory_items)
        assert h1 == h2

    def test_to_dict_roundtrip(self, sample_inventory_items):
        for item in sample_inventory_items:
            d = item.to_dict()
            assert isinstance(d, dict)
            assert d["path"] == item.path


# --- Decision Matrix Tests ---

class TestDecisionMatrix:
    def test_build_decisions(self, sample_decision_items, sample_inventory_items):
        assert len(sample_decision_items) == len(sample_inventory_items)

    def test_valid_decisions_only(self, sample_decision_items):
        for item in sample_decision_items:
            assert item.decision in VALID_DECISIONS

    def test_no_forbidden_decisions(self, sample_decision_items):
        for item in sample_decision_items:
            assert item.decision not in FORBIDDEN_DECISIONS

    def test_release_hold_mismatch(self, sample_inventory_items):
        with pytest.raises(ValueError, match="release_hold"):
            build_decision_matrix(
                [i.to_dict() for i in sample_inventory_items],
                release_hold="WRONG",
            )


class TestDecisionSafetyFlags:
    def test_simulation_only(self, sample_decision_items):
        for item in sample_decision_items:
            assert item.simulation_only is True

    def test_no_touch(self, sample_decision_items):
        for item in sample_decision_items:
            assert item.no_touch_required is True

    def test_advisory_only(self, sample_decision_items):
        for item in sample_decision_items:
            assert item.advisory_only is True

    def test_would_flags_false(self, sample_decision_items):
        for item in sample_decision_items:
            assert item.would_copy is False
            assert item.would_move is False
            assert item.would_delete is False
            assert item.would_modify is False


class TestDecisionLogic:
    def test_high_risk_no_approval_retain(self):
        item = {
            "path": "test.py",
            "cleanup_classification": "RETAIN",
            "has_required_evidence": False,
            "has_approval": False,
            "risk_class": "HIGH",
        }
        decision = build_decision(item)
        assert decision.decision == "RETAIN_FROZEN"

    def test_no_approval_retain(self):
        item = {
            "path": "test.py",
            "cleanup_classification": "RETAIN",
            "has_required_evidence": True,
            "has_approval": False,
            "risk_class": "MEDIUM",
        }
        decision = build_decision(item)
        assert decision.decision == "RETAIN_FROZEN"

    def test_no_evidence_retain(self):
        item = {
            "path": "test.py",
            "cleanup_classification": "ARCHIVE",
            "has_required_evidence": False,
            "has_approval": True,
            "risk_class": "LOW",
        }
        decision = build_decision(item)
        assert decision.decision == "RETAIN_FROZEN"

    def test_reject_classification(self):
        item = {
            "path": "test.py",
            "cleanup_classification": "REJECT",
            "has_required_evidence": True,
            "has_approval": True,
            "risk_class": "LOW",
        }
        decision = build_decision(item)
        assert decision.decision == "REJECT_FROM_CLEANUP"

    def test_archive_proposed(self):
        item = {
            "path": "test.py",
            "cleanup_classification": "ARCHIVE",
            "has_required_evidence": True,
            "has_approval": True,
            "risk_class": "LOW",
        }
        decision = build_decision(item)
        assert decision.decision == "ARCHIVE_PROPOSED"


class TestDecisionDeterministic:
    def test_hash_stable(self, sample_decision_items):
        h1 = compute_decision_hash(sample_decision_items)
        h2 = compute_decision_hash(sample_decision_items)
        assert h1 == h2


# --- Dry-Run Executor Tests ---

class TestDryRunExecutor:
    def test_execute_dry_run(self, sample_dry_run_items, sample_decision_items):
        assert len(sample_dry_run_items) == len(sample_decision_items)

    def test_no_real_operations(self, sample_dry_run_items):
        for item in sample_dry_run_items:
            assert item.would_copy is False
            assert item.would_move is False
            assert item.would_delete is False
            assert item.would_modify is False
            assert item.no_action_performed is True
            assert item.simulation_only is True

    def test_no_forbidden_outcomes(self, sample_dry_run_items):
        for item in sample_dry_run_items:
            assert item.simulated_outcome not in FORBIDDEN_OUTCOMES

    def test_release_hold_mismatch(self, sample_decision_items):
        with pytest.raises(ValueError, match="release_hold"):
            execute_cleanup_dry_run(
                [i.to_dict() for i in sample_decision_items],
                release_hold="WRONG",
            )

    def test_satisfied_item_simulation(self):
        item = {
            "path": "test.py",
            "decision": "RETAIN_FROZEN",
            "preconditions_met": True,
            "evidence_sufficient": True,
            "approval_obtained": True,
            "blocker_cleared": True,
        }
        result = execute_dry_run(item)
        assert result.simulated_outcome == "SIMULATED_RETAIN"
        assert result.preconditions_satisfied is True
        assert result.blocked_reason == ""

    def test_unsatisfied_item_blocked(self):
        item = {
            "path": "test.py",
            "decision": "ARCHIVE_PROPOSED",
            "preconditions_met": False,
            "evidence_sufficient": False,
            "approval_obtained": False,
            "blocker_cleared": False,
        }
        result = execute_dry_run(item)
        assert result.simulated_outcome == "BLOCKED_NO_ACTION"
        assert result.preconditions_satisfied is False
        assert "preconditions_not_met" in result.blocked_reason


class TestDryRunDeterministic:
    def test_hash_stable(self, sample_dry_run_items):
        h1 = compute_dry_run_hash(sample_dry_run_items)
        h2 = compute_dry_run_hash(sample_dry_run_items)
        assert h1 == h2


# --- Evidence Recorder Tests ---

class TestEvidenceRecorder:
    def test_build_from_inventory(self, sample_inventory_items):
        records = build_evidence_from_inventory([i.to_dict() for i in sample_inventory_items])
        assert len(records) == len(sample_inventory_items)
        for r in records:
            assert r.evidence_type == "INVENTORY_COMPLETE"

    def test_build_from_decisions(self, sample_decision_items):
        records = build_evidence_from_decisions([i.to_dict() for i in sample_decision_items])
        assert len(records) == len(sample_decision_items)
        for r in records:
            assert r.evidence_type == "DECISION_MATRIX_GENERATED"

    def test_build_from_dry_run(self, sample_dry_run_items):
        records = build_evidence_from_dry_run([i.to_dict() for i in sample_dry_run_items])
        assert len(records) == len(sample_dry_run_items)
        for r in records:
            assert r.evidence_type == "DRY_RUN_EXECUTED"

    def test_build_all_evidence(self, sample_inventory_items, sample_decision_items, sample_dry_run_items):
        records = build_all_evidence(
            [i.to_dict() for i in sample_inventory_items],
            [i.to_dict() for i in sample_decision_items],
            [i.to_dict() for i in sample_dry_run_items],
            release_hold="HOLD",
        )
        assert len(records) == len(sample_inventory_items) + len(sample_decision_items) + len(sample_dry_run_items)

    def test_no_forbidden_evidence_types(self, sample_inventory_items, sample_decision_items, sample_dry_run_items):
        records = build_all_evidence(
            [i.to_dict() for i in sample_inventory_items],
            [i.to_dict() for i in sample_decision_items],
            [i.to_dict() for i in sample_dry_run_items],
        )
        for r in records:
            assert r.evidence_type not in FORBIDDEN_EVIDENCE_TYPES

    def test_simulation_only(self, sample_inventory_items):
        records = build_evidence_from_inventory([i.to_dict() for i in sample_inventory_items])
        for r in records:
            assert r.simulation_only is True
            assert r.no_action_performed is True
            assert r.advisory_only is True

    def test_release_hold_mismatch(self, sample_inventory_items):
        with pytest.raises(ValueError, match="release_hold"):
            build_all_evidence(
                [i.to_dict() for i in sample_inventory_items], [], [],
                release_hold="WRONG",
            )


class TestEvidenceDeterministic:
    def test_hash_stable(self, sample_inventory_items):
        records = build_evidence_from_inventory([i.to_dict() for i in sample_inventory_items])
        h1 = compute_evidence_hash(records)
        h2 = compute_evidence_hash(records)
        assert h1 == h2


# --- Report Tests ---

class TestCleanupReport:
    def test_build_report(self, sample_inventory_items, sample_decision_items, sample_dry_run_items):
        evidence = build_all_evidence(
            [i.to_dict() for i in sample_inventory_items],
            [i.to_dict() for i in sample_decision_items],
            [i.to_dict() for i in sample_dry_run_items],
        )
        report = build_cleanup_report(
            [i.to_dict() for i in sample_inventory_items],
            [i.to_dict() for i in sample_decision_items],
            [i.to_dict() for i in sample_dry_run_items],
            [e.to_dict() for e in evidence],
            release_hold="HOLD",
        )
        assert report.total_files_inventoried == 5
        assert report.all_simulation_only is True
        assert report.all_no_action_performed is True
        assert report.all_human_approval_required is True
        assert report.cleanup_ready_for_human_review is True

    def test_report_hash_stable(self, sample_inventory_items, sample_decision_items, sample_dry_run_items):
        evidence = build_all_evidence(
            [i.to_dict() for i in sample_inventory_items],
            [i.to_dict() for i in sample_decision_items],
            [i.to_dict() for i in sample_dry_run_items],
        )
        report = build_cleanup_report(
            [i.to_dict() for i in sample_inventory_items],
            [i.to_dict() for i in sample_decision_items],
            [i.to_dict() for i in sample_dry_run_items],
            [e.to_dict() for e in evidence],
        )
        h1 = compute_report_hash(report)
        h2 = compute_report_hash(report)
        assert h1 == h2

    def test_release_hold_mismatch(self, sample_inventory_items):
        with pytest.raises(ValueError, match="release_hold"):
            build_cleanup_report([], [], [], [], release_hold="WRONG")


# --- Handoff Pack Tests ---

class TestHandoffPack:
    def test_build_handoff_pack(self):
        pack = build_handoff_pack(
            "reports/inventory.json",
            "reports/decision_matrix.json",
            "reports/dry_run.json",
            "reports/evidence.json",
            "reports/final_report.json",
            release_hold="HOLD",
        )
        assert pack.total_artifacts == 5
        assert pack.all_simulation_only is True
        assert pack.all_human_review_required is True
        assert len(pack.next_steps) > 0

    def test_handoff_hash_stable(self):
        pack = build_handoff_pack(
            "reports/inventory.json",
            "reports/decision_matrix.json",
            "reports/dry_run.json",
            "reports/evidence.json",
            "reports/final_report.json",
        )
        h1 = compute_handoff_hash(pack)
        h2 = compute_handoff_hash(pack)
        assert h1 == h2

    def test_release_hold_mismatch(self):
        with pytest.raises(ValueError, match="release_hold"):
            build_handoff_pack("a", "b", "c", "d", "e", release_hold="WRONG")


# --- Frozen File Protection Tests ---

class TestFrozenFileProtection:
    def test_inventory_no_modify(self, sample_inventory_items):
        for item in sample_inventory_items:
            assert item.would_modify is False

    def test_decision_no_modify(self, sample_decision_items):
        for item in sample_decision_items:
            assert item.would_modify is False

    def test_dry_run_no_modify(self, sample_dry_run_items):
        for item in sample_dry_run_items:
            assert item.would_modify is False

    def test_inventory_no_delete(self, sample_inventory_items):
        for item in sample_inventory_items:
            assert item.would_delete is False

    def test_decision_no_delete(self, sample_decision_items):
        for item in sample_decision_items:
            assert item.would_delete is False


# --- Missing Approval Rejection Tests ---

class TestMissingApprovalRejection:
    def test_no_approval_retain(self):
        item = {
            "path": "test.py",
            "cleanup_classification": "ARCHIVE",
            "has_required_evidence": True,
            "has_approval": False,
            "risk_class": "LOW",
        }
        decision = build_decision(item)
        assert decision.decision == "RETAIN_FROZEN"
        assert "no_approval" in decision.decision_reason

    def test_no_evidence_retain(self):
        item = {
            "path": "test.py",
            "cleanup_classification": "ARCHIVE",
            "has_required_evidence": False,
            "has_approval": True,
            "risk_class": "LOW",
        }
        decision = build_decision(item)
        assert decision.decision == "RETAIN_FROZEN"
        assert "evidence" in decision.decision_reason

    def test_unsatisfied_dry_run_blocked(self):
        item = {
            "path": "test.py",
            "decision": "ARCHIVE_PROPOSED",
            "preconditions_met": False,
            "evidence_sufficient": False,
            "approval_obtained": False,
            "blocker_cleared": False,
        }
        result = execute_dry_run(item)
        assert result.simulated_outcome == "BLOCKED_NO_ACTION"
        assert result.no_action_performed is True
