"""Split leakage score — leakage detection model.

Pure functions. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class LeakageScore:
    """Leakage score for a split."""
    split_id: str
    leakage_score: float  # 0.0 = clean, 1.0 = fully leaked
    has_leakage: bool
    severity: str  # OK, WARNING, BLOCK
    reason: str


def compute_leakage_score(
    split: Dict[str, Any],
    overlap_threshold: float = 0.0,
) -> LeakageScore:
    """Compute leakage score for a single split."""
    train_end = split.get("train_end", 0)
    test_start = split.get("test_start", 0)

    if train_end <= test_start:
        return LeakageScore(
            split_id=split.get("split_id", ""),
            leakage_score=0.0,
            has_leakage=False,
            severity="OK",
            reason="No train/test overlap",
        )

    overlap = train_end - test_start
    train_size = train_end - split.get("train_start", 0)
    score = overlap / max(train_size, 1)

    severity = "BLOCK" if score > overlap_threshold else "WARNING"
    return LeakageScore(
        split_id=split.get("split_id", ""),
        leakage_score=min(score, 1.0),
        has_leakage=True,
        severity=severity,
        reason=f"Train/test overlap of {overlap} bars (score={score:.4f})",
    )


def leakage_score_to_dict(s: LeakageScore) -> Dict:
    return {
        "split_id": s.split_id,
        "leakage_score": s.leakage_score,
        "has_leakage": s.has_leakage,
        "severity": s.severity,
        "reason": s.reason,
    }
