"""Tests for Feishu alert send gate — dry-run, safety, validation."""
from __future__ import annotations

import ast
import json
import os
import py_compile
import tempfile

import pytest

from core.paper_trading.feishu_alert_send_gate import (
    validate_payload_file,
    validate_safety_flags,
    build_feishu_request_body,
    run_send_gate,
    SendResult,
    SEND_GATE_SAFETY_FLAGS,
)


def _make_payload_file(tmpdir, payloads=None, **overrides):
    """Create a minimal valid payload file for testing."""
    if payloads is None:
        payloads = [_make_payload()]
    data = {
        "date": "2026-06-18",
        "source_mode": "real_public_http",
        "payload_count": len(payloads),
        "payloads": payloads,
        "dry_run_only": True,
        "actually_sent": False,
        "webhook_send_attempted": False,
        "not_order_payload": True,
        "safety_flags": [
            "PAPER_ONLY", "FEISHU_READY_ONLY", "NO_WEBHOOK_SEND",
            "NO_SECRET", "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER",
            "NO_TESTNET", "NO_LIVE", "NOT_TRADING_RECOMMENDATION",
        ],
        "final_verdict": "TEST",
    }
    data.update(overrides)
    path = os.path.join(tmpdir, "payload.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def _make_payload(**overrides):
    payload = {
        "payload_id": "FPA_test123",
        "symbol": "BNBUSDT",
        "timeframe": "5m",
        "direction": "LONG_OBSERVE",
        "priority": "WATCH",
        "title": "[PAPER WATCH] BNBUSDT 5m LONG_OBSERVE",
        "message_text": "test message",
        "feishu_payload": {"msg_type": "interactive", "card": {}},
        "dry_run_only": True,
        "actually_sent": False,
        "webhook_send_attempted": False,
        "not_order_payload": True,
        "safety_flags": ["PAPER_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"],
    }
    payload.update(overrides)
    return payload


class TestValidatePayloadFile:
    def test_valid_payload(self):
        data = {
            "date": "2026-06-18", "payload_count": 1, "payloads": [_make_payload()],
            "safety_flags": ["PAPER_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"],
            "dry_run_only": True, "not_order_payload": True,
            "actually_sent": False, "webhook_send_attempted": False,
        }
        ok, issues = validate_payload_file(data)
        assert ok is True
        assert issues == []

    def test_missing_fields(self):
        ok, issues = validate_payload_file({})
        assert ok is False
        assert any("missing field" in i for i in issues)

    def test_dry_run_only_false(self):
        data = {
            "date": "x", "payload_count": 1, "payloads": [_make_payload()],
            "safety_flags": ["PAPER_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"],
            "dry_run_only": False, "not_order_payload": True,
            "actually_sent": False, "webhook_send_attempted": False,
        }
        ok, issues = validate_payload_file(data)
        assert ok is False
        assert any("dry_run_only" in i for i in issues)

    def test_actually_sent_true_fails(self):
        data = {
            "date": "x", "payload_count": 1, "payloads": [_make_payload()],
            "safety_flags": ["PAPER_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"],
            "dry_run_only": True, "not_order_payload": True,
            "actually_sent": True, "webhook_send_attempted": False,
        }
        ok, issues = validate_payload_file(data)
        assert ok is False
        assert any("actually_sent" in i for i in issues)

    def test_webhook_send_attempted_true_fails(self):
        data = {
            "date": "x", "payload_count": 1, "payloads": [_make_payload()],
            "safety_flags": ["PAPER_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"],
            "dry_run_only": True, "not_order_payload": True,
            "actually_sent": False, "webhook_send_attempted": True,
        }
        ok, issues = validate_payload_file(data)
        assert ok is False
        assert any("webhook_send_attempted" in i for i in issues)

    def test_empty_payloads(self):
        data = {
            "date": "x", "payload_count": 0, "payloads": [],
            "safety_flags": ["PAPER_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"],
            "dry_run_only": True, "not_order_payload": True,
            "actually_sent": False, "webhook_send_attempted": False,
        }
        ok, issues = validate_payload_file(data)
        assert ok is False
        assert any("empty" in i for i in issues)


class TestValidateSafetyFlags:
    def test_valid_flags(self):
        data = {"safety_flags": ["PAPER_ONLY", "NO_ORDER", "NO_REAL_ORDER", "NO_SECRET", "EXTRA"]}
        ok, issues = validate_safety_flags(data)
        assert ok is True

    def test_missing_paper_only(self):
        data = {"safety_flags": ["NO_ORDER", "NO_REAL_ORDER", "NO_SECRET"]}
        ok, issues = validate_safety_flags(data)
        assert ok is False
        assert any("PAPER_ONLY" in i for i in issues)

    def test_missing_no_order(self):
        data = {"safety_flags": ["PAPER_ONLY", "NO_REAL_ORDER", "NO_SECRET"]}
        ok, issues = validate_safety_flags(data)
        assert ok is False
        assert any("NO_ORDER" in i for i in issues)


class TestRunSendGateDryRun:
    def test_default_dry_run(self, tmp_path):
        path = _make_payload_file(str(tmp_path))
        result = run_send_gate(path)
        assert result.dry_run is True
        assert result.allow_send is False
        assert result.send_attempted is False
        assert result.actually_sent is False
        assert result.safety_passed is True
        assert result.payload_count == 1

    def test_allow_send_without_webhook(self, tmp_path):
        path = _make_payload_file(str(tmp_path))
        result = run_send_gate(path, allow_send=True)
        assert result.dry_run is True
        assert result.allow_send is True
        assert result.webhook_url_provided is False
        assert result.send_attempted is False
        assert result.actually_sent is False

    def test_missing_payload_file(self):
        result = run_send_gate("/nonexistent/path.json")
        assert result.dry_run is True
        assert result.safety_passed is False
        assert result.actually_sent is False

    def test_invalid_payload_fails(self, tmp_path):
        path = _make_payload_file(str(tmp_path), dry_run_only=False)
        result = run_send_gate(path)
        assert result.safety_passed is False
        assert result.actually_sent is False


class TestRunSendGateWithMockSend:
    def test_mock_send_success(self, tmp_path, monkeypatch):
        path = _make_payload_file(str(tmp_path))

        def mock_urlopen(req, timeout=10):
            class MockResp:
                def read(self):
                    return json.dumps({"code": 0}).encode()
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return MockResp()

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        result = run_send_gate(path, allow_send=True, webhook_url="https://example.com/hook")
        assert result.send_attempted is True
        assert result.sent_count == 1
        assert result.failed_count == 0
        assert result.actually_sent is True
        assert result.dry_run is False

    def test_mock_send_failure(self, tmp_path, monkeypatch):
        path = _make_payload_file(str(tmp_path))

        def mock_urlopen(req, timeout=10):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        result = run_send_gate(path, allow_send=True, webhook_url="https://example.com/hook")
        assert result.send_attempted is True
        assert result.sent_count == 0
        assert result.failed_count == 1
        assert result.actually_sent is False


class TestSendGateSafety:
    def test_no_env_read(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "feishu_alert_send_gate.py")
        with open(module_path) as f:
            content = f.read()
        assert "os.environ" not in content
        assert "os.getenv" not in content
        assert ".env" not in content
        assert "API_KEY" not in content
        assert "API_SECRET" not in content

    def test_no_order_words(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "feishu_alert_send_gate.py")
        with open(module_path) as f:
            tree = ast.parse(f.read())
        forbidden = {"submit_order", "place_order", "cancel_order",
                     "execute_trade", "close_position", "get_account", "get_balance"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in forbidden:
                    pytest.fail(f"Forbidden method call: .{node.func.attr}")

    def test_no_network_imports(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "feishu_alert_send_gate.py")
        with open(module_path) as f:
            tree = ast.parse(f.read())
        forbidden = {"requests", "httpx", "aiohttp", "websocket"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden

    def test_module_compiles(self):
        module_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "core", "paper_trading", "feishu_alert_send_gate.py")
        py_compile.compile(module_path, doraise=True)

    def test_safety_flags_present(self):
        assert "PAPER_ONLY" in SEND_GATE_SAFETY_FLAGS
        assert "NO_SECRET" in SEND_GATE_SAFETY_FLAGS
        assert "NO_ORDER" in SEND_GATE_SAFETY_FLAGS
        assert "NO_TESTNET" in SEND_GATE_SAFETY_FLAGS
        assert "NO_LIVE" in SEND_GATE_SAFETY_FLAGS
        assert "NO_AUTO_SEND" in SEND_GATE_SAFETY_FLAGS
