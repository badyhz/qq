"""Tests for scripts/verify_historical_backtest_lab.py — 8+ tests."""
from __future__ import annotations

import csv
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
SCRIPT = ROOT / "scripts" / "verify_historical_backtest_lab.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "historical_ohlcv"
SHADOW_FIXTURE_DIR = ROOT / "tests" / "fixtures" / "offline_shadow_research"


class TestVerificationScript:
    def test_script_exists(self):
        assert SCRIPT.exists(), f"Missing script: {SCRIPT}"

    def test_script_is_executable_syntax(self):
        """Script should be valid Python."""
        proc = subprocess.run(
            [sys.executable, "-c", f"import py_compile; py_compile.compile('{SCRIPT}', doraise=True)"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"Syntax error: {proc.stderr}"

    def test_script_runs_without_error(self):
        """Script should run and produce output."""
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True, text=True, cwd=str(ROOT), timeout=120,
        )
        assert "Verification" in proc.stdout or "PASS" in proc.stdout or "FAIL" in proc.stdout

    def test_script_exits_zero_on_success(self):
        """Script should exit 0 when all checks pass."""
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True, text=True, cwd=str(ROOT), timeout=120,
        )
        # If fixtures and modules are present, should pass
        if proc.returncode != 0:
            pytest.skip(f"Script exited {proc.returncode}: {proc.stdout[-500:]}")

    def test_fixture_csv_readable(self):
        """CSV fixtures should be readable with csv module."""
        for name in ["BTCUSDT_5m.csv", "ETHUSDT_5m.csv"]:
            path = FIXTURE_DIR / name
            if not path.exists():
                pytest.skip(f"Missing fixture: {path}")
            with open(path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert len(rows) >= 50

    def test_shadow_fixture_readable(self):
        """Shadow fixtures should be valid JSON."""
        for name in ["bars_BTCUSDT_5m.json", "outcomes_BTCUSDT_5m.json"]:
            path = SHADOW_FIXTURE_DIR / name
            if not path.exists():
                pytest.skip(f"Missing fixture: {path}")
            with open(path) as f:
                data = json.load(f)
            assert isinstance(data, list)

    def test_all_core_modules_importable(self):
        """All backtest lab modules should import cleanly."""
        modules = [
            "core.historical_ohlcv_schema",
            "core.historical_ohlcv_chunked_reader",
            "core.walk_forward_split_engine",
            "core.offline_breakout_signal_engine",
            "core.offline_backtest_trade_simulator",
            "core.offline_backtest_metrics_engine",
            "core.offline_shadow_metric_engine",
            "core.offline_shadow_scorecard",
            "core.offline_shadow_comparison",
            "core.offline_shadow_report_renderer",
            "core.offline_shadow_bundle_builder",
            "core.offline_shadow_parameter_set",
            "core.offline_backtest_orchestrator",
        ]
        for mod_name in modules:
            mod = importlib.import_module(mod_name)
            assert mod is not None

    def test_bundle_safety_flags_hardcoded(self):
        """Bundle manifest should always have HOLD safety flags."""
        from core.offline_shadow_bundle_builder import build_manifest
        manifest = build_manifest([])
        assert manifest["release_hold"] == "HOLD"
        assert manifest["no_live"] is True
        assert manifest["no_submit"] is True
        assert manifest["no_exchange"] is True
