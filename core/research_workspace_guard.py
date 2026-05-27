"""Research workspace guard — dirty workspace and frozen file guard.

No network.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from core.research_safety_regression import FROZEN_PATTERNS, FROZEN_PREFIXES


def check_workspace_dirty(
    untracked_files: Tuple[str, ...],
    modified_files: Tuple[str, ...],
) -> Dict[str, bool]:
    """Check if workspace is dirty."""
    return {
        "has_untracked": len(untracked_files) > 0,
        "has_modified": len(modified_files) > 0,
        "dirty": len(untracked_files) > 0 or len(modified_files) > 0,
    }


def check_frozen_file_guard(
    staged_files: Tuple[str, ...],
    touched_files: Tuple[str, ...],
) -> Dict[str, any]:
    """Check frozen file guard."""
    frozen_violations = []

    for f in staged_files + touched_files:
        for pattern in FROZEN_PATTERNS:
            if pattern in f:
                frozen_violations.append(f)
                break
        for prefix in FROZEN_PREFIXES:
            if f.startswith(prefix):
                frozen_violations.append(f)
                break

    return {
        "frozen_violations": list(set(frozen_violations)),
        "clean": len(frozen_violations) == 0,
    }


def check_git_add_dot(staged_files: Tuple[str, ...]) -> bool:
    """Detect if git add . was used (heuristic: too many files staged at once)."""
    return len(staged_files) > 50  # heuristic
