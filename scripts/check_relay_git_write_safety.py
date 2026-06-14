#!/usr/bin/env python3
"""Static scanner for dangerous git write patterns in project files.

Scans text files for git push/tag/commit/gh release commands.
Excludes .git, .venv, __pycache__, node_modules.
Does NOT read .env, cookie, secret, token, key, password files.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache", "logs"}

SKIP_FILE_PATTERNS = re.compile(
    r"\.env|cookie|secret|token|key|password", re.IGNORECASE
)

# Files that ARE the safety infrastructure (contain patterns by design)
SELF_REFERENCE_NAMES = {
    "check_relay_git_write_safety.py",
    "relay_git_safety.py",
    "test_relay_git_write_safety.py",
    "commit_recorder.sh",
    "settings.local.json",
}

DANGEROUS_PATTERNS = [
    (re.compile(r"git\s+push"), "git push"),
    (re.compile(r"git\s+tag(?!\s+-l\b)(?!\s+--list\b)(?!\s+-d\b)"), "git tag (create)"),
    (re.compile(r"git\s+commit"), "git commit"),
    (re.compile(r"push\s+--tags"), "push --tags"),
    (re.compile(r"gh\s+release"), "gh release"),
]

# Files that are documentation/policy and contain these patterns as examples
DOC_EXEMPTION_SUFFIXES = {".md"}

# Lines that are comments or docstrings are advisory, not code
COMMENT_PREFIXES = ("#", "//", "*", '"""', "'''", "/*")


def should_skip_file(path: Path) -> bool:
    if SKIP_FILE_PATTERNS.search(path.name):
        return True
    if path.suffix in {".pyc", ".pyo", ".so", ".dylib", ".o", ".bin", ".log"}:
        return True
    if path.name in SELF_REFERENCE_NAMES:
        return True
    return False


def _is_comment_line(line: str) -> bool:
    """Check if a line is a comment or docstring (advisory, not code)."""
    stripped = line.lstrip()
    return stripped.startswith(COMMENT_PREFIXES)


def scan_file(path: Path) -> list[tuple[int, str, str, bool]]:
    """Return list of (line_number, matched_text, pattern_name, is_comment)."""
    findings = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return findings

    in_docstring = False
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        # Track docstring state (simple triple-quote toggle)
        if '"""' in stripped or "'''" in stripped:
            # Count occurrences to handle single-line docstrings
            marker = '"""' if '"""' in stripped else "'''"
            count = stripped.count(marker)
            if count == 1:
                in_docstring = not in_docstring
            # count == 2 means single-line docstring open+close, state unchanged

        is_comment = in_docstring or _is_comment_line(line)
        for pattern, name in DANGEROUS_PATTERNS:
            m = pattern.search(line)
            if m:
                findings.append((line_no, m.group(), name, is_comment))
    return findings


def scan_project(root: Path) -> dict[str, list[tuple[int, str, str, bool]]]:
    results = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if should_skip_file(fpath):
                continue
            findings = scan_file(fpath)
            if findings:
                rel = str(fpath.relative_to(root))
                results[rel] = findings
    return results


def main() -> int:
    results = scan_project(PROJECT_ROOT)
    if not results:
        print("OK: No dangerous git write patterns found.")
        return 0

    print(f"WARNING: Found dangerous git patterns in {len(results)} file(s):\n")
    for fpath, findings in sorted(results.items()):
        is_doc = fpath.endswith(".md")
        for line_no, matched, name, is_comment in findings:
            if is_doc:
                tag = " [DOC - advisory]"
            elif is_comment:
                tag = " [COMMENT - advisory]"
            else:
                tag = " [CODE - must fix]"
            print(f"  {fpath}:{line_no} — {name}{tag}")
    print()

    # Only count non-doc, non-comment findings as failures
    code_violations = {}
    for fpath, findings in results.items():
        code_findings = [f for f in findings if not fpath.endswith(".md") and not f[3]]
        if code_findings:
            code_violations[fpath] = code_findings
    if code_violations:
        print(f"FAIL: {len(code_violations)} non-doc file(s) contain dangerous git patterns in code.")
        return 1

    print("PASS: All findings are in documentation or comments (advisory only).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
