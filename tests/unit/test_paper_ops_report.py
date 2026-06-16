"""Tests for paper trading ops report generator."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_paper_trading_ops_report.py")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")


class TestOpsReport:
    def test_ops_report_executes(self):
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "PAPER_TRADING_OPS_COMPLETE" in result.stdout

    def test_json_created(self):
        subprocess.run([sys.executable, SCRIPT], capture_output=True, timeout=60)
        path = os.path.join(REPORT_DIR, "paper_trading_ops_report.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "safety_flags" in data
        assert "PAPER_ONLY" in data["safety_flags"]

    def test_markdown_created(self):
        subprocess.run([sys.executable, SCRIPT], capture_output=True, timeout=60)
        path = os.path.join(REPORT_DIR, "paper_trading_ops_report.md")
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "NO_REAL_ORDER" in content
        assert "PAPER_ONLY" in content

    def test_has_dry_run_data(self):
        subprocess.run([sys.executable, SCRIPT], capture_output=True, timeout=60)
        path = os.path.join(REPORT_DIR, "paper_trading_ops_report.json")
        with open(path) as f:
            data = json.load(f)
        assert data["dry_run"] is not None
        assert "total_pnl" in data["dry_run"]

    def test_has_param_sweep_top10(self):
        subprocess.run([sys.executable, SCRIPT], capture_output=True, timeout=60)
        path = os.path.join(REPORT_DIR, "paper_trading_ops_report.json")
        with open(path) as f:
            data = json.load(f)
        assert len(data["parameter_sweep_top10"]) <= 10

    def test_no_real_orders(self):
        subprocess.run([sys.executable, SCRIPT], capture_output=True, timeout=60)
        path = os.path.join(REPORT_DIR, "paper_trading_ops_report.md")
        with open(path) as f:
            content = f.read()
        assert "NO_TESTNET" in content
        assert "NO_LIVE" in content
