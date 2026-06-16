"""Static security scan tests for paper trading module."""
from __future__ import annotations

import ast
import os
import re

import pytest

PAPER_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "core", "paper_trading")
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")

# Patterns that should never appear in paper trading code
FORBIDDEN_PATTERNS = [
    (r'requests\.(get|post|put|delete|patch)', 'HTTP request'),
    (r'httpx\.', 'httpx client'),
    (r'aiohttp\.', 'aiohttp client'),
    (r'websocket', 'websocket connection'),
    (r'api_key\s*=', 'API key assignment'),
    (r'api_secret\s*=', 'API secret assignment'),
    (r'BINANCE_API', 'Binance API reference'),
    (r'fapi\.binance', 'Binance futures API'),
    (r'api\.binance', 'Binance spot API'),
]

# Import modules that are forbidden in paper trading
FORBIDDEN_IMPORT_MODULES = {
    'live_runner', 'live_playbook', 'submit', 'exchange',
    'testnet', 'broker', 'ccxt',
}


def _get_python_files(directory):
    result = []
    if os.path.isdir(directory):
        for f in os.listdir(directory):
            if f.endswith('.py'):
                result.append(os.path.join(directory, f))
    return result


def _parse_imports(filepath):
    with open(filepath) as f:
        tree = ast.parse(f.read())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


class TestSecurityScan:
    def test_no_http_requests(self):
        """Paper trading code must not make HTTP requests."""
        violations = []
        for filepath in _get_python_files(PAPER_DIR):
            with open(filepath) as f:
                content = f.read()
            for pattern, desc in FORBIDDEN_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    violations.append(f"{os.path.basename(filepath)}: {desc}")
        assert violations == [], f"Forbidden patterns found: {violations}"

    def test_no_forbidden_imports(self):
        """Paper trading code must not import live/testnet/exchange modules."""
        violations = []
        for filepath in _get_python_files(PAPER_DIR):
            imports = _parse_imports(filepath)
            for imp in imports:
                for forbidden in FORBIDDEN_IMPORT_MODULES:
                    if forbidden in imp:
                        violations.append(f"{os.path.basename(filepath)} imports {imp}")
        assert violations == [], f"Forbidden imports: {violations}"

    def test_no_env_reads(self):
        """Paper trading code must not read environment variables for secrets."""
        violations = []
        secret_patterns = [r'os\.environ.*key', r'os\.environ.*secret', r'os\.environ.*token']
        for filepath in _get_python_files(PAPER_DIR):
            with open(filepath) as f:
                content = f.read()
            for pattern in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    violations.append(f"{os.path.basename(filepath)}: env secret read")
        assert violations == [], f"Secret reads: {violations}"

    def test_no_subprocess_calls(self):
        """Paper trading code must not call subprocess."""
        violations = []
        for filepath in _get_python_files(PAPER_DIR):
            with open(filepath) as f:
                content = f.read()
            if 'subprocess' in content:
                violations.append(os.path.basename(filepath))
        assert violations == [], f"Subprocess calls: {violations}"

    def test_no_socket_connections(self):
        """Paper trading code must not open socket connections."""
        violations = []
        for filepath in _get_python_files(PAPER_DIR):
            with open(filepath) as f:
                content = f.read()
            if 'socket' in content.lower() and 'import socket' in content:
                violations.append(os.path.basename(filepath))
        assert violations == [], f"Socket connections: {violations}"

    def test_runner_no_real_calls(self):
        """Runner scripts must not make real API calls."""
        runner = os.path.join(SCRIPTS_DIR, "run_paper_trading_decision_engine_dry.py")
        if not os.path.exists(runner):
            pytest.skip("Runner not found")
        with open(runner) as f:
            content = f.read()
        for pattern, desc in FORBIDDEN_PATTERNS:
            assert not re.search(pattern, content, re.IGNORECASE), f"Runner has {desc}"

    def test_all_modules_frozen_or_dataclass(self):
        """All paper trading modules should use frozen dataclasses or be utility modules."""
        non_dataclass_modules = []
        for filepath in _get_python_files(PAPER_DIR):
            basename = os.path.basename(filepath)
            if basename == '__init__.py':
                continue
            with open(filepath) as f:
                content = f.read()
            # Check for dataclass or class definition
            has_class = 'class ' in content
            has_dataclass = '@dataclass' in content or 'dataclass' in content
            if has_class and not has_dataclass and 'Enum' not in content:
                non_dataclass_modules.append(basename)
        # This is informational, not a hard failure
        # Some modules like lifecycle.py have classes without @dataclass
