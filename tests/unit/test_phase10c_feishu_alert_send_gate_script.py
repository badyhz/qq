"""Tests for phase10c Feishu alert send gate script — structure only."""
from __future__ import annotations

import ast
import os
import py_compile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_phase10c_feishu_alert_send_gate.py")


class TestSendGateScript:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_has_allow_send_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-send" in content

    def test_has_webhook_url_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--webhook-url" in content

    def test_has_dry_run_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--dry-run" in content

    def test_default_payload_path(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "_feishu_paper_alert_payload.json" in content

    def test_output_paths(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "_feishu_send_result.json" in content
        assert "_feishu_send_result.md" in content

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

    def test_no_secret_env_reads(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "API_KEY" not in content
        assert "API_SECRET" not in content
        assert ".env" not in content
        assert "os.environ" not in content
        assert "os.getenv" not in content

    def test_has_main_function(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("gate", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_safety_flags_present(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("gate", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SEND_GATE_SAFETY_FLAGS")
        for flag in ["PAPER_ONLY", "NO_SECRET", "NO_ORDER", "NO_TESTNET", "NO_LIVE"]:
            assert flag in mod.SEND_GATE_SAFETY_FLAGS
