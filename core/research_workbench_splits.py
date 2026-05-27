"""Research workbench splits — walk-forward split adapter for the workbench.

Generates train/validation/test splits for the multi-strategy research workbench.
Pure functions, deterministic, no I/O.

No network, no exchange, no live, no submit.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class ResearchSplit:
    """A split descriptor for the research workbench."""
    split_id: str
    split_type: str  # TRAIN, VALIDATION, TEST
    start_index: int
    end_index: int
    bar_count: int
    fold_index: int


@dataclass(frozen=True)
class ResearchSplitPlan:
    """A collection of splits for a dataset."""
    plan_id: str
    split_mode: str  # "rolling"
    total_bars: int
    folds: int
    splits: Tuple[ResearchSplit, ...]
    small_data_warning: bool = False


def _make_split_id(fold_index: int, split_type: str, dataset_id: str = "") -> str:
    """Generate deterministic split id."""
    raw = f"{dataset_id}:fold{fold_index}:{split_type}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:10]
    return f"split_{fold_index}_{split_type.lower()}_{digest}"


def generate_research_splits(
    total_bars: int,
    split_mode: str = "rolling",
    train_ratio: float = 0.6,
    validation_ratio: float = 0.2,
    test_ratio: float = 0.2,
    n_folds: int = 3,
    min_bars_per_fold: int = 50,
    dataset_id: str = "",
) -> ResearchSplitPlan:
    """Generate research splits from total bar count.

    Pure function. Deterministic. No I/O.
    Generates rolling train/validation/test splits.
    """
    if n_folds < 1:
        raise ValueError(f"n_folds must be >= 1, got {n_folds}")
    if train_ratio + validation_ratio + test_ratio > 1.0 + 1e-9:
        raise ValueError("ratios must sum to <= 1.0")

    small_data_warning = total_bars < min_bars_per_fold * n_folds

    train_size = max(1, int(total_bars * train_ratio))
    val_size = max(1, int(total_bars * validation_ratio))
    test_size = max(1, int(total_bars * test_ratio))
    fold_size = train_size + val_size + test_size

    research_splits: List[ResearchSplit] = []

    for fold in range(n_folds):
        # Compute fold start for rolling
        if n_folds == 1:
            fold_start = 0
        else:
            available = total_bars - fold_size
            step = available // (n_folds - 1) if n_folds > 1 else 0
            fold_start = fold * step

        train_start = fold_start
        train_end = train_start + train_size
        val_start = train_end
        val_end = val_start + val_size
        test_start = val_end
        test_end = test_start + test_size

        if test_end > total_bars:
            break

        research_splits.append(ResearchSplit(
            split_id=_make_split_id(fold, "TRAIN", dataset_id),
            split_type="TRAIN",
            start_index=train_start,
            end_index=train_end,
            bar_count=train_end - train_start,
            fold_index=fold,
        ))
        research_splits.append(ResearchSplit(
            split_id=_make_split_id(fold, "VALIDATION", dataset_id),
            split_type="VALIDATION",
            start_index=val_start,
            end_index=val_end,
            bar_count=val_end - val_start,
            fold_index=fold,
        ))
        research_splits.append(ResearchSplit(
            split_id=_make_split_id(fold, "TEST", dataset_id),
            split_type="TEST",
            start_index=test_start,
            end_index=test_end,
            bar_count=test_end - test_start,
            fold_index=fold,
        ))

    plan_id = f"split_plan_{dataset_id}_{split_mode}_{n_folds}folds"
    return ResearchSplitPlan(
        plan_id=plan_id,
        split_mode=split_mode,
        total_bars=total_bars,
        folds=n_folds,
        splits=tuple(research_splits),
        small_data_warning=small_data_warning,
    )


def split_plan_to_dict(plan: ResearchSplitPlan) -> Dict[str, Any]:
    """Serialize split plan to dict."""
    return {
        "plan_id": plan.plan_id,
        "split_mode": plan.split_mode,
        "total_bars": plan.total_bars,
        "folds": plan.folds,
        "splits": [
            {
                "split_id": s.split_id,
                "split_type": s.split_type,
                "start_index": s.start_index,
                "end_index": s.end_index,
                "bar_count": s.bar_count,
                "fold_index": s.fold_index,
            }
            for s in plan.splits
        ],
        "small_data_warning": plan.small_data_warning,
    }
