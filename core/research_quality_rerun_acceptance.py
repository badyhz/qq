"""Research quality rerun acceptance — rerun bundle comparable with identical hashes.

No network.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from core.research_rerun_diff import detect_rerun_diff
from core.research_quality_manifest import REQUIRED_ARTIFACTS


def verify_rerun_acceptance(
    original_dir: Path,
    rerun_dir: Path,
) -> Dict:
    """Verify rerun produces identical hashes."""
    diff_result = detect_rerun_diff(original_dir, rerun_dir, REQUIRED_ARTIFACTS)

    return {
        "original_dir": str(original_dir),
        "rerun_dir": str(rerun_dir),
        "identical": diff_result["identical"],
        "differences": diff_result["differences"],
        "missing": diff_result["missing"],
        "verdict": "PASS" if diff_result["identical"] else "FAIL",
    }
