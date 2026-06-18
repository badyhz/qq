"""Tests for shadow gate evaluator — no network, no orders."""
from __future__ import annotations

import os
import tempfile

import pytest

from core.paper_trading.shadow_ledger import ShadowLedger, ShadowRecord
from core.paper_trading.shadow_gate_evaluator import evaluate_shadow_gate, ShadowGateResult


def make_record(symbol="BTCUSDT", priority="HIGH", valid_plan=True, outcome="WIN",
                pnl=1000.0, safety_flags=None, timestamp=1000.0):
    """Helper to create a shadow record."""
    if safety_flags is None:
        safety_flags = ["PAPER_ONLY", "NO_REAL_ORDER"]
    return ShadowRecord(
        timestamp=timestamp,
        symbol=symbol,
        timeframe="1h",
        priority=priority,
        signal_type="macd_rebound",
        plan_id=f"plan_{int(timestamp)}",
        valid_plan=valid_plan,
        reject_reason="" if valid_plan else "risk_rejected",
        entry=50000.0,
        stop=49000.0,
        take_profit=52000.0,
        rr=2.0,
        outcome=outcome,
        pnl=pnl,
        expectancy_input=pnl * 0.5,
        data_quality_ok=True,
        safety_flags=safety_flags,
    )


@pytest.fixture
def ledger():
    """Create a temporary ledger."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    yield ShadowLedger(path)
    if os.path.exists(path):
        os.unlink(path)


class TestShadowGateEvaluator:
    def test_pass_case(self, ledger):
        """PASS: 30+ valid plans, good distribution, positive expectancy."""
        for i in range(20):
            ledger.append(make_record(priority="HIGH", outcome="WIN", pnl=1000.0, timestamp=1000 + i))
        for i in range(15):
            ledger.append(make_record(priority="MEDIUM", outcome="WIN", pnl=500.0, timestamp=2000 + i))
        for i in range(5):
            ledger.append(make_record(priority="LOW", outcome="LOSS", pnl=-100.0, timestamp=3000 + i))
        result = evaluate_shadow_gate(ledger)
        assert result.decision == "PASS"
        assert result.valid_plans == 40
        assert result.high_count == 20
        assert result.medium_count == 15

    def test_fail_negative_expectancy(self, ledger):
        """FAIL: negative expectancy."""
        for i in range(20):
            ledger.append(make_record(priority="HIGH", outcome="LOSS", pnl=-1000.0, timestamp=1000 + i))
        for i in range(15):
            ledger.append(make_record(priority="MEDIUM", outcome="LOSS", pnl=-500.0, timestamp=2000 + i))
        result = evaluate_shadow_gate(ledger)
        assert result.decision == "FAIL"
        assert any("expectancy" in r.lower() for r in result.reasons)

    def test_fail_safety_violation(self, ledger):
        """FAIL: safety violation."""
        for i in range(35):
            ledger.append(make_record(priority="HIGH", outcome="WIN", pnl=1000.0,
                                      safety_flags=["PAPER_ONLY"], timestamp=1000 + i))
        result = evaluate_shadow_gate(ledger)
        assert result.decision == "FAIL"
        assert result.safety_violations > 0

    def test_extend_insufficient_samples(self, ledger):
        """EXTEND: insufficient valid plans."""
        for i in range(10):
            ledger.append(make_record(priority="HIGH", outcome="WIN", pnl=1000.0, timestamp=1000 + i))
        result = evaluate_shadow_gate(ledger)
        assert result.decision == "EXTEND"
        assert any("insufficient" in r.lower() for r in result.reasons)

    def test_extend_insufficient_high_medium(self, ledger):
        """EXTEND: insufficient HIGH/MEDIUM (with some HIGH/MEDIUM to avoid LOW domination)."""
        for i in range(3):
            ledger.append(make_record(priority="HIGH", outcome="WIN", pnl=1000.0, timestamp=1000 + i))
        for i in range(5):
            ledger.append(make_record(priority="MEDIUM", outcome="WIN", pnl=500.0, timestamp=2000 + i))
        for i in range(22):
            ledger.append(make_record(priority="LOW", outcome="WIN", pnl=100.0, timestamp=3000 + i))
        result = evaluate_shadow_gate(ledger)
        assert result.decision in ["EXTEND", "FAIL"]
        assert result.high_count < 5 or result.medium_count < 10

    def test_fail_low_dominates(self, ledger):
        """FAIL/EXTEND: LOW > 50%."""
        for i in range(5):
            ledger.append(make_record(priority="HIGH", outcome="WIN", pnl=1000.0, timestamp=1000 + i))
        for i in range(30):
            ledger.append(make_record(priority="LOW", outcome="WIN", pnl=100.0, timestamp=2000 + i))
        result = evaluate_shadow_gate(ledger)
        assert result.decision in ["FAIL", "EXTEND"]
        assert result.low_ratio > 0.5

    def test_fail_low_profit_factor(self, ledger):
        """FAIL: profit factor <= 1.2."""
        for i in range(20):
            ledger.append(make_record(priority="HIGH", outcome="WIN", pnl=100.0, timestamp=1000 + i))
        for i in range(20):
            ledger.append(make_record(priority="MEDIUM", outcome="LOSS", pnl=-90.0, timestamp=2000 + i))
        result = evaluate_shadow_gate(ledger)
        assert result.decision == "FAIL"
        assert result.profit_factor <= 1.2

    def test_fail_high_expectancy_negative(self, ledger):
        """FAIL: HIGH expectancy <= 0."""
        for i in range(20):
            ledger.append(make_record(priority="HIGH", outcome="LOSS", pnl=-1000.0, timestamp=1000 + i))
        for i in range(15):
            ledger.append(make_record(priority="MEDIUM", outcome="WIN", pnl=500.0, timestamp=2000 + i))
        for i in range(5):
            ledger.append(make_record(priority="LOW", outcome="WIN", pnl=100.0, timestamp=3000 + i))
        result = evaluate_shadow_gate(ledger)
        assert result.decision == "FAIL"
        assert result.high_expectancy <= 0

    def test_empty_ledger(self, ledger):
        """FAIL/EXTEND: empty ledger."""
        result = evaluate_shadow_gate(ledger)
        assert result.decision in ["FAIL", "EXTEND"]
        assert result.valid_plans == 0


class TestShadowGateEvaluatorSafety:
    def test_no_network_imports(self):
        import ast
        module_path = os.path.join(os.path.dirname(__file__), "..", "..", "core", "paper_trading", "shadow_gate_evaluator.py")
        with open(module_path) as f:
            tree = ast.parse(f.read())
        forbidden = {"requests", "httpx", "aiohttp", "websocket", "urllib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden
