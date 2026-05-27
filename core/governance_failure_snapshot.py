"""Governance failure snapshot verifier — pure markdown diff/hash.

No file I/O. No network. Deterministic string comparison only.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class GovernanceFailureSnapshotDiff:
    ok: bool
    expected_hash: str
    actual_hash: str
    changed_sections: List[str]
    added_lines: List[str]
    removed_lines: List[str]


def normalize_governance_failure_markdown(markdown_text: str) -> str:
    """Normalize markdown for stable comparison.

    Strips trailing whitespace per line, collapses multiple blank lines,
    strips leading/trailing blank lines. Deterministic.
    """
    lines = markdown_text.split("\n")
    normalized = []
    prev_blank = False
    for line in lines:
        stripped = line.rstrip()
        is_blank = stripped == ""
        if is_blank and prev_blank:
            continue
        normalized.append(stripped)
        prev_blank = is_blank
    # strip leading/trailing blanks
    while normalized and normalized[0] == "":
        normalized.pop(0)
    while normalized and normalized[-1] == "":
        normalized.pop()
    return "\n".join(normalized)


def compare_governance_failure_markdown(
    expected: str,
    actual: str,
) -> GovernanceFailureSnapshotDiff:
    """Compare two governance failure markdown strings.

    Returns diff with ok flag, hashes, changed sections, added/removed lines.
    Deterministic. No I/O.
    """
    norm_expected = normalize_governance_failure_markdown(expected)
    norm_actual = normalize_governance_failure_markdown(actual)

    expected_hash = hashlib.sha256(norm_expected.encode()).hexdigest()[:16]
    actual_hash = hashlib.sha256(norm_actual.encode()).hexdigest()[:16]

    ok = norm_expected == norm_actual

    if ok:
        return GovernanceFailureSnapshotDiff(
            ok=True,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            changed_sections=[],
            added_lines=[],
            removed_lines=[],
        )

    expected_sections = _extract_sections(norm_expected)
    actual_sections = _extract_sections(norm_actual)

    changed_sections = []
    all_section_names = sorted(set(expected_sections.keys()) | set(actual_sections.keys()))
    for name in all_section_names:
        exp_content = expected_sections.get(name, "")
        act_content = actual_sections.get(name, "")
        if exp_content != act_content:
            changed_sections.append(name)

    expected_lines = set(norm_expected.split("\n"))
    actual_lines = set(norm_actual.split("\n"))
    added_lines = sorted(actual_lines - expected_lines)
    removed_lines = sorted(expected_lines - actual_lines)

    return GovernanceFailureSnapshotDiff(
        ok=False,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        changed_sections=changed_sections,
        added_lines=added_lines,
        removed_lines=removed_lines,
    )


def _extract_sections(markdown: str) -> dict[str, str]:
    """Split markdown into sections keyed by heading. Deterministic."""
    sections: dict[str, str] = {}
    current_name = "__preamble__"
    current_lines: list[str] = []

    for line in markdown.split("\n"):
        if line.startswith("## "):
            sections[current_name] = "\n".join(current_lines)
            current_name = line[3:].strip()
            current_lines = [line]
        elif line.startswith("# ") and not line.startswith("## "):
            sections[current_name] = "\n".join(current_lines)
            current_name = line[2:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    sections[current_name] = "\n".join(current_lines)
    return sections
