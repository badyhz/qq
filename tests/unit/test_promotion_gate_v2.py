"""Tests for promotion gate v2 — T8041-T8080.

PASS/PARTIAL/FAIL, hard block, advisory status tests.
"""
from __future__ import annotations

import pytest
from core.promotion_gate_v2 import evaluate_promotion_gate, build_promotion_gate_report


class TestPromotionGateNormal:
    def test_advisory_pass(self):
        d = evaluate_promotion_gate(0.8, 0.9, [])
        assert d.status == "ADVISORY_PASS"
        assert d.advisory_only is True
        assert d.release_hold == "HOLD"

    def test_build_report(self):
        d = evaluate_promotion_gate(0.8, 0.9, [])
        report = build_promotion_gate_report(d, seed=42)
        assert report["verdict"] == "PASS"


class TestPromotionGateEdge:
    def test_low_score_fail(self):
        d = evaluate_promotion_gate(0.1, 0.9, [])
        assert d.status == "ADVISORY_FAIL"

    def test_low_completeness_partial(self):
        d = evaluate_promotion_gate(0.8, 0.5, [])
        assert d.status == "ADVISORY_PARTIAL"


class TestPromotionGateAdversarial:
    def test_hard_blocks_fail(self):
        d = evaluate_promotion_gate(0.8, 0.9, ["BLOCK1"])
        assert d.status == "ADVISORY_FAIL"
        assert "BLOCK1" in d.block_reasons

    def test_never_promotes_to_live(self):
        d = evaluate_promotion_gate(1.0, 1.0, [])
        assert d.advisory_only is True
        assert d.human_review_required is True
        assert d.release_hold == "HOLD"


class TestPromotionGateSafetyBoundary:
    def test_always_advisory(self):
        for score in [0.0, 0.5, 1.0]:
            d = evaluate_promotion_gate(score, 1.0, [])
            assert d.advisory_only is True
            assert d.release_hold == "HOLD"
