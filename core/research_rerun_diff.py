"""Research rerun diff detector — detect differences between two quality bundles.

No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

from core.research_artifact_hashing import TIMESTAMP_ALLOWLIST, compare_hashes, compute_artifact_hashes
from core.research_quality_contract import RELEASE_HOLD_VALUE
from core.research_quality_manifest import REQUIRED_ARTIFACTS


def detect_rerun_diff(
    left_dir: Path,
    right_dir: Path,
    artifact_names: Tuple[str, ...] = REQUIRED_ARTIFACTS,
    allowlist: Tuple[str, ...] = TIMESTAMP_ALLOWLIST,
) -> Dict:
    """Detect differences between two quality bundle runs."""
    left_hashes = compute_artifact_hashes(left_dir, artifact_names)
    right_hashes = compute_artifact_hashes(right_dir, artifact_names)

    diffs, missing = compare_hashes(left_hashes, right_hashes, allowlist)

    return {
        "schema_version": "1.0.0",
        "generated_by": "research_rerun_diff",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "left_dir": str(left_dir),
        "right_dir": str(right_dir),
        "total_left_artifacts": len(left_hashes),
        "total_right_artifacts": len(right_hashes),
        "differences": diffs,
        "missing": list(missing),
        "identical": len(diffs) == 0 and len(missing) == 0,
        "warnings": [] if not diffs else [f"DIFFS_FOUND:{len(diffs)}"],
        "hard_blocks": [] if not diffs and not missing else ["RERUN_DIFF_DETECTED"],
        "verdict": "PASS" if not diffs and not missing else "FAIL",
    }
