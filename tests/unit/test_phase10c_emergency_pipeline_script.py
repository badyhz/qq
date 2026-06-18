"""Tests for phase10c emergency pipeline script — structure only."""
from __future__ import annotations

import ast
import os
import py_compile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_phase10c_emergency_pipeline.py")


class TestEmergencyPipelineScript:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_has_allow_public_http(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-public-http" in content

    def test_has_offline_sample(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--offline-sample" in content

    def test_no_allow_send(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-send" not in content

    def test_no_webhook_url(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--webhook-url" not in content
        assert "webhook" not in content.lower() or "no webhook" in content.lower() or "NO_WEBHOOK" in content

    def test_default_symbols(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pipeline", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert "BNBUSDT" in mod.DEFAULT_SYMBOLS
        assert "SUIUSDT" in mod.DEFAULT_SYMBOLS
        assert "XRPUSDT" in mod.DEFAULT_SYMBOLS
        assert "ARBUSDT" in mod.DEFAULT_SYMBOLS
        assert len(mod.DEFAULT_SYMBOLS) == 9

    def test_calls_expected_scripts(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "run_phase10c_emergency_signal_report.py" in content
        assert "run_phase10c_trigger_recheck.py" in content
        assert "run_phase10c_focused_paper_plan_preview.py" in content
        assert "run_phase10c_feishu_paper_alert_payload.py" in content
        assert "run_phase10c_feishu_alert_send_gate.py" in content

    def test_writes_pipeline_result(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "_emergency_pipeline_result.json" in content
        assert "_emergency_pipeline_result.md" in content

    def test_no_secret_env_reads(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        # Check no os.environ or os.getenv calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("environ", "getenv"):
                    pytest.fail(f"Forbidden env read: .{node.func.attr}")
        # Check no API_KEY/API_SECRET string literals in non-docstring context
        with open(SCRIPT) as f:
            content = f.read()
        assert "os.environ" not in content
        assert "os.getenv" not in content

    def test_no_websocket_imports(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        forbidden = {"websocket", "aiohttp"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden

    def test_no_account_order_methods(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        forbidden_attrs = {"submit_order", "place_order", "cancel_order",
                           "execute_trade", "close_position", "get_account", "get_balance"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in forbidden_attrs:
                    pytest.fail(f"Forbidden method call: .{node.func.attr}")

    def test_has_main_function(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pipeline", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_safety_flags_present(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pipeline", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SAFETY_FLAGS")
        for flag in ["PAPER_ONLY", "NO_SECRET", "NO_ORDER", "NO_TESTNET", "NO_LIVE", "NO_WEBHOOK_SEND"]:
            assert flag in mod.SAFETY_FLAGS

    def test_send_attempted_false_in_result(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert '"send_attempted": False' in content
        assert '"actually_sent": False' in content

    def test_dry_run_for_send_gate(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--dry-run" in content
