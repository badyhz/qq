"""Tests for phase10c focused paper plan preview script — structure only."""
from __future__ import annotations

import ast
import os
import py_compile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_phase10c_focused_paper_plan_preview.py")


class TestFocusedPlanPreviewScript:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_default_no_public_http(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-public-http" in content
        assert "Must specify --allow-public-http or --offline-sample" in content

    def test_offline_sample_mode(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--offline-sample" in content

    def test_default_symbols(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("preview", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert "BNBUSDT" in mod.DEFAULT_SYMBOLS
        assert "SUIUSDT" in mod.DEFAULT_SYMBOLS
        assert "XRPUSDT" in mod.DEFAULT_SYMBOLS
        assert "ARBUSDT" in mod.DEFAULT_SYMBOLS
        assert len(mod.DEFAULT_SYMBOLS) == 4

    def test_output_paths(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "_focused_paper_plan_preview.json" in content
        assert "_focused_paper_plan_preview.md" in content
        assert "_focused_paper_plan_preview.csv" in content
        assert "_focused_plan_preview_ledger.jsonl" in content

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
        spec = importlib.util.spec_from_file_location("preview", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_safety_flags_present(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("preview", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SAFETY_FLAGS")
        for flag in ["PAPER_ONLY", "NO_SECRET", "NO_ORDER", "NO_TESTNET", "NO_LIVE"]:
            assert flag in mod.SAFETY_FLAGS
