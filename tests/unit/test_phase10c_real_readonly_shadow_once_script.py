"""Tests for phase10c real readonly shadow once script — structure only."""
from __future__ import annotations

import ast
import os
import py_compile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_phase10c_real_readonly_shadow_once.py")


class TestPhase10C1Script:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_default_no_public_http(self):
        """Default mode must NOT enable real HTTP."""
        with open(SCRIPT) as f:
            content = f.read()
        # The main() function must check for --allow-public-http
        assert "--allow-public-http" in content
        # Default must require explicit flag
        assert "Must specify --allow-public-http or --offline-sample" in content

    def test_offline_sample_mode_exists(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--offline-sample" in content
        assert "run_offline_sample" in content

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

    def test_output_paths_defined(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "phase10c_real_readonly_shadow_once.json" in content
        assert "phase10c_real_readonly_shadow_once.md" in content
        assert "phase10c_real_readonly_shadow_ledger.jsonl" in content

    def test_safety_flags_present(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("phase10c1", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SAFETY_FLAGS")
        for flag in ["PAPER_ONLY", "NO_SECRET", "NO_ORDER", "NO_REAL_ORDER",
                     "NO_TESTNET", "NO_LIVE", "NO_WEBSOCKET"]:
            assert flag in mod.SAFETY_FLAGS

    def test_has_main_function(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("phase10c1", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)
