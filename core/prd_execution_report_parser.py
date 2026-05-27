"""Parse agent PRD execution reports into structured summaries.

Pure, deterministic, no I/O, no timestamps, no random.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


_SECTIONS = ["FILES", "TESTS", "COMMITS", "RESULT", "NOTES"]
_VALID_RESULTS = {"PASS", "PARTIAL", "FAIL", "BLOCKED"}


@dataclass(frozen=True)
class PrdExecutionReport:
    files_section: str
    tests_section: str
    commits_section: str
    result: str
    notes_section: str
    missing_sections: List[str] = field(default_factory=list)
    parsed_ok: bool = False


def _extract_sections(text: str) -> Dict[str, str]:
    """Split report text into {SECTION_NAME: body} by top-level headers."""
    import re

    lines = text.strip().splitlines()
    sections: Dict[str, str] = {}
    current_key = None
    current_lines: List[str] = []

    header_re = re.compile(r"^[A-Z][A-Z_]*\s*$")

    for line in lines:
        stripped = line.strip()
        if stripped.rstrip(":") in _SECTIONS:
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = stripped.rstrip(":")
            current_lines = []
        else:
            current_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def parse_prd_execution_report(report_text: str) -> PrdExecutionReport:
    """Parse raw report text into a PrdExecutionReport."""
    sections = _extract_sections(report_text)

    missing = [s for s in _SECTIONS if s not in sections]
    result_raw = sections.get("RESULT", "").strip()
    result_upper = result_raw.upper() if result_raw else ""

    parsed_ok = len(missing) == 0 and result_upper in _VALID_RESULTS

    return PrdExecutionReport(
        files_section=sections.get("FILES", ""),
        tests_section=sections.get("TESTS", ""),
        commits_section=sections.get("COMMITS", ""),
        result=result_upper,
        notes_section=sections.get("NOTES", ""),
        missing_sections=missing,
        parsed_ok=parsed_ok,
    )


def execution_report_to_dict(report: PrdExecutionReport) -> Dict:
    """Convert PrdExecutionReport to a plain dict."""
    return {
        "files_section": report.files_section,
        "tests_section": report.tests_section,
        "commits_section": report.commits_section,
        "result": report.result,
        "notes_section": report.notes_section,
        "missing_sections": list(report.missing_sections),
        "parsed_ok": report.parsed_ok,
    }


def execution_report_to_markdown(report: PrdExecutionReport) -> str:
    """Render PrdExecutionReport as markdown."""
    parts = [
        "# PRD Execution Report\n",
        f"**Parsed OK:** {report.parsed_ok}",
        f"**Result:** {report.result}",
        "",
        "## FILES",
        report.files_section or "(missing)",
        "",
        "## TESTS",
        report.tests_section or "(missing)",
        "",
        "## COMMITS",
        report.commits_section or "(missing)",
        "",
        "## NOTES",
        report.notes_section or "(missing)",
    ]
    if report.missing_sections:
        parts.extend(["", f"**Missing sections:** {', '.join(report.missing_sections)}"])
    return "\n".join(parts) + "\n"


def summarize_execution_report(report: PrdExecutionReport) -> Dict:
    """Return a compact summary dict."""
    return {
        "parsed_ok": report.parsed_ok,
        "result": report.result,
        "missing_sections": list(report.missing_sections),
        "has_files": bool(report.files_section),
        "has_tests": bool(report.tests_section),
        "has_commits": bool(report.commits_section),
        "has_notes": bool(report.notes_section),
    }
