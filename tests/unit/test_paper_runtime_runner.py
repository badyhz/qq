"""Tests for paper runtime CLI runner."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_paper_runtime.py")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
CONFIG_SAMPLE = os.path.join(os.path.dirname(__file__), "..", "fixtures", "paper_trading", "runtime_config_sample.json")


class TestRuntimeRunner:
    def test_default_run(self):
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "PAPER_RUNTIME_COMPLETE" in result.stdout

    def test_json_created(self):
        subprocess.run([sys.executable, SCRIPT], capture_output=True, timeout=120)
        path = os.path.join(REPORT_DIR, "paper_trading_runtime_result.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "safety_flags" in data
        assert "PAPER_ONLY" in data["safety_flags"]

    def test_markdown_created(self):
        subprocess.run([sys.executable, SCRIPT], capture_output=True, timeout=120)
        path = os.path.join(REPORT_DIR, "paper_trading_runtime_report.md")
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "NO_REAL_ORDER" in content
        assert "PAPER_ONLY" in content

    def test_with_config(self):
        result = subprocess.run(
            [sys.executable, SCRIPT, "--config", CONFIG_SAMPLE],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0
        assert "PAPER_RUNTIME_COMPLETE" in result.stdout

    def test_json_has_score(self):
        subprocess.run([sys.executable, SCRIPT], capture_output=True, timeout=120)
        path = os.path.join(REPORT_DIR, "paper_trading_runtime_result.json")
        with open(path) as f:
            data = json.load(f)
        assert "score" in data
        assert "rating" in data

    def test_markdown_has_score(self):
        subprocess.run([sys.executable, SCRIPT], capture_output=True, timeout=120)
        path = os.path.join(REPORT_DIR, "paper_trading_runtime_report.md")
        with open(path) as f:
            content = f.read()
        assert "Score" in content
        assert "Rating" in content

    def test_no_network(self):
        import scripts.run_paper_runtime as mod
        source = open(mod.__file__).read()
        assert "requests" not in source
        assert "httpx" not in source
