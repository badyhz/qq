"""Tests for daily ops runner."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
SCRIPT = os.path.join(REPO_ROOT, "scripts", "run_paper_daily_ops.py")


class TestDailyOpsRunner:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        import py_compile
        py_compile.compile(SCRIPT, doraise=True)

    def test_runner_executes(self):
        """Daily ops runner should complete (may have individual runner failures)."""
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True,
            timeout=600, cwd=REPO_ROOT,
        )
        # Should produce output (exit code may be 1 due to malformed fixture)
        assert "Paper Trading Daily Ops" in result.stdout
        assert "PAPER_DAILY_OPS" in result.stdout

    def test_runner_produces_json(self):
        json_path = os.path.join(REPO_ROOT, "reports", "paper_trading_daily_ops.json")
        # Run the script first
        subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True,
            timeout=600, cwd=REPO_ROOT,
        )
        assert os.path.isfile(json_path)
        import json
        with open(json_path) as f:
            data = json.load(f)
        assert "passed" in data
        assert "failed" in data
        assert "runners" in data

    def test_runner_produces_md(self):
        md_path = os.path.join(REPO_ROOT, "reports", "paper_trading_daily_ops.md")
        subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True,
            timeout=600, cwd=REPO_ROOT,
        )
        assert os.path.isfile(md_path)
        with open(md_path) as f:
            content = f.read()
        assert "Daily Ops" in content
        assert "paper-only" in content

    def test_runner_generates_index(self):
        index_path = os.path.join(REPO_ROOT, "reports", "paper_trading_index.html")
        subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True,
            timeout=600, cwd=REPO_ROOT,
        )
        assert os.path.isfile(index_path)

    def test_json_has_operator_review(self):
        json_path = os.path.join(REPO_ROOT, "reports", "paper_trading_daily_ops.json")
        subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True,
            timeout=600, cwd=REPO_ROOT,
        )
        import json
        with open(json_path) as f:
            data = json.load(f)
        assert "operator_review" in data
