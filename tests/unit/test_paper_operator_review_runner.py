"""Tests for operator review runner."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
SCRIPT = os.path.join(REPO_ROOT, "scripts", "run_paper_operator_review.py")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")


class TestOperatorReviewRunner:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        import py_compile
        py_compile.compile(SCRIPT, doraise=True)

    def test_runner_executes(self):
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=120, cwd=REPO_ROOT,
        )
        assert "PAPER_OPERATOR_REVIEW_COMPLETE" in result.stdout
        assert result.returncode == 0

    def test_output_json(self):
        subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=120, cwd=REPO_ROOT,
        )
        path = os.path.join(REPORT_DIR, "paper_trading_operator_review.json")
        assert os.path.isfile(path)
        with open(path) as f:
            data = json.load(f)
        assert "runtime_status" in data
        assert "queue_summary" in data
        assert "safety_flags" in data

    def test_output_markdown(self):
        subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=120, cwd=REPO_ROOT,
        )
        path = os.path.join(REPORT_DIR, "paper_trading_operator_review.md")
        assert os.path.isfile(path)
        with open(path) as f:
            content = f.read()
        assert "Safety" in content
        assert "NO_REAL_ORDER" in content

    def test_output_html(self):
        subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=120, cwd=REPO_ROOT,
        )
        path = os.path.join(REPORT_DIR, "paper_trading_operator_review.html")
        assert os.path.isfile(path)
        with open(path) as f:
            content = f.read()
        assert "<html" in content
        assert "http://" not in content

    def test_queue_jsonl(self):
        subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True, text=True, timeout=120, cwd=REPO_ROOT,
        )
        path = os.path.join(REPORT_DIR, "paper_trading_review_queue.jsonl")
        assert os.path.isfile(path)
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert "review_id" in entry
        assert "NO_REAL_ORDER" in entry.get("safety_flags", [])
