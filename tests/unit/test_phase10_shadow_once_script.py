"""Tests for phase10 shadow once script — structure only, no full run."""
from __future__ import annotations

import ast
import os
import py_compile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_phase10_shadow_once.py")


class TestPhase10ShadowOnceScript:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_no_network_imports(self):
        with open(SCRIPT) as f:
            tree = ast.parse(f.read())
        forbidden = {"requests", "httpx", "aiohttp", "websocket", "urllib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden

    def test_has_main_function(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("shadow_once", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "run_local_shadow")
        assert callable(mod.run_local_shadow)

    def test_has_safety_flags(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("shadow_once", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SAFETY_FLAGS")
        assert "PAPER_ONLY" in mod.SAFETY_FLAGS
        assert "NO_REAL_HTTP" in mod.SAFETY_FLAGS
        assert "NO_ORDER" in mod.SAFETY_FLAGS
        assert "NO_TESTNET" in mod.SAFETY_FLAGS
        assert "NO_LIVE" in mod.SAFETY_FLAGS
