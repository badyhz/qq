"""Tests for operator decision pack module."""
from __future__ import annotations

import pytest

from core.paper_trading.candidate_ranker import Priority, RankedCandidate, rank_candidate
from core.paper_trading.operator_decision_pack import (
    generate_decision_pack, generate_decision_markdown, generate_decision_html,
)


def _ranked(**kwargs):
    defaults = dict(
        review_id="test_001", rank=1, priority=Priority.HIGH,
        rank_score=70.0, reason_codes=["rating_a", "good_rr"],
        human_summary="BTCUSDT BUY rated A — HIGH priority",
        symbol="BTCUSDT", strategy_name="macd_rebound", side="BUY",
        entry_price=50000.0, stop_loss=49000.0, take_profit=52000.0,
        score=80.0, rating="A", risk_summary="normal",
        operator_status="PENDING_REVIEW", source_run_id="run_001",
        safety_flags=["NO_REAL_ORDER", "PAPER_ONLY"],
    )
    defaults.update(kwargs)
    return RankedCandidate(**defaults)


class TestDecisionPack:
    def test_empty_queue(self):
        pack = generate_decision_pack([])
        assert pack["total_candidates"] == 0
        assert pack["high_count"] == 0

    def test_single_candidate(self):
        pack = generate_decision_pack([_ranked()])
        assert pack["total_candidates"] == 1
        assert pack["high_count"] == 1

    def test_multiple_ranked(self):
        candidates = [
            _ranked(rank=1, priority=Priority.HIGH),
            _ranked(review_id="r2", rank=2, priority=Priority.MEDIUM),
            _ranked(review_id="r3", rank=3, priority=Priority.LOW),
        ]
        pack = generate_decision_pack(candidates)
        assert pack["total_candidates"] == 3
        assert pack["high_count"] == 1
        assert pack["medium_count"] == 1
        assert pack["low_count"] == 1

    def test_reject_candidate(self):
        pack = generate_decision_pack([_ranked(priority=Priority.REJECT)])
        assert pack["reject_count"] == 1

    def test_safety_flags_present(self):
        pack = generate_decision_pack([_ranked()])
        assert "NO_REAL_ORDER" in pack["safety_flags"]
        assert "HUMAN_REVIEW_REQUIRED" in pack["safety_flags"]

    def test_allowed_actions(self):
        pack = generate_decision_pack([_ranked()])
        assert "WATCHLIST" in pack["allowed_actions"]
        assert "PAPER_APPROVED" in pack["allowed_actions"]


class TestDecisionMarkdown:
    def test_contains_key_info(self):
        md = generate_decision_markdown([_ranked()])
        assert "BTCUSDT" in md
        assert "HIGH" in md
        assert "Safety" in md
        assert "PAPER_APPROVED" in md

    def test_contains_risk(self):
        md = generate_decision_markdown([_ranked(risk_summary="high volatility")])
        assert "high volatility" in md

    def test_empty(self):
        md = generate_decision_markdown([])
        assert "Operator Decision Pack" in md

    def test_no_order_strings(self):
        md = generate_decision_markdown([_ranked()])
        assert "submit_order" not in md.lower()
        assert "place_order" not in md.lower()


class TestDecisionHtml:
    def test_generates_html(self):
        html = generate_decision_html([_ranked()])
        assert "<html" in html
        assert "Operator Decision Pack" in html

    def test_no_external_links(self):
        html = generate_decision_html([_ranked()])
        assert "http://" not in html
        assert "https://" not in html
        assert "<script" not in html.lower()
        assert 'rel="stylesheet"' not in html

    def test_contains_data(self):
        html = generate_decision_html([_ranked()])
        assert "BTCUSDT" in html
        assert "50000" in html

    def test_safety_footer(self):
        html = generate_decision_html([_ranked()])
        assert "NO_REAL_ORDER" in html
        assert "paper-only" in html.lower()

    def test_no_testnet_live_strings(self):
        html = generate_decision_html([_ranked()])
        # Safety flags contain NO_TESTNET/NO_LIVE — these are declarations, not connections
        assert "connect" not in html.lower()
        assert "api.binance" not in html.lower()

    def test_empty(self):
        html = generate_decision_html([])
        assert "<html" in html
        assert "0" in html
