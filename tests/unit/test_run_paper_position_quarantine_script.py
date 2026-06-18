"""Tests for run_paper_position_quarantine.py script."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pytest

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "scripts", "run_paper_position_quarantine.py")


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, SCRIPT_PATH] + args,
        capture_output=True, text=True, timeout=30, **kwargs,
    )


def _make_positions_data(positions: list[dict]) -> dict:
    return {"positions": positions, "date": "2026-06-18"}


def _make_clean_position():
    return {
        "position_id": "PP_clean",
        "intent_id": "TI_clean",
        "symbol": "XRPUSDT",
        "side": "SHORT",
        "status": "OPEN",
        "entry_price": 1.15,
        "stop_loss": 1.18,
        "take_profit": 1.09,
        "lifecycle_mode": "future_only",
        "opened_bar_time": 5000,
        "last_checked_bar_time": 6000,
        "exit_reason": "",
        "realized_pnl": 0.0,
        "r_multiple": 0.0,
        "position_size_preview": 100.0,
    }


def _make_legacy_position():
    return {
        "position_id": "PP_legacy",
        "intent_id": "TI_legacy",
        "symbol": "BTCUSDT",
        "side": "LONG",
        "status": "STOP_LOSS_HIT",
        "entry_price": 60000.0,
        "stop_loss": 59000.0,
        "take_profit": 62000.0,
        "lifecycle_mode": None,
        "opened_bar_time": None,
        "last_checked_bar_time": None,
        "exit_reason": "old_backtest_sl",
        "realized_pnl": -50.0,
        "r_multiple": -1.0,
        "position_size_preview": 0.5,
    }


class TestScriptCompiles:
    def test_compiles(self):
        import py_compile
        py_compile.compile(SCRIPT_PATH, doraise=True)


class TestMissingInput:
    def test_missing_file_exits_1(self):
        r = _run(["--input-file", "/tmp/nonexistent_positions_12345.json"])
        assert r.returncode == 1
        assert "ERROR" in r.stdout


class TestWithInput:
    def test_quarantine_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "positions.json")
            data = _make_positions_data([
                _make_clean_position(),
                _make_legacy_position(),
            ])
            with open(input_path, "w") as f:
                json.dump(data, f)

            r = _run([
                "--input-file", input_path,
                "--output-dir", tmpdir,
                "--date", "2026-06-18",
            ])
            assert r.returncode == 0

            # Check quarantine JSON
            q_path = os.path.join(tmpdir, "2026-06-18_paper_positions_quarantine.json")
            assert os.path.isfile(q_path)
            with open(q_path) as f:
                q_data = json.load(f)
            assert q_data["quarantined_count"] >= 1

            # Check clean summary
            cs_path = os.path.join(tmpdir, "2026-06-18_paper_positions_clean_summary.json")
            assert os.path.isfile(cs_path)

            # Check markdown
            md_path = os.path.join(tmpdir, "2026-06-18_paper_positions_quarantine.md")
            assert os.path.isfile(md_path)
            with open(md_path) as f:
                content = f.read()
            assert "LEGACY" in content

    def test_safety_flags_in_clean_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "positions.json")
            with open(input_path, "w") as f:
                json.dump(_make_positions_data([]), f)

            r = _run(["--input-file", input_path, "--output-dir", tmpdir, "--date", "2026-06-18"])
            assert r.returncode == 0

            cs_path = os.path.join(tmpdir, "2026-06-18_paper_positions_clean_summary.json")
            with open(cs_path) as f:
                cs_data = json.load(f)
            assert "PAPER_ONLY" in cs_data["safety_flags"]
            assert cs_data["dry_run_only"] is True
            assert cs_data["actually_executed"] is False


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
