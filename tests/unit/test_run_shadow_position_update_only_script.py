"""Tests for shadow position update-only pipeline script — structure and safety."""
from __future__ import annotations

import ast
import os
import py_compile

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "run_shadow_position_update_only.py")


class TestScriptStructure:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT)

    def test_script_compiles(self):
        py_compile.compile(SCRIPT, doraise=True)

    def test_has_date_flag(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--date" in content

    def test_has_allow_public_http(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-public-http" in content

    def test_has_stop_on_failure(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--stop-on-failure" in content

    def test_has_output_dir(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--output-dir" in content


class TestPipelineSteps:
    def test_calls_run_paper_position_simulator(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "run_paper_position_simulator" in content

    def test_calls_run_paper_position_quarantine(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "run_paper_position_quarantine" in content

    def test_calls_run_paper_performance_scorecard(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "run_paper_performance_scorecard" in content

    def test_calls_run_sample_collection_gate(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "run_sample_collection_gate" in content

    def test_does_not_call_run_enabled_strategies(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "run_enabled_strategies" not in content

    def test_does_not_call_run_strategy_trade_intents(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "run_strategy_trade_intents" not in content

    def test_uses_update_existing_only(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--update-existing-only" in content

    def test_output_paths(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "_shadow_position_update_result.json" in content
        assert "_shadow_position_update_result.md" in content


class TestSafety:
    def test_no_shell_true(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "shell=True" not in content

    def test_no_allow_send(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--allow-send" not in content

    def test_no_webhook_url(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "--webhook-url" not in content

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

    def test_safety_flags_present(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SAFETY_FLAGS")
        for flag in ["PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ORDER", "NO_TESTNET", "NO_LIVE",
                      "UPDATE_ONLY_PIPELINE", "NO_NEW_POSITIONS"]:
            assert flag in mod.SAFETY_FLAGS

    def test_has_main_function(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_has_render_markdown(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("runner", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "render_markdown")
        assert callable(mod.render_markdown)

    def test_registry_integration(self):
        with open(SCRIPT) as f:
            content = f.read()
        assert "build_run_record" in content
        assert "append_registry_record" in content
        assert "evaluate_gate" in content

    def test_no_new_positions_safety(self):
        """Script enforces new_positions_count=0 in summary."""
        with open(SCRIPT) as f:
            content = f.read()
        assert "NO_NEW_POSITIONS" in content
