"""Data quality fixture corruption — detect truncated, wrong header, poisoned files.

Pure functions. No network.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class CorruptionResult:
    """Fixture corruption check result."""
    file_path: str
    file_hash: str
    corruption_type: str  # NONE, TRUNCATED, WRONG_HEADER, WRONG_TYPE, POISONED, EMPTY
    severity: str  # OK, HARD_BLOCK
    block_promotion: bool
    details: str


REQUIRED_CSV_HEADERS = ("timestamp", "open", "high", "low", "close", "volume")


def check_fixture_corruption(
    file_path: Path,
    max_sample_bytes: int = 4096,
) -> CorruptionResult:
    """Check a single fixture file for corruption."""
    if not file_path.exists():
        return CorruptionResult(
            file_path=str(file_path), file_hash="",
            corruption_type="EMPTY", severity="HARD_BLOCK",
            block_promotion=True, details="File does not exist",
        )

    try:
        data = file_path.read_bytes()
    except (OSError, PermissionError) as e:
        return CorruptionResult(
            file_path=str(file_path), file_hash="",
            corruption_type="POISONED", severity="HARD_BLOCK",
            block_promotion=True, details=f"Cannot read: {e}",
        )

    file_hash = hashlib.sha256(data).hexdigest()

    if len(data) == 0:
        return CorruptionResult(
            file_path=str(file_path), file_hash=file_hash,
            corruption_type="EMPTY", severity="HARD_BLOCK",
            block_promotion=True, details="Empty file",
        )

    # Check for CSV header
    sample = data[:max_sample_bytes].decode("utf-8", errors="replace")
    first_line = sample.split("\n")[0].strip().lower()

    if file_path.suffix == ".csv":
        headers = [h.strip() for h in first_line.split(",")]
        missing = [h for h in REQUIRED_CSV_HEADERS if h not in headers]
        if missing:
            return CorruptionResult(
                file_path=str(file_path), file_hash=file_hash,
                corruption_type="WRONG_HEADER", severity="HARD_BLOCK",
                block_promotion=True,
                details=f"Missing CSV headers: {missing}",
            )

    # Check for JSON validity
    if file_path.suffix == ".json":
        try:
            import json
            json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return CorruptionResult(
                file_path=str(file_path), file_hash=file_hash,
                corruption_type="TRUNCATED", severity="HARD_BLOCK",
                block_promotion=True, details="Invalid JSON",
            )

    return CorruptionResult(
        file_path=str(file_path), file_hash=file_hash,
        corruption_type="NONE", severity="OK",
        block_promotion=False, details="OK",
    )


def corruption_result_to_dict(r: CorruptionResult) -> Dict:
    return {
        "file_path": r.file_path, "file_hash": r.file_hash,
        "corruption_type": r.corruption_type, "severity": r.severity,
        "block_promotion": r.block_promotion, "details": r.details,
    }
