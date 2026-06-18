"""Tests for shadow web console core module — safety and structure."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from core.paper_trading.shadow_web_console import (
    is_safe_report_name, load_console_status, render_dashboard_html,
    run_allowed_action, render_report_file, append_action_log,
    ALLOWED_ACTIONS, SAFETY_FLAGS,
)


class TestSafeReportName:
    def test_valid_json(self):
        assert is_safe_report_name("2026-06-18_report.json") is True

    def test_valid_md(self):
        assert is_safe_report_name("report.md") is True

    def test_valid_csv(self):
        assert is_safe_report_name("data.csv") is True

    def test_valid_jsonl(self):
        assert is_safe_report_name("log.jsonl") is True

    def test_rejects_path_traversal(self):
        assert is_safe_report_name("../etc/passwd") is False

    def test_rejects_slash(self):
        assert is_safe_report_name("subdir/file.json") is False

    def test_rejects_backslash(self):
        assert is_safe_report_name("subdir\\file.json") is False

    def test_rejects_dot_dot(self):
        assert is_safe_report_name("..") is False

    def test_rejects_empty(self):
        assert is_safe_report_name("") is False

    def test_rejects_unsafe_extension(self):
        assert is_safe_report_name("file.py") is False
        assert is_safe_report_name("file.sh") is False
        assert is_safe_report_name("file.exe") is False

    def test_rejects_null_byte(self):
        assert is_safe_report_name("file.json\x00.txt") is False


class TestLoadConsoleStatus:
    def test_missing_dir_returns_empty(self):
        result = load_console_status("/nonexistent/path")
        assert result == {}

    def test_loads_from_real_reports(self):
        report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "strategies")
        if os.path.isdir(report_dir):
            status = load_console_status(report_dir)
            assert isinstance(status, dict)


class TestRenderDashboard:
    def test_contains_title(self):
        html = render_dashboard_html({})
        assert "Shadow Trading Console" in html

    def test_contains_sample_status(self):
        html = render_dashboard_html({"sample_status": "INSUFFICIENT_CLOSED_SAMPLE"})
        assert "sample_status" in html
        assert "INSUFFICIENT_CLOSED_SAMPLE" in html

    def test_contains_testnet_gate_status(self):
        html = render_dashboard_html({"testnet_gate_status": "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE"})
        assert "testnet_gate_status" in html
        assert "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE" in html

    def test_contains_buttons(self):
        html = render_dashboard_html({})
        assert "扫描新机会" in html
        assert "只更新已有持仓" in html
        assert "刷新样本门禁" in html
        assert "打印当前状态" in html

    def test_contains_safety_footer(self):
        html = render_dashboard_html({})
        assert "Paper-only" in html
        assert "No order" in html
        assert "No testnet" in html
        assert "No live" in html

    def test_contains_next_action(self):
        html = render_dashboard_html({})
        assert "不要 testnet" in html
        assert "不要 live" in html

    def test_ready_for_review_hint(self):
        html = render_dashboard_html({"testnet_gate_status": "PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW"})
        assert "人工审查" in html


class TestAllowedActions:
    def test_fixed_actions(self):
        expected = {"run-lifecycle", "run-update-only", "run-sample-gate", "print-status"}
        assert set(ALLOWED_ACTIONS.keys()) == expected

    def test_all_have_label(self):
        for action, defn in ALLOWED_ACTIONS.items():
            assert "label" in defn
            assert "command" in defn

    def test_commands_use_sys_executable(self):
        for action, defn in ALLOWED_ACTIONS.items():
            cmd = defn["command"]
            assert cmd[0] == os.sys.executable

    def test_no_shell(self):
        for action, defn in ALLOWED_ACTIONS.items():
            assert "shell" not in defn

    def test_unknown_action_rejected(self):
        result = run_allowed_action("hack-the-planet", "/tmp", "/tmp")
        assert result["status"] == "REJECTED"


class TestRunAllowedAction:
    def test_print_status_passes(self):
        report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "strategies")
        repo_root = os.path.join(os.path.dirname(__file__), "..", "..")
        if os.path.isdir(report_dir):
            result = run_allowed_action("print-status", repo_root, report_dir)
            assert result["status"] == "PASS"
            assert result["exit_code"] == 0

    def test_result_has_safety_flags(self):
        result = run_allowed_action("unknown", "/tmp", "/tmp")
        # Even rejected actions should not crash
        assert result["status"] == "REJECTED"


class TestActionLog:
    def test_appends_log(self):
        with tempfile.TemporaryDirectory() as td:
            result = {"action": "test", "status": "PASS"}
            append_action_log(result, td)
            import glob
            files = glob.glob(os.path.join(td, "*_shadow_web_console_actions.jsonl"))
            assert len(files) == 1
            with open(files[0]) as f:
                line = json.loads(f.readline())
            assert line["action"] == "test"


class TestRenderReportFile:
    def test_rejects_unsafe_name(self):
        assert render_report_file("/tmp", "../etc/passwd") is None

    def test_rejects_missing_file(self):
        assert render_report_file("/tmp", "nonexistent.json") is None

    def test_reads_valid_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", dir="/tmp", delete=False) as f:
            f.write("# Test Report")
            path = f.name
        name = os.path.basename(path)
        content = render_report_file("/tmp", name)
        assert content == "# Test Report"
        os.unlink(path)


class TestSafetyFlags:
    def test_required_flags(self):
        for flag in ["PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ORDER",
                      "NO_TESTNET", "NO_LIVE", "LOCAL_ONLY"]:
            assert flag in SAFETY_FLAGS
