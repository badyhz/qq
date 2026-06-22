"""Tests for paper position simulator script — structure and safety."""
from __future__ import annotations

import ast
import json
import os
import py_compile
import importlib.util

import pytest

from core.paper_trading.data_source import MarketBar
from core.paper_trading.paper_position_simulator import simulate_existing_positions_update_only

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_paper_position_simulator.py")


def _load_runner_module():
    spec = importlib.util.spec_from_file_location("paper_position_runner", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_position(position_id="P1", status="OPEN", **overrides):
    position = {
        "position_id": position_id,
        "intent_id": f"TI_{position_id}",
        "date": "2026-06-22",
        "source": "trade_intent",
        "strategy_id": "macd_rebound_watch",
        "strategy_type": "macd_rebound_watch",
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "side": "LONG",
        "status": status,
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "rr_ratio": 2.0,
        "position_size_preview": 1.0,
        "max_risk_pct": 0.5,
        "paper_equity_preview": 10000.0,
        "opened_at": "2026-06-22T00:00:00+00:00",
        "opened_bar_time": 1700000000000,
        "closed_at": None,
        "exit_price": None,
        "exit_reason": None,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
        "realized_pnl_pct": 0.0,
        "r_multiple": 0.0,
        "source_trade_intent_status": "SHADOW_READY",
        "risk_gate_status": "PASS",
        "lifecycle_mode": "future_only",
        "last_checked_at": None,
        "last_checked_bar_time": None,
        "safety_flags": ["PAPER_ONLY", "SHADOW_ONLY", "NO_ORDER", "NO_TESTNET", "NO_LIVE"],
        "created_at": "2026-06-22T00:00:00+00:00",
    }
    position.update(overrides)
    return position


def _write_ledger(path, positions):
    path.write_text("".join(json.dumps(p) + "\n" for p in positions))


def _write_positions(path, positions):
    path.write_text(json.dumps({"positions": positions}))


class TestScriptStructure:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_has_input_file_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--input-file" in content

    def test_has_date_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--date" in content

    def test_has_allow_public_http(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-public-http" in content

    def test_has_update_with_klines(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--update-with-klines" in content

    def test_has_update_existing_only(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--update-existing-only" in content

    def test_has_timeout_bars(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--timeout-bars" in content

    def test_output_paths(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "_paper_positions.json" in content
        assert "_paper_positions.md" in content
        assert "_paper_position_ledger.jsonl" in content
        assert "_paper_position_summary.json" in content

    def test_no_allow_send(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-send" not in content

    def test_no_webhook_url(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--webhook-url" not in content

    def test_no_secret_env_reads(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("environ", "getenv"):
                    pytest.fail(f"Forbidden env read: .{node.func.attr}")

    def test_no_websocket_imports(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        forbidden = {"websocket", "aiohttp"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden

    def test_no_account_order_methods(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        forbidden_attrs = {"submit_order", "place_order", "cancel_order",
                           "execute_trade", "close_position", "get_account", "get_balance"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in forbidden_attrs:
                    pytest.fail(f"Forbidden method call: .{node.func.attr}")

    def test_has_main_function(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_safety_flags_present(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SAFETY_FLAGS")
        for flag in ["PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ORDER", "NO_TESTNET", "NO_LIVE"]:
            assert flag in mod.SAFETY_FLAGS

    def test_dry_run_only(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "actually_executed" in content
        assert "dry_run_only" in content

    def test_overlap_guard_in_markdown(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "overlap" in content.lower()

    def test_overlap_guard_in_console(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "overlap" in content.lower()


class TestCrossDayUpdateOnlyLoader:
    def test_previous_day_open_loaded_for_current_day_update_only(self, tmp_path):
        mod = _load_runner_module()
        previous_open = _make_position("P1", date="2026-06-22")
        _write_ledger(tmp_path / "2026-06-22_paper_position_ledger.jsonl", [previous_open])
        _write_positions(tmp_path / "2026-06-23_paper_positions.json", [])

        loaded = mod._load_update_existing_positions(str(tmp_path), "2026-06-23")

        assert [p["position_id"] for p in loaded] == ["P1"]

    def test_current_day_positions_load_without_ledger(self, tmp_path):
        mod = _load_runner_module()
        current_open = _make_position("P2", date="2026-06-23")
        _write_positions(tmp_path / "2026-06-23_paper_positions.json", [current_open])

        loaded = mod._load_update_existing_positions(str(tmp_path), "2026-06-23")

        assert [p["position_id"] for p in loaded] == ["P2"]

    def test_duplicate_position_id_keeps_latest_record(self, tmp_path):
        mod = _load_runner_module()
        old_open = _make_position("P1", last_checked_bar_time=100)
        latest_open = _make_position("P1", last_checked_bar_time=200)
        _write_ledger(tmp_path / "2026-06-21_paper_position_ledger.jsonl", [old_open])
        _write_ledger(tmp_path / "2026-06-22_paper_position_ledger.jsonl", [latest_open])

        loaded = mod._load_update_existing_positions(str(tmp_path), "2026-06-23")

        assert len(loaded) == 1
        assert loaded[0]["position_id"] == "P1"
        assert loaded[0]["last_checked_bar_time"] == 200

    def test_closed_position_is_not_resurrected_by_old_open(self, tmp_path):
        mod = _load_runner_module()
        old_open = _make_position("P1", status="OPEN")
        latest_closed = _make_position(
            "P1",
            status="TAKE_PROFIT_HIT",
            closed_at="2026-06-22T01:00:00+00:00",
            exit_reason="take_profit triggered",
        )
        _write_ledger(tmp_path / "2026-06-21_paper_position_ledger.jsonl", [old_open])
        _write_ledger(tmp_path / "2026-06-22_paper_position_ledger.jsonl", [latest_closed])

        loaded = mod._load_update_existing_positions(str(tmp_path), "2026-06-23")

        assert loaded == []

    def test_cross_day_open_with_ms_timestamp_can_close_on_seconds_bar(self, tmp_path):
        mod = _load_runner_module()
        previous_open = _make_position("P1", opened_bar_time=1700000000000)
        _write_ledger(tmp_path / "2026-06-22_paper_position_ledger.jsonl", [previous_open])

        loaded = mod._load_update_existing_positions(str(tmp_path), "2026-06-23")
        bars = [
            MarketBar(
                timestamp=1700000300,
                open=100.0,
                high=111.0,
                low=99.0,
                close=110.5,
                volume=1000.0,
                symbol="BTCUSDT",
                timeframe="15m",
            )
        ]
        result = simulate_existing_positions_update_only(
            loaded, {"BTCUSDT_15m": bars}, "2026-06-23",
        )

        assert result.positions[0]["status"] == "TAKE_PROFIT_HIT"
        assert result.lifecycle_stats["positions_updated_count"] == 1
        assert result.lifecycle_stats["positions_skipped_no_future_bars"] == 0
