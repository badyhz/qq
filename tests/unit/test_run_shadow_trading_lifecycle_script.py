"""Tests for run_shadow_trading_lifecycle.py pipeline script."""
from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "scripts", "run_shadow_trading_lifecycle.py")

# Import internals for unit testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.run_shadow_trading_lifecycle import (
    _build_steps, _extract_summary, _run_step, _ts,
    finalize_batch_registry, render_markdown,
)
import scripts.run_shadow_trading_lifecycle as lifecycle_script


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

    def test_timestamps_are_timezone_aware(self):
        assert datetime.fromisoformat(_ts()).tzinfo is not None


class TestBatchContract:
    def test_explicit_run_id_is_preserved_without_registry(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lifecycle_script, "_build_steps", lambda *a, **k: [])
        monkeypatch.setattr(
            lifecycle_script,
            "_extract_summary",
            lambda *a, **k: ({"closed_clean_positions": 0}, []),
        )
        monkeypatch.setattr(
            lifecycle_script,
            "generate_run_id",
            lambda: pytest.fail("explicit run ID must not be regenerated"),
        )
        monkeypatch.setattr(
            sys,
            "argv",
            [SCRIPT_PATH, "--date", "2026-07-13", "--output-dir", str(tmp_path),
             "--run-id", "RUN-123", "--defer-scorecard", "--defer-registry"],
        )
        assert lifecycle_script.main() == 0
        result = json.loads(
            (tmp_path / "2026-07-13_shadow_lifecycle_result.json").read_text()
        )
        assert result["run_id"] == "RUN-123"
        assert result["registry_written"] is False
        assert datetime.fromisoformat(result["started_at"]).tzinfo is not None
        assert datetime.fromisoformat(result["finished_at"]).tzinfo is not None

    def test_standalone_run_generates_compatible_id(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lifecycle_script, "_build_steps", lambda *a, **k: [])
        monkeypatch.setattr(
            lifecycle_script,
            "_extract_summary",
            lambda *a, **k: ({"closed_clean_positions": 0}, []),
        )
        monkeypatch.setattr(lifecycle_script, "generate_run_id", lambda: "AUTO-RUN")
        monkeypatch.setattr(
            sys,
            "argv",
            [SCRIPT_PATH, "--date", "2026-07-13", "--output-dir", str(tmp_path),
             "--defer-scorecard", "--defer-registry"],
        )
        assert lifecycle_script.main() == 0
        result = json.loads(
            (tmp_path / "2026-07-13_shadow_lifecycle_result.json").read_text()
        )
        assert result["run_id"] == "AUTO-RUN"

    def test_final_registry_is_unique_and_after_both_runners(self, tmp_path):
        run_id = "RUN-123"
        started = datetime.now(timezone.utc) - timedelta(minutes=2)
        lifecycle_finished = started + timedelta(seconds=30)
        update_started = lifecycle_finished + timedelta(seconds=1)
        update_finished = update_started + timedelta(seconds=30)

        def result(start, finish, name):
            return {
                "date": "2026-07-13", "mode": "offline", "pipeline_status": "PASS",
                "allow_public_http": False, "run_id": run_id,
                "started_at": start.isoformat(), "finished_at": finish.isoformat(),
                "steps": [{"step_name": name, "status": "PASS", "exit_code": 0,
                           "started_at": start.isoformat(), "finished_at": finish.isoformat()}],
            }

        (tmp_path / "2026-07-13_shadow_lifecycle_result.json").write_text(
            json.dumps(result(started, lifecycle_finished, "lifecycle"))
        )
        (tmp_path / "2026-07-13_shadow_position_update_result.json").write_text(
            json.dumps(result(update_started, update_finished, "update"))
        )
        (tmp_path / "2026-07-13_strategy_run_summary.json").write_text(
            json.dumps({"candidate_count": 0})
        )
        (tmp_path / "2026-07-13_trade_intents.json").write_text(
            json.dumps({"intent_count": 0, "status_counts": {}})
        )
        (tmp_path / "2026-07-13_paper_position_summary.json").write_text(
            json.dumps({"status_counts": {}, "lifecycle_stats": {}})
        )
        (tmp_path / "2026-07-13_paper_positions_quarantine.json").write_text(
            json.dumps({"quarantined_count": 0, "clean_count": 0})
        )
        (tmp_path / "2026-07-13_paper_performance_scorecard.json").write_text(
            json.dumps({"global_metrics": {"closed_positions": 0,
                                            "sample_status": "LOW_SAMPLE_SIZE"},
                        "cumulative_closed_clean": 0, "strategy_scorecards": []})
        )

        finalize_batch_registry("2026-07-13", str(tmp_path), run_id, started.isoformat())
        records = [json.loads(line) for line in
                   (tmp_path / "shadow_run_registry.jsonl").read_text().splitlines()]
        assert len(records) == 1
        assert records[0]["run_id"] == run_id
        assert datetime.fromisoformat(records[0]["started_at"]).tzinfo is not None
        registry_finished = datetime.fromisoformat(records[0]["finished_at"])
        assert registry_finished >= lifecycle_finished
        assert registry_finished >= update_finished
        with pytest.raises(ValueError, match="already contains"):
            finalize_batch_registry("2026-07-13", str(tmp_path), run_id, started.isoformat())


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
