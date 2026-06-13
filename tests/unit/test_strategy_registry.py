"""Tests for T18501 — Strategy Registry + Promotion Board.

Covers:
- Registry schema validation
- Invalid mode rejection
- Real/live/submit field rejection
- Strategy ID uniqueness
- Missing evidence blocks promotion
- Blocker not cleared blocks promotion
- Promotion board decisions
- Forbidden statuses never appear
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.strategy_registry import (
    FORBIDDEN_MODES,
    FORBIDDEN_PROMOTION_STATUSES,
    VALID_PROMOTION_STATUSES,
    StrategyRecord,
    build_default_registry,
    build_strategy_record,
    check_unique_ids,
    compute_registry_hash,
    validate_strategy_record,
)
from core.strategy_promotion_board import (
    FORBIDDEN_BOARD_DECISIONS,
    VALID_BOARD_DECISIONS,
    PromotionBoardDecision,
    build_board_decision,
    build_promotion_board,
    compute_board_hash,
)


# --- Registry Schema Tests ---

class TestRegistrySchema:
    def test_build_record(self):
        r = build_strategy_record(
            strategy_id="test_v1",
            strategy_name="Test Strategy",
            market="crypto",
            asset_type="spot",
            signal_type="test",
            timeframe="1h",
            data_source="test",
            risk_level="LOW",
        )
        assert r.strategy_id == "test_v1"
        assert r.current_mode == "SHADOW_ONLY"
        assert r.promotion_status == "RESEARCH_ONLY"

    def test_default_registry(self):
        records = build_default_registry()
        assert len(records) == 11

    def test_unique_ids(self):
        records = build_default_registry()
        assert check_unique_ids(records) is True

    def test_all_records_have_required_fields(self):
        records = build_default_registry()
        for r in records:
            assert r.strategy_id
            assert r.strategy_name
            assert r.market
            assert r.asset_type
            assert r.signal_type
            assert r.timeframe
            assert r.data_source
            assert r.risk_level


class TestRegistryValidation:
    def test_valid_record(self):
        record = {
            "strategy_id": "test",
            "current_mode": "SHADOW_ONLY",
            "promotion_status": "RESEARCH_ONLY",
        }
        errors = validate_strategy_record(record)
        assert len(errors) == 0

    def test_missing_id(self):
        record = {"current_mode": "SHADOW_ONLY", "promotion_status": "RESEARCH_ONLY"}
        errors = validate_strategy_record(record)
        assert "missing_strategy_id" in errors

    def test_forbidden_mode_rejected(self):
        for mode in FORBIDDEN_MODES:
            record = {"strategy_id": "test", "current_mode": mode, "promotion_status": "RESEARCH_ONLY"}
            errors = validate_strategy_record(record)
            assert any("forbidden_mode" in e for e in errors)

    def test_forbidden_promotion_status_rejected(self):
        for status in FORBIDDEN_PROMOTION_STATUSES:
            record = {"strategy_id": "test", "current_mode": "SHADOW_ONLY", "promotion_status": status}
            errors = validate_strategy_record(record)
            assert any("forbidden_promotion_status" in e for e in errors)

    def test_valid_promotion_statuses(self):
        for status in VALID_PROMOTION_STATUSES:
            record = {"strategy_id": "test", "current_mode": "SHADOW_ONLY", "promotion_status": status}
            errors = validate_strategy_record(record)
            assert not any("forbidden_promotion_status" in e for e in errors)


class TestRegistryDeterministic:
    def test_hash_stable(self):
        records = build_default_registry()
        h1 = compute_registry_hash(records)
        h2 = compute_registry_hash(records)
        assert h1 == h2


# --- Promotion Board Tests ---

class TestPromotionBoard:
    def test_build_board(self):
        records = build_default_registry()
        strategies = [r.to_dict() for r in records]
        decisions = build_promotion_board(strategies, release_hold="HOLD")
        assert len(decisions) == 11

    def test_valid_decisions_only(self):
        records = build_default_registry()
        strategies = [r.to_dict() for r in records]
        decisions = build_promotion_board(strategies)
        for d in decisions:
            assert d.board_decision in VALID_BOARD_DECISIONS

    def test_no_forbidden_decisions(self):
        records = build_default_registry()
        strategies = [r.to_dict() for r in records]
        decisions = build_promotion_board(strategies)
        for d in decisions:
            assert d.board_decision not in FORBIDDEN_BOARD_DECISIONS

    def test_simulation_only(self):
        records = build_default_registry()
        strategies = [r.to_dict() for r in records]
        decisions = build_promotion_board(strategies)
        for d in decisions:
            assert d.simulation_only is True

    def test_release_hold_mismatch(self):
        with pytest.raises(ValueError, match="release_hold"):
            build_promotion_board([], release_hold="WRONG")


class TestBoardDecisionLogic:
    def test_rejected_stays_rejected(self):
        strategy = {
            "strategy_id": "test",
            "strategy_name": "Test",
            "promotion_status": "REJECTED",
            "blockers": [],
            "test_status": "PASSED",
        }
        d = build_board_decision(strategy)
        assert d.board_decision == "REJECT"

    def test_frozen_stays_frozen(self):
        strategy = {
            "strategy_id": "test",
            "strategy_name": "Test",
            "promotion_status": "FROZEN",
            "blockers": [],
            "test_status": "PASSED",
        }
        d = build_board_decision(strategy)
        assert d.board_decision == "FREEZE"

    def test_blockers_hold(self):
        strategy = {
            "strategy_id": "test",
            "strategy_name": "Test",
            "promotion_status": "SHADOW_CANDIDATE",
            "blockers": ["needs_evidence"],
            "test_status": "PASSED",
        }
        d = build_board_decision(strategy)
        assert d.board_decision == "HOLD"

    def test_shadow_candidate_with_tests_promotes(self):
        strategy = {
            "strategy_id": "test",
            "strategy_name": "Test",
            "promotion_status": "SHADOW_CANDIDATE",
            "blockers": [],
            "test_status": "PASSED",
        }
        d = build_board_decision(strategy)
        assert d.board_decision == "PROMOTE"

    def test_shadow_candidate_without_tests_holds(self):
        strategy = {
            "strategy_id": "test",
            "strategy_name": "Test",
            "promotion_status": "SHADOW_CANDIDATE",
            "blockers": [],
            "test_status": "PENDING",
        }
        d = build_board_decision(strategy)
        assert d.board_decision == "HOLD"


class TestBoardDeterministic:
    def test_hash_stable(self):
        records = build_default_registry()
        strategies = [r.to_dict() for r in records]
        decisions = build_promotion_board(strategies)
        h1 = compute_board_hash(decisions)
        h2 = compute_board_hash(decisions)
        assert h1 == h2
