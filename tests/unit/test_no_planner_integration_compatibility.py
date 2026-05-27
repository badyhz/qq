from __future__ import annotations

import re
from pathlib import Path

PLANNER_PATTERNS = [
    "planner",
    "wave_planner",
    "batch_planner",
    "milestone_planner",
    "execution_planner",
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


def test_no_planner_imports() -> None:
    pat = re.compile(r"^\s*(?:from|import)\s+\S*planner", re.MULTILINE | re.IGNORECASE)
    for f in _collect_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Planner import found in {f}"


def test_no_planner_class_references() -> None:
    pat = re.compile(r"Planner\b")
    for f in _collect_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Planner class reference in {f}"


def test_no_planner_module_strings() -> None:
    pat = re.compile(r"\bplanner\b", re.IGNORECASE)
    for f in _collect_files():
        text = f.read_text(encoding="utf-8")
        assert not pat.search(text), f"Planner string found in {f}"
