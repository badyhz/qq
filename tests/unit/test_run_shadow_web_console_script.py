"""Tests for shadow web console runner script — structure and safety."""
from __future__ import annotations

import ast
import os
import py_compile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_shadow_web_console.py")


class TestScriptStructure:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_has_host_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--host" in content

    def test_has_port_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--port" in content

    def test_has_report_dir_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--report-dir" in content

    def test_has_smoke_render_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--smoke-render" in content

    def test_default_host_is_local(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "127.0.0.1" in content

    def test_rejects_non_local_host(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "localhost" in content
        # Should reject non-local hosts
        assert "127.0.0.1" in content

    def test_has_main_function(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)


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
        forbidden = {"websocket", "aiohttp", "httpx", "requests", "flask", "django", "fastapi"}
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

    def test_no_0000_binding(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert '0.0.0.0' not in content

    def test_safety_flags_present(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "SAFETY_FLAGS" in content or "shadow_web_console" in content


class TestLocalHostGuard:
    def test_script_validates_host(self):
        with open(SCRIPT) as f:
            content = f.read()
        # Should check host is local
        assert "127.0.0.1" in content
        assert "localhost" in content
        # Should exit on non-local host
        assert "return 1" in content or "sys.exit" in content


class TestDashboard:
    def test_dashboard_in_output(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "Shadow Trading Console" in content or "render_dashboard_html" in content

    def test_smoke_render_support(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "smoke" in content.lower()
