"""Tests for T17501 — Shadow-to-Testnet Promotion Gate.

Covers:
- Evidence loader: all evidence types loaded
- Decision engine: correct decisions based on evidence
- Denial reasons: blocking failures produce denials
- Approval packet: simulation-only
- Rollback plan: complete steps
- Forbidden decisions never emitted
- Missing evidence blocks promotion
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.promotion_evidence_loader import (
    FORBIDDEN_PROMOTION_MODES,
    REQUIRED_EVIDENCE_TYPES,
    PromotionEvidenceItem,
    load_all_promotion_evidence,
    compute_evidence_hash,
)
from core.promotion_decision_engine import (
    FORBIDDEN_DECISIONS,
    VALID_DECISIONS,
    DenialReason,
    PromotionDecision,
    make_promotion_decision,
    compute_decision_hash,
)
from core.promotion_approval_packet import ApprovalPacket, build_approval_packet, compute_packet_hash
from core.promotion_rollback_plan import RollbackPlan, build_rollback_plan, compute_rollback_hash


# --- Fixtures ---

@pytest.fixture
def all_pass_evidence():
    return [
        {"evidence_type": "shadow_evidence_exists", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
        {"evidence_type": "no_critical_blocker", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
        {"evidence_type": "no_submit_guard_passed", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
        {"evidence_type": "frozen_cleanup_finalized", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
        {"evidence_type": "offline_regression_clean", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
        {"evidence_type": "strategy_registry_exists", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
        {"evidence_type": "testnet_dry_run_no_submit_default", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
    ]


@pytest.fixture
def some_fail_evidence():
    return [
        {"evidence_type": "shadow_evidence_exists", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
        {"evidence_type": "no_critical_blocker", "status": "FAIL", "description": "blocker found", "source": "test", "verified": False, "blocking": True},
        {"evidence_type": "no_submit_guard_passed", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
        {"evidence_type": "frozen_cleanup_finalized", "status": "FAIL", "description": "not finalized", "source": "test", "verified": False, "blocking": True},
        {"evidence_type": "offline_regression_clean", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
        {"evidence_type": "strategy_registry_exists", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
        {"evidence_type": "testnet_dry_run_no_submit_default", "status": "PASS", "description": "ok", "source": "test", "verified": True, "blocking": True},
    ]


@pytest.fixture
def all_fail_evidence():
    return [
        {"evidence_type": t, "status": "FAIL", "description": f"fail_{t}", "source": "test", "verified": False, "blocking": True}
        for t in REQUIRED_EVIDENCE_TYPES
    ]


# --- Evidence Loader Tests ---

class TestEvidenceLoader:
    def test_load_from_cleanup(self):
        from core.promotion_evidence_loader import load_evidence_from_cleanup
        items = load_evidence_from_cleanup({"cleanup_ready_for_human_review": True})
        assert len(items) == 1
        assert items[0].status == "PASS"

    def test_load_from_cleanup_fail(self):
        from core.promotion_evidence_loader import load_evidence_from_cleanup
        items = load_evidence_from_cleanup({"cleanup_ready_for_human_review": False})
        assert items[0].status == "FAIL"

    def test_load_from_shadow(self):
        from core.promotion_evidence_loader import load_evidence_from_shadow
        items = load_evidence_from_shadow({"shadow_evidence_exists": True, "stability_score": 0.8})
        assert len(items) == 2
        assert all(i.status == "PASS" for i in items)

    def test_load_from_shadow_fail(self):
        from core.promotion_evidence_loader import load_evidence_from_shadow
        items = load_evidence_from_shadow({"shadow_evidence_exists": False, "stability_score": 0.2})
        assert all(i.status == "FAIL" for i in items)

    def test_load_all_evidence(self):
        items = load_all_promotion_evidence(
            {"cleanup_ready_for_human_review": True},
            {"shadow_evidence_exists": True, "stability_score": 0.8},
            {"no_submit_guard_passed": True},
            {"offline_regression_clean": True},
            {"strategy_registry_exists": True},
            {"testnet_dry_run_no_submit_default": True},
            release_hold="HOLD",
        )
        assert len(items) == 7

    def test_release_hold_mismatch(self):
        with pytest.raises(ValueError, match="release_hold"):
            load_all_promotion_evidence({}, {}, {}, {}, {}, {}, release_hold="WRONG")


class TestEvidenceTypes:
    def test_required_types_covered(self):
        items = load_all_promotion_evidence(
            {"cleanup_ready_for_human_review": True},
            {"shadow_evidence_exists": True, "stability_score": 0.8},
            {"no_submit_guard_passed": True},
            {"offline_regression_clean": True},
            {"strategy_registry_exists": True},
            {"testnet_dry_run_no_submit_default": True},
        )
        loaded_types = {i.evidence_type for i in items}
        for rt in REQUIRED_EVIDENCE_TYPES:
            assert rt in loaded_types, f"Missing evidence type: {rt}"


class TestEvidenceDeterministic:
    def test_hash_stable(self):
        items = load_all_promotion_evidence(
            {"cleanup_ready_for_human_review": True},
            {"shadow_evidence_exists": True, "stability_score": 0.8},
            {"no_submit_guard_passed": True},
            {"offline_regression_clean": True},
            {"strategy_registry_exists": True},
            {"testnet_dry_run_no_submit_default": True},
        )
        h1 = compute_evidence_hash(items)
        h2 = compute_evidence_hash(items)
        assert h1 == h2


# --- Decision Engine Tests ---

class TestDecisionEngine:
    def test_all_pass_ready(self, all_pass_evidence):
        decision = make_promotion_decision(all_pass_evidence)
        assert decision.decision == "READY_FOR_TESTNET_DRY_RUN_PREP"
        assert decision.all_evidence_passed is True
        assert decision.any_critical_blocker is False

    def test_some_fail_blocked(self, some_fail_evidence):
        decision = make_promotion_decision(some_fail_evidence)
        assert decision.decision == "BLOCKED"
        assert decision.all_evidence_passed is False
        assert decision.any_critical_blocker is True

    def test_all_fail_blocked(self, all_fail_evidence):
        decision = make_promotion_decision(all_fail_evidence)
        assert decision.decision == "BLOCKED"
        assert len(decision.evidence_failed) == len(REQUIRED_EVIDENCE_TYPES)

    def test_valid_decisions_only(self, all_pass_evidence, some_fail_evidence, all_fail_evidence):
        for ev in [all_pass_evidence, some_fail_evidence, all_fail_evidence]:
            d = make_promotion_decision(ev)
            assert d.decision in VALID_DECISIONS

    def test_no_forbidden_decisions(self, all_pass_evidence, some_fail_evidence, all_fail_evidence):
        for ev in [all_pass_evidence, some_fail_evidence, all_fail_evidence]:
            d = make_promotion_decision(ev)
            assert d.decision not in FORBIDDEN_DECISIONS

    def test_release_hold_mismatch(self, all_pass_evidence):
        with pytest.raises(ValueError, match="release_hold"):
            make_promotion_decision(all_pass_evidence, release_hold="WRONG")

    def test_simulation_only(self, all_pass_evidence):
        d = make_promotion_decision(all_pass_evidence)
        assert d.simulation_only is True


class TestMissingEvidenceBlocks:
    def test_missing_shadow_blocks(self):
        evidence = [
            {"evidence_type": "shadow_evidence_exists", "status": "FAIL", "description": "missing", "source": "test", "blocking": True},
        ]
        d = make_promotion_decision(evidence)
        assert d.decision == "BLOCKED"

    def test_missing_guard_blocks(self):
        evidence = [
            {"evidence_type": "no_submit_guard_passed", "status": "FAIL", "description": "failed", "source": "test", "blocking": True},
        ]
        d = make_promotion_decision(evidence)
        assert d.decision == "BLOCKED"

    def test_missing_cleanup_blocks(self):
        evidence = [
            {"evidence_type": "frozen_cleanup_finalized", "status": "FAIL", "description": "not done", "source": "test", "blocking": True},
        ]
        d = make_promotion_decision(evidence)
        assert d.decision == "BLOCKED"


class TestDecisionDeterministic:
    def test_hash_stable(self, all_pass_evidence):
        d = make_promotion_decision(all_pass_evidence)
        h1 = compute_decision_hash(d)
        h2 = compute_decision_hash(d)
        assert h1 == h2


# --- Denial Reason Tests ---

class TestDenialReasons:
    def test_denial_from_failures(self, some_fail_evidence):
        d = make_promotion_decision(some_fail_evidence)
        assert len(d.denial_reasons) > 0

    def test_no_denial_when_all_pass(self, all_pass_evidence):
        d = make_promotion_decision(all_pass_evidence)
        assert len(d.denial_reasons) == 0


# --- Approval Packet Tests ---

class TestApprovalPacket:
    def test_build_packet(self, all_pass_evidence):
        decision = make_promotion_decision(all_pass_evidence)
        packet = build_approval_packet(decision.to_dict(), release_hold="HOLD")
        assert packet.simulation_only is True
        assert packet.total_items > 0

    def test_packet_hash_stable(self, all_pass_evidence):
        decision = make_promotion_decision(all_pass_evidence)
        packet = build_approval_packet(decision.to_dict())
        h1 = compute_packet_hash(packet)
        h2 = compute_packet_hash(packet)
        assert h1 == h2

    def test_release_hold_mismatch(self, all_pass_evidence):
        decision = make_promotion_decision(all_pass_evidence)
        with pytest.raises(ValueError, match="release_hold"):
            build_approval_packet(decision.to_dict(), release_hold="WRONG")


# --- Rollback Plan Tests ---

class TestRollbackPlan:
    def test_build_plan(self):
        plan = build_rollback_plan(release_hold="HOLD")
        assert plan.simulation_only is True
        assert plan.total_steps == 5
        assert len(plan.trigger_conditions) > 0

    def test_plan_hash_stable(self):
        plan = build_rollback_plan()
        h1 = compute_rollback_hash(plan)
        h2 = compute_rollback_hash(plan)
        assert h1 == h2

    def test_release_hold_mismatch(self):
        with pytest.raises(ValueError, match="release_hold"):
            build_rollback_plan(release_hold="WRONG")

    def test_all_steps_simulation_only(self):
        plan = build_rollback_plan()
        for step in plan.steps:
            assert step.simulation_only is True


# --- Forbidden Promotion Modes Tests ---

class TestForbiddenPromotionModes:
    def test_no_forbidden_modes_in_evidence_loader(self):
        items = load_all_promotion_evidence(
            {"cleanup_ready_for_human_review": True},
            {"shadow_evidence_exists": True, "stability_score": 0.8},
            {"no_submit_guard_passed": True},
            {"offline_regression_clean": True},
            {"strategy_registry_exists": True},
            {"testnet_dry_run_no_submit_default": True},
        )
        for item in items:
            assert item.evidence_type not in FORBIDDEN_PROMOTION_MODES

    def test_no_forbidden_decisions_in_engine(self, all_pass_evidence):
        d = make_promotion_decision(all_pass_evidence)
        for fd in FORBIDDEN_DECISIONS:
            assert d.decision != fd
