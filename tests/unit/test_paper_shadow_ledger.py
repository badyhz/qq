"""Tests for shadow ledger — no network, no orders."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from core.paper_trading.shadow_ledger import ShadowLedger, ShadowRecord


@pytest.fixture
def ledger_path():
    """Create a temporary ledger path."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sample_record():
    """Create a sample shadow record."""
    return ShadowRecord(
        timestamp=1000.0,
        symbol="BTCUSDT",
        timeframe="1h",
        priority="HIGH",
        signal_type="macd_rebound",
        plan_id="plan_001",
        valid_plan=True,
        reject_reason="",
        entry=50000.0,
        stop=49000.0,
        take_profit=52000.0,
        rr=2.0,
        outcome="WIN",
        pnl=2000.0,
        expectancy_input=500.0,
        data_quality_ok=True,
        safety_flags=["PAPER_ONLY", "NO_REAL_ORDER"],
    )


@pytest.fixture
def loss_record():
    """Create a sample loss record."""
    return ShadowRecord(
        timestamp=2000.0,
        symbol="ETHUSDT",
        timeframe="1h",
        priority="MEDIUM",
        signal_type="macd_rebound",
        plan_id="plan_002",
        valid_plan=True,
        reject_reason="",
        entry=3000.0,
        stop=2900.0,
        take_profit=3200.0,
        rr=2.0,
        outcome="LOSS",
        pnl=-1000.0,
        expectancy_input=-200.0,
        data_quality_ok=True,
        safety_flags=["PAPER_ONLY", "NO_REAL_ORDER"],
    )


class TestShadowRecord:
    def test_create_record(self, sample_record):
        assert sample_record.symbol == "BTCUSDT"
        assert sample_record.priority == "HIGH"
        assert sample_record.valid_plan is True
        assert sample_record.outcome == "WIN"

    def test_record_is_readonly(self, sample_record):
        with pytest.raises(AttributeError):
            sample_record.symbol = "ETHUSDT"


class TestShadowLedger:
    def test_append_and_read(self, ledger_path, sample_record):
        ledger = ShadowLedger(ledger_path)
        ledger.append(sample_record)
        records = ledger.read_all()
        assert len(records) == 1
        assert records[0].symbol == "BTCUSDT"

    def test_append_multiple(self, ledger_path, sample_record, loss_record):
        ledger = ShadowLedger(ledger_path)
        ledger.append(sample_record)
        ledger.append(loss_record)
        records = ledger.read_all()
        assert len(records) == 2

    def test_read_empty(self, ledger_path):
        ledger = ShadowLedger(ledger_path)
        records = ledger.read_all()
        assert records == []

    def test_summary_empty(self, ledger_path):
        ledger = ShadowLedger(ledger_path)
        summary = ledger.summary()
        assert summary["total_records"] == 0
        assert summary["valid_plans"] == 0

    def test_summary_with_records(self, ledger_path, sample_record, loss_record):
        ledger = ShadowLedger(ledger_path)
        ledger.append(sample_record)
        ledger.append(loss_record)
        summary = ledger.summary()
        assert summary["total_records"] == 2
        assert summary["valid_plans"] == 2
        assert summary["high_count"] == 1
        assert summary["medium_count"] == 1
        assert summary["total_pnl"] == 1000.0
        assert summary["win_rate"] == 0.5

    def test_path_property(self, ledger_path):
        ledger = ShadowLedger(ledger_path)
        assert ledger.path == ledger_path


class TestShadowLedgerSafety:
    def test_no_network_imports(self):
        import ast
        module_path = os.path.join(os.path.dirname(__file__), "..", "..", "core", "paper_trading", "shadow_ledger.py")
        with open(module_path) as f:
            tree = ast.parse(f.read())
        forbidden = {"requests", "httpx", "aiohttp", "websocket", "urllib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden

    def test_no_account_methods(self):
        ledger = ShadowLedger("/tmp/test.jsonl")
        assert not hasattr(ledger, "submit_order")
        assert not hasattr(ledger, "place_order")
        assert not hasattr(ledger, "cancel_order")
        assert not hasattr(ledger, "get_account")
