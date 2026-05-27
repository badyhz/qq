"""Split rejection reasons — registry of reason codes.

Pure functions. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


REJECTION_REASON_CODES = {
    "TRAIN_TEST_OVERLAP": "Train and test ranges overlap",
    "NON_CHRONOLOGICAL": "Splits not in chronological order",
    "EMPTY_TRAIN": "Train range is empty",
    "EMPTY_TEST": "Test range is empty",
    "SHORT_TRAIN": "Train range too short",
    "SHORT_TEST": "Test range too short",
    "LEAKAGE_DETECTED": "Data leakage detected between train and test",
    "BOUNDARY_HASH_MISMATCH": "Boundary hash changed unexpectedly",
    "SPLIT_COVERAGE_MISMATCH": "Split coverage inconsistent across symbols",
}


@dataclass(frozen=True)
class SplitRejection:
    """A single split rejection."""
    split_id: str
    reason_code: str
    reason_text: str
    severity: str  # BLOCK, WARNING


def build_rejection(
    split_id: str,
    reason_code: str,
    severity: str = "BLOCK",
) -> SplitRejection:
    return SplitRejection(
        split_id=split_id,
        reason_code=reason_code,
        reason_text=REJECTION_REASON_CODES.get(reason_code, "Unknown reason"),
        severity=severity,
    )


def rejections_to_dict(rejections: Tuple[SplitRejection, ...]) -> Dict:
    return {
        "rejections": [
            {"split_id": r.split_id, "reason_code": r.reason_code,
             "reason_text": r.reason_text, "severity": r.severity}
            for r in rejections
        ],
        "total_rejections": len(rejections),
        "blocks": sum(1 for r in rejections if r.severity == "BLOCK"),
    }
