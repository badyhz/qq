from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN_IMPORTS = [
    "core.live_runner",
    "core.execution",
    "core.order_manager",
    "core.binance_connector",
]

GOVERNANCE_GLOBS = [
    "core/human_review_*.py",
    "core/dirty_workspace_*.py",
    "core/freeze_aware_*.py",
]


def _collect_files() -> list[Path]:
    files: list[Path] = []
    for pattern in GOVERNANCE_GLOBS:
        files.extend(Path(".").glob(pattern))
    return sorted(files)


def test_no_governance_file_imports_live_runner() -> None:
    pat = re.compile(r"^\s*(?:from|import)\s+core\.live_runner", re.MULTILINE)
    for f in _collect_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Forbidden import core.live_runner in {f}"


def test_no_governance_file_imports_execution() -> None:
    pat = re.compile(r"^\s*(?:from|import)\s+core\.execution\b", re.MULTILINE)
    for f in _collect_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Forbidden import core.execution in {f}"


def test_no_governance_file_imports_order_manager() -> None:
    pat = re.compile(r"^\s*(?:from|import)\s+core\.order_manager", re.MULTILINE)
    for f in _collect_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Forbidden import core.order_manager in {f}"


def test_no_governance_file_imports_binance_connector() -> None:
    pat = re.compile(r"^\s*(?:from|import)\s+core\.binance_connector", re.MULTILINE)
    for f in _collect_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Forbidden import core.binance_connector in {f}"
