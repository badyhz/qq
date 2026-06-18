"""Tests for run_shadow_trading_lifecycle.py pipeline script."""
from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
import tempfile

import pytest

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "scripts", "run_shadow_trading_lifecycle.py")

# Import internals for unit testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.run_shadow_trading_lifecycle import (
    _build_steps, _extract_summary, _run_step, render_markdown,
)


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, SCRIPT_PATH] + args,
        capture_output=True, text=True, timeout=120, **kwargs,
    )


class TestScriptCompiles:
    def test_compiles(self):
        py_compile.compile(SCRIPT_PATH, doraise=True)


class TestArgparse:
    def test_has_allow_public_http(self):
        r = _run(["--help"])
        assert "allow-public-http" in r.stdout

    def test_has_offline_sample(self):
        r = _run(["--help"])
        assert "offline-sample" in r.stdout

    def test_no_webhook_url(self):
        r = _run(["--help"])
        assert "webhook-url" not in r.stdout.lower()

    def test_no_allow_send(self):
        r = _run(["--help"])
        assert "allow-send" not in r.stdout.lower()


class TestNoForbiddenPatterns:
    def test_no_shell_true(self):
        with open(SCRIPT_PATH) as f:
            content = f.read()
        assert "shell=True" not in content

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

    def test_contains_registry_write(self):
        with open(SCRIPT_PATH) as f:
            content = f.read()
        assert "registry" in content.lower()
        assert "append_registry_record" in content or "build_run_record" in content


class TestBuildCommands:
    def test_offline_commands(self):
        steps = _build_steps("2026-06-18", "/tmp/out", allow_public_http=False, offline_sample=True)
        assert len(steps) == 5
        assert steps[0]["name"] == "run_enabled_strategies"
        assert steps[1]["name"] == "run_strategy_trade_intents"
        assert steps[2]["name"] == "run_paper_position_simulator"
        assert steps[3]["name"] == "run_paper_position_quarantine"
        assert steps[4]["name"] == "run_paper_performance_scorecard"

    def test_offline_has_offline_sample_flag(self):
        steps = _build_steps("2026-06-18", "/tmp/out", allow_public_http=False, offline_sample=True)
        assert "--offline-sample" in steps[0]["cmd"]

    def test_offline_simulator_no_public_http(self):
        steps = _build_steps("2026-06-18", "/tmp/out", allow_public_http=False, offline_sample=False)
        cmd = steps[2]["cmd"]
        assert "--allow-public-http" not in cmd
        assert "--update-with-klines" not in cmd

    def test_real_public_commands(self):
        steps = _build_steps("2026-06-18", "/tmp/out", allow_public_http=True, offline_sample=False)
        # Step 1 should have --allow-public-http
        assert "--allow-public-http" in steps[0]["cmd"]
        # Step 3 should have --allow-public-http --update-with-klines
        cmd3 = steps[2]["cmd"]
        assert "--allow-public-http" in cmd3
        assert "--update-with-klines" in cmd3
        assert "--future-only" in cmd3

    def test_date_passed_to_all(self):
        steps = _build_steps("2026-06-18", "/tmp/out", False, False)
        for step in steps:
            assert "--date" in step["cmd"]
            assert "2026-06-18" in step["cmd"]


class TestExtractSummary:
    def test_missing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary, missing = _extract_summary("2099-01-01", tmpdir)
            assert len(missing) == 5
            assert "strategy_run_summary" in missing

    def test_with_scorecard_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sc_data = {
                "global_metrics": {
                    "clean_positions": 10,
                    "excluded_positions": 2,
                    "closed_positions": 3,
                    "sample_status": "LOW_SAMPLE_SIZE",
                },
                "strategy_scorecards": [{"strategy_id": "a"}, {"strategy_id": "b"}],
            }
            with open(os.path.join(tmpdir, "2026-06-18_paper_performance_scorecard.json"), "w") as f:
                json.dump(sc_data, f)

            summary, missing = _extract_summary("2026-06-18", tmpdir)
            assert summary["closed_clean_positions"] == 3
            assert summary["sample_status"] == "LOW_SAMPLE_SIZE"
            assert summary["strategy_scorecard_rows"] == 2
            assert "scorecard" not in missing


class TestRunStep:
    def test_pass_command(self):
        result = _run_step("test", [sys.executable, "-c", "print('ok')"])
        assert result["status"] == "PASS"
        assert result["exit_code"] == 0
        assert "ok" in result["stdout_tail"]

    def test_fail_command(self):
        result = _run_step("test", [sys.executable, "-c", "import sys; sys.exit(1)"])
        assert result["status"] == "FAIL"
        assert result["exit_code"] == 1

    def test_result_fields(self):
        result = _run_step("test", [sys.executable, "-c", "pass"])
        assert "step_name" in result
        assert "command" in result
        assert "started_at" in result
        assert "finished_at" in result
        assert "duration_seconds" in result


class TestRenderMarkdown:
    def test_contains_safety_text(self):
        result = {
            "date": "2026-06-18",
            "mode": "offline_sample",
            "pipeline_status": "PASS",
            "steps": [],
            "summary": {"sample_status": "INSUFFICIENT_CLOSED_SAMPLE"},
        }
        md = render_markdown(result)
        assert "shadow-only" in md.lower() or "Shadow-only" in md
        assert "不会下单" in md
        assert "不会 testnet/live" in md

    def test_contains_insufficient_message(self):
        result = {
            "date": "2026-06-18",
            "mode": "offline_sample",
            "pipeline_status": "PASS",
            "steps": [],
            "summary": {"sample_status": "INSUFFICIENT_CLOSED_SAMPLE"},
        }
        md = render_markdown(result)
        assert "INSUFFICIENT_CLOSED_SAMPLE" in md
        assert "不允许进入 testnet/live" in md

    def test_contains_step_table(self):
        result = {
            "date": "2026-06-18",
            "mode": "offline_sample",
            "pipeline_status": "PASS",
            "steps": [
                {"step_name": "step1", "status": "PASS", "duration_seconds": 1.0, "exit_code": 0},
            ],
            "summary": {},
        }
        md = render_markdown(result)
        assert "step1" in md
        assert "PASS" in md

    def test_contains_sample_gate_section(self):
        result = {
            "date": "2026-06-18",
            "mode": "offline_sample",
            "pipeline_status": "PASS",
            "steps": [],
            "summary": {
                "closed_clean_positions": 0,
                "sample_status": "INSUFFICIENT_CLOSED_SAMPLE",
            },
            "sample_gate_status": "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE",
            "sample_gate_reasons": ["closed_clean_positions=0 < 10"],
        }
        md = render_markdown(result)
        assert "Sample Collection Gate" in md
        assert "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE" in md
