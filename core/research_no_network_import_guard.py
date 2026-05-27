"""Research no-network import guard — scan for forbidden imports.

No network. No exchange.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

from core.research_quality_contract import FORBIDDEN_IMPORTS


def scan_file_forbidden_imports(file_path: Path) -> Tuple[str, ...]:
    """Scan a single file for forbidden imports."""
    try:
        content = file_path.read_text(errors="replace")
    except (OSError, PermissionError):
        return ()

    found = []
    for imp in FORBIDDEN_IMPORTS:
        pattern = rf'(?:from|import)\s+{re.escape(imp)}\b'
        if re.search(pattern, content):
            found.append(f"{file_path.name}:{imp}")

    return tuple(found)


def scan_directory_forbidden_imports(
    code_dir: Path,
    exclude_patterns: Tuple[str, ...] = ("__pycache__", ".git", ".venv"),
) -> Tuple[str, ...]:
    """Scan directory for forbidden imports."""
    found = []
    for f in code_dir.rglob("*.py"):
        # Skip excluded patterns
        if any(p in str(f) for p in exclude_patterns):
            continue
        violations = scan_file_forbidden_imports(f)
        found.extend(violations)

    return tuple(sorted(set(found)))
