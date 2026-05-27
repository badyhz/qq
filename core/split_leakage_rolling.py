"""Split leakage rolling — rolling split verifier.

Validates chronological ordering, no train/test overlap.
Pure functions. No network.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class RollingSplitResult:
    """Rolling split validation result."""
    split_id: str
    valid: bool
    chronological: bool
    no_overlap: bool
    train_range: Tuple[int, int]
    test_range: Tuple[int, int]
    rejection_reasons: Tuple[str, ...]


def validate_rolling_splits(
    splits: List[Dict[str, Any]],
) -> Tuple[RollingSplitResult, ...]:
    """Validate rolling splits for chronological ordering and no overlap."""
    results = []
    prev_end = -1

    for s in splits:
        split_id = s.get("split_id", "")
        train_start = s.get("train_start", 0)
        train_end = s.get("train_end", 0)
        test_start = s.get("test_start", 0)
        test_end = s.get("test_end", 0)

        reasons = []
        chronological = True
        no_overlap = True

        # Check chronological ordering
        if train_start < prev_end:
            chronological = False
            reasons.append(f"train_start {train_start} < prev_end {prev_end}")

        # Check no train/test overlap
        if train_end > test_start:
            no_overlap = False
            reasons.append(f"train_end {train_end} > test_start {test_start}")

        if train_start >= train_end:
            reasons.append(f"empty train range: [{train_start}, {train_end})")

        if test_start >= test_end:
            reasons.append(f"empty test range: [{test_start}, {test_end})")

        prev_end = max(prev_end, test_end)

        results.append(RollingSplitResult(
            split_id=split_id,
            valid=len(reasons) == 0,
            chronological=chronological,
            no_overlap=no_overlap,
            train_range=(train_start, train_end),
            test_range=(test_start, test_end),
            rejection_reasons=tuple(reasons),
        ))

    return tuple(results)


def rolling_splits_to_dict(results: Tuple[RollingSplitResult, ...]) -> Dict:
    return {
        "splits": [
            {
                "split_id": r.split_id, "valid": r.valid,
                "chronological": r.chronological, "no_overlap": r.no_overlap,
                "train_range": list(r.train_range), "test_range": list(r.test_range),
                "rejection_reasons": list(r.rejection_reasons),
            }
            for r in results
        ],
        "total_splits": len(results),
        "valid_count": sum(1 for r in results if r.valid),
        "invalid_count": sum(1 for r in results if not r.valid),
    }
