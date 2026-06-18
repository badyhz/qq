"""Tests for phase10b public readonly smoke script — structure only."""
from __future__ import annotations

import ast
import os
import py_compile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_phase10b_public_readonly_smoke.py")


class TestPhase10BSmokeScript:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_no_secret_references(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "API_KEY" not in content
        assert "API_SECRET" not in content
        assert ".env" not in content
        assert "os.environ" not in content
        assert "os.getenv" not in content

    def test_no_order_imports_or_calls(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if node.attr in ("submit_order", "place_order", "cancel_order", "execute_trade"):
                    pytest.fail(f"Forbidden method call: .{node.attr}")

    def test_has_safety_flags(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("smoke10b", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SAFETY_FLAGS")
        assert "PAPER_ONLY" in mod.SAFETY_FLAGS
        assert "NO_ORDER" in mod.SAFETY_FLAGS
        assert "NO_SECRET" in mod.SAFETY_FLAGS
        assert "NO_TESTNET" in mod.SAFETY_FLAGS
        assert "NO_LIVE" in mod.SAFETY_FLAGS

    def test_has_run_function(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("smoke10b", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "run_smoke")
        assert callable(mod.run_smoke)
