"""Tests for run_sample_collection_gate.py script."""
from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
import tempfile

import pytest

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "scripts", "run_sample_collection_gate.py")


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, SCRIPT_PATH] + args,
        capture_output=True, text=True, timeout=30, **kwargs,
    )


def _write_registry(tmpdir: str, records: list[dict]):
    path = os.path.join(tmpdir, "shadow_run_registry.jsonl")
    with open(path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def _write_scorecard(tmpdir: str, report_date: str = "2026-06-18"):
    path = os.path.join(tmpdir, f"{report_date}_paper_performance_scorecard.json")
    with open(path, "w") as f:
        json.dump({"date": report_date}, f)


def _make_registry_record(**overrides):
    rec = {
        "run_id": "20260618T120000Z_shadow_lifecycle",
        "date": "2026-06-18",
        "pipeline_status": "PASS",
        "mode": "offline_sample",
        "clean_positions": 30,
        "closed_clean_positions": 0,
        "sample_status": "INSUFFICIENT_CLOSED_SAMPLE",
        "testnet_gate_status": "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE",
        "testnet_gate_reasons": ["closed_clean_positions=0 < 10"],
    }
    rec.update(overrides)
    return rec


class TestScriptCompiles:
    def test_compiles(self):
        py_compile.compile(SCRIPT_PATH, doraise=True)


class TestWithRegistry:
    def test_empty_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_scorecard(tmpdir)
            r = _run(["--registry-dir", tmpdir, "--output-dir", tmpdir, "--date", "2026-06-18"])
            assert r.returncode == 0
            assert "Registry records: 0" in r.stdout

            json_path = os.path.join(tmpdir, "2026-06-18_shadow_sample_gate.json")
            assert os.path.isfile(json_path)
            with open(json_path) as f:
                data = json.load(f)
            assert data["total_runs"] == 0
            assert data["testnet_gate_status"] == "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE"

    def test_with_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_scorecard(tmpdir)
            _write_registry(tmpdir, [
                _make_registry_record(),
                _make_registry_record(closed_clean_positions=5, run_id="run2"),
            ])
            r = _run(["--registry-dir", tmpdir, "--output-dir", tmpdir, "--date", "2026-06-18"])
            assert r.returncode == 0
            assert "Registry records: 2" in r.stdout

            json_path = os.path.join(tmpdir, "2026-06-18_shadow_sample_gate.json")
            with open(json_path) as f:
                data = json.load(f)
            assert data["total_runs"] == 2

    def test_markdown_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_scorecard(tmpdir)
            _write_registry(tmpdir, [_make_registry_record()])
            r = _run(["--registry-dir", tmpdir, "--output-dir", tmpdir, "--date", "2026-06-18"])
            assert r.returncode == 0

            md_path = os.path.join(tmpdir, "2026-06-18_shadow_sample_gate.md")
            assert os.path.isfile(md_path)
            with open(md_path) as f:
                content = f.read()
            assert "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE" in content
            assert "不允许 testnet/live" in content

    def test_scorecard_date_conflict_fails_before_gate_publication(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_scorecard(tmpdir)
            scorecard_path = os.path.join(
                tmpdir, "2026-06-18_paper_performance_scorecard.json"
            )
            with open(scorecard_path, "w") as f:
                json.dump({"date": "2026-06-17"}, f)
            r = _run([
                "--registry-dir", tmpdir,
                "--output-dir", tmpdir,
                "--date", "2026-06-18",
            ])
            assert r.returncode == 1
            assert "report_date conflict" in r.stderr
            assert not os.path.exists(
                os.path.join(tmpdir, "2026-06-18_shadow_sample_gate.json")
            )


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
