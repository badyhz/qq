"""Tests for run_paper_performance_scorecard.py script."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pytest

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "scripts", "run_paper_performance_scorecard.py")


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, SCRIPT_PATH] + args,
        capture_output=True, text=True, timeout=30, **kwargs,
    )


def _make_quarantine_data(clean_count=1, excluded_count=0):
    positions = []
    for i in range(clean_count):
        positions.append({
            "position_id": f"PP_clean_{i}",
            "intent_id": f"TI_clean_{i}",
            "strategy_id": "weak_short_watch",
            "strategy_type": "weak_short_watch",
            "symbol": "XRPUSDT",
            "side": "SHORT",
            "status": "OPEN",
            "entry_price": 1.15,
            "stop_loss": 1.18,
            "take_profit": 1.09,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "r_multiple": 0.0,
            "lifecycle_mode": "future_only",
            "opened_bar_time": 5000,
            "quarantine_status": "CLEAN",
            "excluded_from_performance_stats": False,
            "quarantine_reasons": [],
        })
    for i in range(excluded_count):
        positions.append({
            "position_id": f"PP_legacy_{i}",
            "strategy_id": "weak_short_watch",
            "strategy_type": "weak_short_watch",
            "symbol": "XRPUSDT",
            "status": "STOP_LOSS_HIT",
            "realized_pnl": -50.0,
            "r_multiple": -1.0,
            "quarantine_status": "LEGACY_PRE_FUTURE_ONLY_FIX",
            "excluded_from_performance_stats": True,
            "quarantine_reasons": ["missing_lifecycle_mode"],
        })
    return {"positions": positions, "date": "2026-06-18"}


def _write_ledger(tmpdir: str, date_str: str, clean_count=1, excluded_count=0):
    """Write a ledger JSONL file with clean and excluded positions."""
    import datetime as _dt
    ledger_path = os.path.join(tmpdir, f"{date_str}_paper_position_ledger.jsonl")
    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    with open(ledger_path, "w") as f:
        for i in range(clean_count):
            rec = {
                "position_id": f"PP_clean_{i}",
                "intent_id": f"TI_clean_{i}",
                "strategy_id": "weak_short_watch",
                "strategy_type": "weak_short_watch",
                "symbol": "XRPUSDT",
                "timeframe": "1h",
                "side": "SHORT",
                "status": "TAKE_PROFIT_HIT",
                "entry_price": 1.15,
                "exit_price": 1.09,
                "stop_loss": 1.18,
                "take_profit": 1.09,
                "realized_pnl": 50.0,
                "unrealized_pnl": 0.0,
                "r_multiple": 2.0,
                "lifecycle_mode": "future_only",
                "opened_bar_time": 5000,
                "closed_at": now_iso,
                "quarantine_status": "CLEAN",
                "source_mode": "real_public_readonly",
                "recorded_at": now_iso,
            }
            f.write(json.dumps(rec) + "\n")
        for i in range(excluded_count):
            rec = {
                "position_id": f"PP_legacy_{i}",
                "strategy_id": "weak_short_watch",
                "strategy_type": "weak_short_watch",
                "symbol": "XRPUSDT",
                "timeframe": "1h",
                "side": "SHORT",
                "status": "STOP_LOSS_HIT",
                "entry_price": 1.0,
                "exit_price": 0.9,
                "stop_loss": 1.05,
                "take_profit": 0.85,
                "realized_pnl": -50.0,
                "r_multiple": -1.0,
                "lifecycle_mode": "future_only",
                "opened_bar_time": 4000,
                "closed_at": now_iso,
                "quarantine_status": "EXCLUDED",
                "source_mode": "real_public_readonly",
                "recorded_at": now_iso,
            }
            f.write(json.dumps(rec) + "\n")
    return ledger_path


class TestScriptCompiles:
    def test_compiles(self):
        import py_compile
        py_compile.compile(SCRIPT_PATH, doraise=True)


class TestMissingInput:
    def test_no_ledger_files_exits_1(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            r = _run(["--output-dir", tmpdir, "--date", "2026-06-18"])
            assert r.returncode == 1
            assert "No positions found" in r.stdout


class TestWithLedger:
    def test_scorecard_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_ledger(tmpdir, "2026-06-18", clean_count=5, excluded_count=2)

            r = _run(["--output-dir", tmpdir, "--date", "2026-06-18"])
            assert r.returncode == 0

            # Check scorecard JSON
            sc_path = os.path.join(tmpdir, "2026-06-18_paper_performance_scorecard.json")
            assert os.path.isfile(sc_path)
            with open(sc_path) as f:
                sc_data = json.load(f)
            assert sc_data["global_metrics"]["closed_positions"] == 5
            assert sc_data["global_metrics"]["excluded_positions"] == 0  # Scorecard only gets eligible
            assert sc_data["cumulative_closed_clean"] == 5

            # Check markdown
            md_path = os.path.join(tmpdir, "2026-06-18_paper_performance_scorecard.md")
            assert os.path.isfile(md_path)
            with open(md_path) as f:
                content = f.read()
            assert "LOW_SAMPLE_SIZE" in content

            # Check CSV
            csv_path = os.path.join(tmpdir, "2026-06-18_strategy_scorecard.csv")
            assert os.path.isfile(csv_path)

    def test_empty_ledger(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = os.path.join(tmpdir, "2026-06-18_paper_position_ledger.jsonl")
            with open(ledger_path, "w") as f:
                pass  # empty file

            r = _run(["--output-dir", tmpdir, "--date", "2026-06-18"])
            assert r.returncode == 1

    def test_no_webhook_url_flag(self):
        """Script must not accept --webhook-url."""
        r = _run(["--help"])
        assert "webhook-url" not in r.stdout.lower() or "webhook" not in r.stdout.lower()

    def test_no_allow_send_flag(self):
        """Script must not accept --allow-send."""
        r = _run(["--help"])
        assert "allow-send" not in r.stdout.lower()

    def test_safety_flags_in_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_ledger(tmpdir, "2026-06-18", clean_count=3, excluded_count=1)

            r = _run(["--output-dir", tmpdir, "--date", "2026-06-18"])
            assert r.returncode == 0

            sc_path = os.path.join(tmpdir, "2026-06-18_paper_performance_scorecard.json")
            with open(sc_path) as f:
                sc_data = json.load(f)
            assert "PAPER_ONLY" in sc_data["safety_flags"]
            assert "STATS_FROM_CLEAN_POSITIONS_ONLY" in sc_data["safety_flags"]


class TestNoForbiddenPatterns:
    def test_no_order_words(self):
        with open(SCRIPT_PATH) as f:
            content = f.read()
        for word in ["submit_order", "place_order", "cancel_order", "execute_trade"]:
            assert word not in content

    def test_no_env_reads(self):
        with open(SCRIPT_PATH) as f:
            content = f.read()
        assert "os.environ" not in content
        assert "os.getenv" not in content

    def test_no_dangerous_imports(self):
        with open(SCRIPT_PATH) as f:
            content = f.read()
        for path in ["order_executor", "account_sync", "websocket"]:
            assert f"import {path}" not in content
            assert f"from {path}" not in content
