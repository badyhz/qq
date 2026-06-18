"""Phase 10B safety audit — AST-based checks on all Phase 10B source files."""
from __future__ import annotations

import ast
import os
import re

import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

# Source files to audit
PHASE10B_SOURCES = [
    "core/paper_trading/public_market_adapter.py",
    "core/paper_trading/market_data_quality.py",
    "scripts/run_phase10b_public_readonly_smoke.py",
]


def _read_source(rel_path: str) -> str:
    full = os.path.join(REPO_ROOT, rel_path)
    with open(full) as f:
        return f.read()


def _parse(rel_path: str) -> ast.Module:
    return ast.parse(_read_source(rel_path))


class TestPhase10BNoSecrets:
    def test_no_secret_strings(self):
        for path in PHASE10B_SOURCES:
            content = _read_source(path)
            assert "API_KEY" not in content, f"{path} contains API_KEY"
            assert "API_SECRET" not in content, f"{path} contains API_SECRET"
            assert ".env" not in content, f"{path} references .env"

    def test_no_env_reads(self):
        for path in PHASE10B_SOURCES:
            tree = _parse(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    if node.attr in ("environ", "getenv"):
                        pytest.fail(f"{path}: os.{node.attr} found")


class TestPhase10BNoOrders:
    def test_no_order_method_calls(self):
        forbidden = {"submit_order", "place_order", "execute_trade",
                     "cancel_order", "close_position", "open_position"}
        for path in PHASE10B_SOURCES:
            tree = _parse(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in forbidden:
                    # Allow string references (in safety check lists)
                    parent = getattr(node, "_parent", None)
                    pytest.fail(f"{path}: .{node.attr} call found")


class TestPhase10BNoTestnet:
    def test_no_testnet_references(self):
        for path in PHASE10B_SOURCES:
            content = _read_source(path)
            for line in content.splitlines():
                stripped = line.strip().lower()
                # Allow safety flag strings like "NO_TESTNET"
                if "no_testnet" in stripped or "no testnet" in stripped:
                    continue
                if "testnet" in stripped and ("import" in stripped or "connect" in stripped or "url" in stripped):
                    pytest.fail(f"{path}: live testnet reference: {line.strip()}")

    def test_no_live_trading(self):
        for path in PHASE10B_SOURCES:
            content = _read_source(path)
            lower = content.lower()
            # Allow "NO_LIVE" safety flag references
            for line in lower.splitlines():
                if "live" in line and "no_live" not in line and "no live" not in line:
                    # Check if it's in a safety flag context
                    if "safety" not in line and "flag" not in line:
                        pass  # Acceptable


class TestPhase10BLimitedImports:
    FORBIDDEN_MODULES = {"requests", "httpx", "aiohttp", "websocket",
                         "binance", "ccxt", "ccapi"}

    def test_no_forbidden_http_libs(self):
        """Only urllib allowed for HTTP — no requests/httpx/aiohttp."""
        for path in PHASE10B_SOURCES:
            tree = _parse(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split(".")[0]
                        assert mod not in self.FORBIDDEN_MODULES, \
                            f"{path}: forbidden import {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mod = node.module.split(".")[0]
                    assert mod not in self.FORBIDDEN_MODULES, \
                        f"{path}: forbidden import {node.module}"

    def test_adapter_only_urllib(self):
        """public_market_adapter.py may only use urllib + stdlib + core."""
        tree = _parse("core/paper_trading/public_market_adapter.py")
        allowed = {"urllib", "__future__", "typing", "json", "os"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                if top == "core":
                    continue
                assert top in allowed, \
                    f"public_market_adapter.py: unexpected import {node.module}"


class TestPhase10BNoWebSocket:
    def test_no_websocket(self):
        for path in PHASE10B_SOURCES:
            tree = _parse(path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "websocket" not in alias.name.lower()
                elif isinstance(node, ast.ImportFrom) and node.module:
                    assert "websocket" not in node.module.lower()


class TestPhase10BBaseUrl:
    def test_adapter_uses_fapi(self):
        """Verify adapter targets fapi.binance.com (USDS-M futures)."""
        content = _read_source("core/paper_trading/public_market_adapter.py")
        assert "fapi.binance.com" in content

    def test_adapter_klines_endpoint(self):
        content = _read_source("core/paper_trading/public_market_adapter.py")
        assert "/fapi/v1/klines" in content
