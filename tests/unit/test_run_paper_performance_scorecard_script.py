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


class TestScriptCompiles:
    def test_compiles(self):
        import py_compile
        py_compile.compile(SCRIPT_PATH, doraise=True)


class TestMissingInput:
    def test_missing_file_exits_1(self):
        r = _run(["--input-file", "/tmp/nonexistent_scorecard_12345.json"])
        assert r.returncode == 1
        assert "ERROR" in r.stdout


class TestWithInput:
    def test_scorecard_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "quarantine.json")
            data = _make_quarantine_data(clean_count=5, excluded_count=2)
            with open(input_path, "w") as f:
                json.dump(data, f)

            r = _run([
                "--input-file", input_path,
                "--output-dir", tmpdir,
                "--date", "2026-06-18",
            ])
            assert r.returncode == 0

            # Check scorecard JSON
            sc_path = os.path.join(tmpdir, "2026-06-18_paper_performance_scorecard.json")
            assert os.path.isfile(sc_path)
            with open(sc_path) as f:
                sc_data = json.load(f)
            assert sc_data["global_metrics"]["clean_positions"] == 5
            assert sc_data["global_metrics"]["excluded_positions"] == 2

            # Check markdown
            md_path = os.path.join(tmpdir, "2026-06-18_paper_performance_scorecard.md")
            assert os.path.isfile(md_path)
            with open(md_path) as f:
                content = f.read()
            assert "INSUFFICIENT_CLOSED_SAMPLE" in content

            # Check CSV
            csv_path = os.path.join(tmpdir, "2026-06-18_strategy_scorecard.csv")
            assert os.path.isfile(csv_path)

    def test_empty_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "quarantine.json")
            with open(input_path, "w") as f:
                json.dump({"positions": [], "date": "2026-06-18"}, f)

            r = _run(["--input-file", input_path, "--output-dir", tmpdir, "--date", "2026-06-18"])
            assert r.returncode == 0

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
            input_path = os.path.join(tmpdir, "quarantine.json")
            with open(input_path, "w") as f:
                json.dump(_make_quarantine_data(), f)

            r = _run(["--input-file", input_path, "--output-dir", tmpdir, "--date", "2026-06-18"])
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
