"""Structure tests for Phase 10C-3J Feishu payload runner."""
from __future__ import annotations

import ast
import os
import py_compile

import pytest


SCRIPT = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "scripts",
    "run_phase10c_feishu_paper_alert_payload.py",
)


def test_script_exists() -> None:
    assert os.path.isfile(SCRIPT)


def test_script_compiles() -> None:
    py_compile.compile(SCRIPT, doraise=True)


def test_default_outputs() -> None:
    content = open(SCRIPT, encoding="utf-8").read()
    assert "_focused_paper_plan_preview.json" in content
    assert "_feishu_paper_alert_payload.json" in content
    assert "_feishu_paper_alert_payload.md" in content


def test_no_forbidden_imports() -> None:
    tree = ast.parse(open(SCRIPT, encoding="utf-8").read())
    forbidden = {"requests", "httpx", "aiohttp", "websocket"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden


def test_no_send_or_order_calls() -> None:
    tree = ast.parse(open(SCRIPT, encoding="utf-8").read())
    forbidden_attrs = {
        "post",
        "request",
        "send",
        "submit_order",
        "place_order",
        "cancel_order",
        "execute_trade",
        "get_account",
        "get_balance",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in forbidden_attrs:
                pytest.fail(f"Forbidden method call: .{node.func.attr}")


def test_no_secret_env_reads() -> None:
    content = open(SCRIPT, encoding="utf-8").read()
    assert "API_KEY" not in content
    assert "API_SECRET" not in content
    assert ".env" not in content
    assert "os.environ" not in content
    assert "os.getenv" not in content
