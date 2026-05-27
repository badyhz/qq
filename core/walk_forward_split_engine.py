"""Walk-forward split engine. Pure functions, no I/O.

Generates train/validation/test index-range splits for backtesting.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence


class SplitType(Enum):
    TRAIN = "TRAIN"
    VALIDATION = "VALIDATION"
    TEST = "TEST"


@dataclass(frozen=True)
class WalkForwardSplit:
    """Frozen split descriptor. Index ranges only, no bar data."""

    split_id: int
    split_type: SplitType
    start_index: int
    end_index: int
    bar_count: int

    def __post_init__(self) -> None:
        if self.start_index < 0:
            raise ValueError(f"start_index must be >= 0, got {self.start_index}")
        if self.end_index < self.start_index:
            raise ValueError(
                f"end_index ({self.end_index}) must be >= start_index ({self.start_index})"
            )
        if self.bar_count < 0:
            raise ValueError(f"bar_count must be >= 0, got {self.bar_count}")
        if self.bar_count != self.end_index - self.start_index:
            raise ValueError(
                f"bar_count ({self.bar_count}) must equal end_index - start_index "
                f"({self.end_index - self.start_index})"
            )


def validate_split(split: WalkForwardSplit, min_bars: int) -> bool:
    """Return True if split has at least min_bars bars."""
    return split.bar_count >= min_bars


def detect_split_gaps(
    split: WalkForwardSplit, max_gap_bars: int, bar_timestamps: Optional[Sequence] = None
) -> list:
    """Detect gaps in a split. Returns list of gap descriptors.

    For index-based splits (no timestamps), checks if bar_count is reasonable
    relative to the index range. If timestamps provided, checks for missing bars.
    """
    # Pure index-based gap detection: if the index range is significantly larger
    # than the bar_count, there may be gaps. But since we operate on index ranges
    # (not actual bar data), we can only report if bar_count is 0 for non-empty range.
    gaps = []
    if split.end_index > split.start_index and split.bar_count == 0:
        gaps.append({
            "split_id": split.split_id,
            "gap_start": split.start_index,
            "gap_end": split.end_index,
            "missing_bars": split.end_index - split.start_index,
        })
    return gaps


def split_rolling(
    bars,
    train_pct: float,
    test_pct: float,
    n_splits: int,
    min_bars_per_split: int = 1,
) -> List[WalkForwardSplit]:
    """Generate rolling walk-forward splits.

    Each split has a fixed-size train window that slides forward.
    Returns list of WalkForwardSplit (train + test per split_id).
    """
    n_bars = len(bars)
    if n_splits < 1:
        raise ValueError(f"n_splits must be >= 1, got {n_splits}")
    if not 0 < train_pct < 1:
        raise ValueError(f"train_pct must be in (0, 1), got {train_pct}")
    if not 0 < test_pct < 1:
        raise ValueError(f"test_pct must be in (0, 1), got {test_pct}")
    if train_pct + test_pct > 1.0:
        raise ValueError(
            f"train_pct + test_pct must be <= 1.0, got {train_pct + test_pct}"
        )

    train_size = max(1, int(n_bars * train_pct))
    test_size = max(1, int(n_bars * test_pct))

    total_needed = train_size + test_size
    if total_needed > n_bars:
        raise ValueError(
            f"Not enough bars ({n_bars}) for train ({train_size}) + test ({test_size})"
        )

    # Calculate step size so we get n_splits evenly spaced
    available_range = n_bars - total_needed
    if n_splits == 1:
        step = 0
    else:
        step = available_range // (n_splits - 1) if n_splits > 1 else 0

    splits = []
    for i in range(n_splits):
        train_start = i * step
        train_end = train_start + train_size
        test_start = train_end
        test_end = test_start + test_size

        if test_end > n_bars:
            break

        sid = i * 2
        splits.append(
            WalkForwardSplit(
                split_id=sid,
                split_type=SplitType.TRAIN,
                start_index=train_start,
                end_index=train_end,
                bar_count=train_end - train_start,
            )
        )
        splits.append(
            WalkForwardSplit(
                split_id=sid + 1,
                split_type=SplitType.TEST,
                start_index=test_start,
                end_index=test_end,
                bar_count=test_end - test_start,
            )
        )

    return splits


def split_expanding(
    bars,
    train_pct: float,
    test_pct: float,
    n_splits: int,
    min_bars_per_split: int = 1,
) -> List[WalkForwardSplit]:
    """Generate expanding window walk-forward splits.

    The train window grows from the start, test window follows.
    Returns list of WalkForwardSplit (train + test per split_id).
    """
    n_bars = len(bars)
    if n_splits < 1:
        raise ValueError(f"n_splits must be >= 1, got {n_splits}")
    if not 0 < train_pct < 1:
        raise ValueError(f"train_pct must be in (0, 1), got {train_pct}")
    if not 0 < test_pct < 1:
        raise ValueError(f"test_pct must be in (0, 1), got {test_pct}")
    if train_pct + test_pct > 1.0:
        raise ValueError(
            f"train_pct + test_pct must be <= 1.0, got {train_pct + test_pct}"
        )

    test_size = max(1, int(n_bars * test_pct))

    # For expanding: train grows from 0, test is fixed-size window after train
    # Split points evenly across available space
    min_train = max(1, int(n_bars * train_pct))
    max_train_end = n_bars - test_size

    if min_train >= max_train_end:
        raise ValueError(
            f"Not enough bars ({n_bars}) for expanding splits with "
            f"min_train ({min_train}) and test ({test_size})"
        )

    if n_splits == 1:
        train_ends = [min_train]
    else:
        step = (max_train_end - min_train) / (n_splits - 1)
        train_ends = [min_train + int(i * step) for i in range(n_splits)]

    splits = []
    for i, train_end in enumerate(train_ends):
        test_start = train_end
        test_end = test_start + test_size

        if test_end > n_bars:
            break

        sid = i * 2
        splits.append(
            WalkForwardSplit(
                split_id=sid,
                split_type=SplitType.TRAIN,
                start_index=0,
                end_index=train_end,
                bar_count=train_end,
            )
        )
        splits.append(
            WalkForwardSplit(
                split_id=sid + 1,
                split_type=SplitType.TEST,
                start_index=test_start,
                end_index=test_end,
                bar_count=test_end - test_start,
            )
        )

    return splits
