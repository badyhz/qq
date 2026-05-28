"""Frozen inventory audit scanner.

Reads file metadata (size, sha256, line count, risk keywords) WITHOUT
importing or executing any target file.  Pure pathlib + hashlib only.

release_hold = HOLD
advisory_only = True
no_live / no_submit / no_exchange / no_network = True
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RELEASE_HOLD_REQUIRED = "HOLD"

MAX_SAFE_SIZE_BYTES = 512_000  # 512 KB

RISK_KEYWORDS: list[str] = [
    "live",
    "testnet",
    "shadow",
    "submit",
    "order",
    "cancel",
    "flatten",
    "positionRisk",
    "fapi",
    "binance",
    "api_key",
    "secret",
    "requests",
    "httpx",
    "aiohttp",
    "urllib",
    "websocket",
    "exchange",
    "runtime",
    "planner",
    "approve",
    "release",
    "observation",
]

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("LIVE", ["live"]),
    ("FLATTEN", ["flatten"]),
    ("CANCEL", ["cancel"]),
    ("SUBMIT", ["submit"]),
    ("TESTNET", ["testnet"]),
    ("SHADOW", ["shadow"]),
    ("OBSERVATION", ["observation"]),
    ("VERIFY", ["verify"]),
    ("RUNTIME", ["runtime"]),
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FileRecord:
    path: str
    exists: bool
    git_status: str  # untracked | tracked | modified | missing
    size_bytes: int | None = None
    line_count: int | None = None
    sha256: str | None = None
    risk_keywords: list[str] = field(default_factory=list)
    category: str = "UNKNOWN"
    skip_reason: str | None = None


@dataclass
class InventoryResult:
    files: list[FileRecord]
    manifest: dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _count_lines(path: pathlib.Path) -> int:
    with open(path, "rb") as fh:
        return sum(1 for _ in fh)


def _detect_risk_keywords(text: str) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for kw in RISK_KEYWORDS:
        if kw.lower() in lower:
            found.append(kw)
    return sorted(found)


def _classify_category(path_str: str, text: str) -> str:
    combined = (path_str + " " + text).lower()
    for cat, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in combined:
                return cat
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Git status helpers
# ---------------------------------------------------------------------------


def _git_status_map(repo_root: pathlib.Path) -> dict[str, str]:
    """Return {relative_path: status_code} from git status --short."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "status", "--short", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return {}
    out: dict[str, str] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        code = line[:2].strip()
        path = line[3:]
        if code == "??":
            out[path] = "untracked"
        elif code == "M":
            out[path] = "modified"
        elif code == "A":
            out[path] = "tracked"
        else:
            out[path] = code
    return out


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------


def scan_files(
    file_paths: list[str],
    *,
    repo_root: str | pathlib.Path = ".",
    release_hold: str = RELEASE_HOLD_REQUIRED,
    max_size_bytes: int = MAX_SAFE_SIZE_BYTES,
) -> InventoryResult:
    """Scan a list of file paths and return inventory records.

    Never imports or executes any target file.
    """
    root = pathlib.Path(repo_root).resolve()
    status_map = _git_status_map(root)

    records: list[FileRecord] = []
    for rel_path in file_paths:
        abs_path = root / rel_path
        exists = abs_path.is_file()
        git_st = status_map.get(rel_path, "missing" if not exists else "tracked")

        rec = FileRecord(path=rel_path, exists=exists, git_status=git_st)

        if not exists:
            records.append(rec)
            continue

        size = abs_path.stat().st_size
        rec.size_bytes = size

        if size > max_size_bytes:
            rec.skip_reason = f"size {size} > max {max_size_bytes}"
            rec.sha256 = _sha256_file(abs_path)
            records.append(rec)
            continue

        rec.sha256 = _sha256_file(abs_path)

        # Try reading as text for line count + keyword scan
        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
            rec.line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
            rec.risk_keywords = _detect_risk_keywords(text)
            rec.category = _classify_category(rel_path, text)
        except Exception:
            rec.skip_reason = "unreadable as text"

        records.append(rec)

    manifest = _build_manifest(
        release_hold=release_hold,
        input_paths=file_paths,
        records=records,
    )

    return InventoryResult(files=records, manifest=manifest)


def _build_manifest(
    *,
    release_hold: str,
    input_paths: list[str],
    records: list[FileRecord],
) -> dict[str, Any]:
    output_hashes = {}
    for rec in records:
        if rec.sha256:
            output_hashes[rec.path] = rec.sha256
    return {
        "release_hold": release_hold,
        "advisory_only": True,
        "human_review_required": True,
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "no_network": True,
        "no_runtime_integration": True,
        "no_planner_integration": True,
        "audit_only": True,
        "no_execution": True,
        "no_import": True,
        "generated_by": "frozen_inventory_audit.py",
        "input_paths": input_paths,
        "output_hashes": output_hashes,
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def write_json(result: InventoryResult, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "manifest": result.manifest,
        "files": [_record_to_dict(r) for r in result.files],
    }
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(result: InventoryResult, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(result: InventoryResult, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Frozen Testnet / Runtime Inventory")
    lines.append("")
    lines.append(f"**release_hold:** {result.manifest['release_hold']}")
    lines.append(f"**advisory_only:** {result.manifest['advisory_only']}")
    lines.append(f"**human_review_required:** {result.manifest['human_review_required']}")
    lines.append(f"**total files:** {len(result.files)}")
    lines.append("")

    # Category counts
    cat_counts: dict[str, int] = {}
    for rec in result.files:
        cat_counts[rec.category] = cat_counts.get(rec.category, 0) + 1
    lines.append("## Category Counts")
    lines.append("")
    for cat in sorted(cat_counts):
        lines.append(f"- {cat}: {cat_counts[cat]}")
    lines.append("")

    # Risk keyword summary
    kw_counts: dict[str, int] = {}
    for rec in result.files:
        for kw in rec.risk_keywords:
            kw_counts[kw] = kw_counts.get(kw, 0) + 1
    lines.append("## Risk Keyword Summary")
    lines.append("")
    for kw in sorted(kw_counts, key=lambda k: kw_counts[k], reverse=True):
        lines.append(f"- {kw}: {kw_counts[kw]} files")
    lines.append("")

    # Per-file detail
    lines.append("## File Detail")
    lines.append("")
    lines.append("| Path | Status | Category | Size | Lines | Risk Keywords |")
    lines.append("|------|--------|----------|------|-------|---------------|")
    for rec in result.files:
        size_str = str(rec.size_bytes) if rec.size_bytes is not None else "N/A"
        line_str = str(rec.line_count) if rec.line_count is not None else "N/A"
        kws = ", ".join(rec.risk_keywords) if rec.risk_keywords else "none"
        lines.append(f"| {rec.path} | {rec.git_status} | {rec.category} | {size_str} | {line_str} | {kws} |")
    lines.append("")

    # Safety boundary
    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- No execution. No import. No staging.")
    lines.append("- release_hold = HOLD")
    lines.append("- Advisory only. Human review required.")
    lines.append("-")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _record_to_dict(rec: FileRecord) -> dict[str, Any]:
    return {
        "path": rec.path,
        "exists": rec.exists,
        "git_status": rec.git_status,
        "size_bytes": rec.size_bytes,
        "line_count": rec.line_count,
        "sha256": rec.sha256,
        "risk_keywords": rec.risk_keywords,
        "category": rec.category,
        "skip_reason": rec.skip_reason,
    }
