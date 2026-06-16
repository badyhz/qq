"""Tests for multi-fixture replay runner."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "paper_trading")
SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_paper_multi_fixture_replay.py")


class TestMultiFixtureRunner:
    def test_runner_executes(self):
        """Runner script executes without crashing (exit 0 or 1 for fixture errors)."""
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode in (0, 1), f"unexpected exit: {result.returncode}, stderr: {result.stderr}"
        assert "PAPER_MULTI_FIXTURE_REPLAY_COMPLETE" in result.stdout

    def test_json_report_created(self):
        """JSON summary report is generated."""
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=60,
        )
        report_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "reports",
            "paper_trading_multi_fixture_summary.json",
        )
        assert os.path.exists(report_path)
        with open(report_path) as f:
            data = json.load(f)
        assert "total_fixtures" in data
        assert "results" in data
        assert len(data["results"]) >= 4  # at least 4 fixtures exist

    def test_markdown_report_created(self):
        """Markdown report is generated."""
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=60,
        )
        md_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "reports",
            "paper_trading_multi_fixture_report.md",
        )
        assert os.path.exists(md_path)
        with open(md_path) as f:
            content = f.read()
        assert "Paper Trading Multi-Fixture Replay Report" in content
        assert "PAPER_ONLY" in content

    def test_all_fixtures_processed(self):
        """All JSON fixtures in the directory are processed (excluding non-fixture configs)."""
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=60,
        )
        report_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "reports",
            "paper_trading_multi_fixture_summary.json",
        )
        with open(report_path) as f:
            data = json.load(f)
        SKIP = {"runtime_config_sample.json"}
        fixture_count = len([f for f in os.listdir(FIXTURE_DIR) if f.endswith(".json") and f not in SKIP])
        assert data["total_fixtures"] == fixture_count

    def test_safety_flags_in_report(self):
        """Safety flags are present in JSON report."""
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=60,
        )
        report_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "reports",
            "paper_trading_multi_fixture_summary.json",
        )
        with open(report_path) as f:
            data = json.load(f)
        for r in data["results"]:
            if r["status"] == "OK":
                assert "NO_REAL_ORDER" in r["safety_flags"]
                assert "PAPER_ONLY" in r["safety_flags"]

    def test_markdown_has_safety(self):
        """Markdown report must contain safety declarations."""
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=60,
        )
        md_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "reports",
            "paper_trading_multi_fixture_report.md",
        )
        with open(md_path) as f:
            content = f.read()
        assert "NO_REAL_ORDER" in content
        assert "NO_LIVE" in content
        assert "PAPER_ONLY" in content
