from __future__ import annotations

import re
from pathlib import Path

GOVERNANCE_GLOBS = [
    "core/human_review_*.py",
    "core/dirty_workspace_*.py",
    "core/freeze_aware_*.py",
]

GOVERNANCE_DOC_GLOBS = [
    "docs/dev_prd/human_review_*.md",
    "docs/dev_prd/dirty_workspace_*.md",
    "docs/dev_prd/freeze_aware_*.md",
]


def _collect_core_files() -> list[Path]:
    files: list[Path] = []
    for pattern in GOVERNANCE_GLOBS:
        files.extend(Path(".").glob(pattern))
    return sorted(files)


def _collect_doc_files() -> list[Path]:
    files: list[Path] = []
    for pattern in GOVERNANCE_DOC_GLOBS:
        files.extend(Path(".").glob(pattern))
    return sorted(files)


def test_no_authorized_for_live_trading_in_core() -> None:
    pat = re.compile(r"authorized for live trading", re.IGNORECASE)
    for f in _collect_core_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Forbidden claim in {f}"


def test_no_authorized_for_real_order_in_core() -> None:
    pat = re.compile(r"authorized for real order", re.IGNORECASE)
    for f in _collect_core_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Forbidden claim in {f}"


def test_no_authorized_for_live_trading_in_docs() -> None:
    pat = re.compile(r"authorized for live trading", re.IGNORECASE)
    for f in _collect_doc_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Forbidden claim in {f}"


def test_no_authorized_for_real_order_in_docs() -> None:
    pat = re.compile(r"authorized for real order", re.IGNORECASE)
    for f in _collect_doc_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Forbidden claim in {f}"
