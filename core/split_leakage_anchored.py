"""Split leakage anchored — anchored split verifier.

Pure functions. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class AnchoredSplitResult:
    """Anchored split validation result."""
    split_id: str
    valid: bool
    anchor_index: int
    train_range: Tuple[int, int]
    test_range: Tuple[int, int]
    rejection_reasons: Tuple[str, ...]


def validate_anchored_splits(
    splits: List[Dict[str, Any]],
    min_train_bars: int = 10,
    min_test_bars: int = 5,
) -> Tuple[AnchoredSplitResult, ...]:
    """Validate anchored splits."""
    results = []
    for s in splits:
        split_id = s.get("split_id", "")
        anchor = s.get("anchor_index", 0)
        train_start = s.get("train_start", 0)
        train_end = s.get("train_end", anchor)
        test_start = s.get("test_start", anchor)
        test_end = s.get("test_end", 0)

        reasons = []

        if train_end - train_start < min_train_bars:
            reasons.append(f"train too short: {train_end - train_start} < {min_train_bars}")

        if test_end - test_start < min_test_bars:
            reasons.append(f"test too short: {test_end - test_start} < {min_test_bars}")

        if train_end > test_start:
            reasons.append(f"train/test overlap: train_end={train_end} > test_start={test_start}")

        results.append(AnchoredSplitResult(
            split_id=split_id,
            valid=len(reasons) == 0,
            anchor_index=anchor,
            train_range=(train_start, train_end),
            test_range=(test_start, test_end),
            rejection_reasons=tuple(reasons),
        ))

    return tuple(results)


def anchored_splits_to_dict(results: Tuple[AnchoredSplitResult, ...]) -> Dict:
    return {
        "splits": [
            {
                "split_id": r.split_id, "valid": r.valid,
                "anchor_index": r.anchor_index,
                "train_range": list(r.train_range), "test_range": list(r.test_range),
                "rejection_reasons": list(r.rejection_reasons),
            }
            for r in results
        ],
        "total_splits": len(results),
        "valid_count": sum(1 for r in results if r.valid),
    }
