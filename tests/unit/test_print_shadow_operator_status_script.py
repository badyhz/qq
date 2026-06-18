"""Tests for print_shadow_operator_status script — structure and safety."""
from __future__ import annotations

import ast
import json
import os
import py_compile
import tempfile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "print_shadow_operator_status.py")
RUNBOOK = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "SHADOW_TRADING_DAILY_OPERATOR_RUNBOOK.md")


class TestScriptStructure:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_has_report_dir_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--report-dir" in content

    def test_has_date_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--date" in content

    def test_has_main_function(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_has_render_status(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "render_status")
        assert callable(mod.render_status)

    def test_has_load_status(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "load_status")
        assert callable(mod.load_status)


class TestSafety:
    def test_no_env_reads(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("environ", "getenv"):
                    pytest.fail(f"Forbidden env read: .{node.func.attr}")

    def test_no_dangerous_imports(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        forbidden = {"websocket", "aiohttp", "httpx", "requests"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden

    def test_no_order_methods(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        forbidden_attrs = {"submit_order", "place_order", "cancel_order",
                           "execute_trade", "close_position", "get_account", "get_balance"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in forbidden_attrs:
                    pytest.fail(f"Forbidden method call: .{node.func.attr}")

    def test_safety_flags_present(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SAFETY_FLAGS")
        for flag in ["PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ORDER", "NO_TESTNET", "NO_LIVE"]:
            assert flag in mod.SAFETY_FLAGS

    def test_no_webhook_url(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--webhook-url" not in content

    def test_no_allow_send(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-send" not in content

    def test_no_shell_true(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "shell=True" not in content


class TestStatusOutput:
    def test_prints_sample_status(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "sample_status" in content

    def test_prints_testnet_gate_status(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "testnet_gate_status" in content

    def test_prints_do_not_testnet(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "不要 testnet" in content

    def test_prints_do_not_live(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "不要 live" in content

    def test_handles_missing_reports(self):
        """Script should handle missing report directory gracefully."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.load_status("/nonexistent/path")
        assert result == {}

    def test_load_status_from_files(self):
        """Script can load status from real report files."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        report_dir = os.path.join(os.path.dirname(SCRIPT), "..", "reports", "strategies")
        if os.path.isdir(report_dir):
            status = mod.load_status(report_dir)
            assert "sample_status" in status or "clean_positions" in status or len(status) == 0


class TestRenderStatus:
    def test_render_contains_key_fields(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        status = {
            "sample_status": "INSUFFICIENT_CLOSED_SAMPLE",
            "testnet_gate_status": "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE",
            "clean_positions": 54,
            "closed_clean_positions": 0,
            "excluded_positions": 4,
        }
        output = mod.render_status(status)
        assert "sample_status: INSUFFICIENT_CLOSED_SAMPLE" in output
        assert "testnet_gate_status: BLOCKED_INSUFFICIENT_CLOSED_SAMPLE" in output
        assert "clean_positions: 54" in output
        assert "不要 testnet" in output
        assert "不要 live" in output

    def test_render_low_sample(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        status = {
            "sample_status": "LOW_SAMPLE_SIZE",
            "testnet_gate_status": "BLOCKED_LOW_SAMPLE_SIZE",
            "clean_positions": 54,
            "closed_clean_positions": 20,
        }
        output = mod.render_status(status)
        assert "不要 testnet" in output
        assert "不足 30" in output

    def test_render_ready_for_review(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        status = {
            "sample_status": "EVALUABLE",
            "testnet_gate_status": "PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW",
            "clean_positions": 54,
            "closed_clean_positions": 35,
        }
        output = mod.render_status(status)
        assert "人工审查" in output
        assert "不会自动进入 testnet" in output


class TestRunbook:
    def test_runbook_exists(self):
        assert os.path.isfile(RUNBOOK)

    def test_runbook_has_main_commands(self):
        with open(RUNBOOK) as f:
            content = f.read()
        assert "run_shadow_trading_lifecycle" in content
        assert "run_shadow_position_update_only" in content
        assert "run_sample_collection_gate" in content
        assert "print_shadow_operator_status" in content

    def test_runbook_no_testnet_ready_claim(self):
        with open(RUNBOOK) as f:
            content = f.read()
        assert "testnet_ready=true" not in content
        assert "live_ready=true" not in content

    def test_runbook_has_safety_boundary(self):
        with open(RUNBOOK) as f:
            content = f.read()
        assert "Paper-only" in content
        assert "No order" in content
        assert "No testnet" in content
        assert "No live" in content

    def test_runbook_has_common_mistakes(self):
        with open(RUNBOOK) as f:
            content = f.read()
        assert "Common Mistakes" in content
        assert "clean_positions" in content
        assert "overlap" in content.lower()
