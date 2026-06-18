"""Artifact validator — check local reports integrity. No network."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ValidationIssue:
    file: str
    level: str  # ERROR or WARNING
    message: str


def validate_artifacts(report_dir: str) -> List[ValidationIssue]:
    """Validate all paper_trading reports in a directory."""
    issues: List[ValidationIssue] = []
    if not os.path.isdir(report_dir):
        issues.append(ValidationIssue(report_dir, "ERROR", "Directory does not exist"))
        return issues

    for fname in sorted(os.listdir(report_dir)):
        if not fname.startswith("paper_trading"):
            continue
        fpath = os.path.join(report_dir, fname)
        if fname.endswith(".json"):
            issues.extend(_validate_json(fpath, fname))
        elif fname.endswith(".jsonl"):
            issues.extend(_validate_jsonl(fpath, fname))
        elif fname.endswith(".md"):
            issues.extend(_validate_markdown(fpath, fname))
        elif fname.endswith(".html"):
            issues.extend(_validate_html(fpath, fname))
    return issues


def validate_artifact(filepath: str) -> List[ValidationIssue]:
    """Validate a single artifact."""
    fname = os.path.basename(filepath)
    if not os.path.isfile(filepath):
        return [ValidationIssue(fname, "ERROR", "File does not exist")]

    if fname.endswith(".json"):
        return _validate_json(filepath, fname)
    elif fname.endswith(".jsonl"):
        return _validate_jsonl(filepath, fname)
    elif fname.endswith(".md"):
        return _validate_markdown(filepath, fname)
    elif fname.endswith(".html"):
        return _validate_html(filepath, fname)
    return []


def _validate_json(path: str, name: str) -> List[ValidationIssue]:
    issues = []
    try:
        with open(path) as f:
            content = f.read()
        if not content.strip():
            issues.append(ValidationIssue(name, "ERROR", "Empty JSON file"))
            return issues
        json.loads(content)
    except json.JSONDecodeError as e:
        issues.append(ValidationIssue(name, "ERROR", f"Invalid JSON: {e}"))
    except OSError as e:
        issues.append(ValidationIssue(name, "ERROR", f"Read error: {e}"))
    return issues


def _validate_jsonl(path: str, name: str) -> List[ValidationIssue]:
    issues = []
    try:
        with open(path) as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    json.loads(stripped)
                except json.JSONDecodeError:
                    issues.append(ValidationIssue(name, "ERROR", f"Corrupted line {i}"))
    except OSError as e:
        issues.append(ValidationIssue(name, "ERROR", f"Read error: {e}"))
    return issues


def _validate_markdown(path: str, name: str) -> List[ValidationIssue]:
    issues = []
    try:
        with open(path) as f:
            content = f.read()
        if not content.strip():
            issues.append(ValidationIssue(name, "ERROR", "Empty markdown"))
            return issues
        content_lower = content.lower()
        if "paper" not in content_lower and "safety" not in content_lower:
            issues.append(ValidationIssue(name, "WARNING", "No safety/paper keywords found"))
    except OSError as e:
        issues.append(ValidationIssue(name, "ERROR", f"Read error: {e}"))
    return issues


def _validate_html(path: str, name: str) -> List[ValidationIssue]:
    issues = []
    try:
        with open(path) as f:
            content = f.read()
        if not content.strip():
            issues.append(ValidationIssue(name, "ERROR", "Empty HTML"))
            return issues
        content_lower = content.lower()
        # Check for external resources
        if 'http://' in content_lower or 'https://' in content_lower:
            issues.append(ValidationIssue(name, "ERROR", "Contains external HTTP link"))
        if '<script' in content_lower and 'src=' in content_lower:
            issues.append(ValidationIssue(name, "ERROR", "Contains script src"))
        if 'rel="stylesheet"' in content_lower:
            issues.append(ValidationIssue(name, "ERROR", "Contains external stylesheet link"))
    except OSError as e:
        issues.append(ValidationIssue(name, "ERROR", f"Read error: {e}"))
    return issues


def has_errors(issues: List[ValidationIssue]) -> bool:
    return any(i.level == "ERROR" for i in issues)
