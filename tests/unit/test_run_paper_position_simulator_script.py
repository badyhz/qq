"""Tests for paper position simulator script — structure and safety."""
from __future__ import annotations

import ast
import os
import py_compile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_paper_position_simulator.py")


class TestScriptStructure:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_has_input_file_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--input-file" in content

    def test_has_date_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--date" in content

    def test_has_allow_public_http(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-public-http" in content

    def test_has_update_with_klines(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--update-with-klines" in content

    def test_has_timeout_bars(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--timeout-bars" in content

    def test_output_paths(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "_paper_positions.json" in content
        assert "_paper_positions.md" in content
        assert "_paper_position_ledger.jsonl" in content
        assert "_paper_position_summary.json" in content

    def test_no_allow_send(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-send" not in content

    def test_no_webhook_url(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--webhook-url" not in content

    def test_no_secret_env_reads(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("environ", "getenv"):
                    pytest.fail(f"Forbidden env read: .{node.func.attr}")

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
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_safety_flags_present(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SAFETY_FLAGS")
        for flag in ["PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ORDER", "NO_TESTNET", "NO_LIVE"]:
            assert flag in mod.SAFETY_FLAGS

    def test_dry_run_only(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "actually_executed" in content
        assert "dry_run_only" in content

    def test_overlap_guard_in_markdown(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "overlap" in content.lower()

    def test_overlap_guard_in_console(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "overlap" in content.lower()
