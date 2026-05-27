# Walk-Forward Research Matrix — Design Document

## Split Modes

### Rolling Window

Fixed-size train window that slides forward through the data.

```
Split 1: [====TRAIN====][=TEST=]................
Split 2: ........[====TRAIN====][=TEST=]........
Split 3: ................[====TRAIN====][=TEST=]
```

Properties:
- Train size is constant across all splits
- Test size is constant across all splits
- Each split uses different data (no overlap in test windows)
- Good for detecting regime changes

### Expanding Window

Train window grows from the start, test window follows.

```
Split 1: [==TRAIN==][=TEST=]....................
Split 2: [====TRAIN====][=TEST=]................
Split 3: [======TRAIN======][=TEST=]............
```

Properties:
- Train start is always index 0
- Train size grows with each split
- Test size is constant
- Good for accumulating more history

## Gap Handling

Gaps in splits are detected by `detect_split_gaps()`:
- Checks if `bar_count == 0` for a non-empty index range
- Returns list of gap descriptors with `split_id`, `gap_start`, `gap_end`, `missing_bars`

For timestamp-based gap detection, pass `bar_timestamps` to check
for missing intervals within a split.

## Minimum Bars

`validate_split(split, min_bars)` returns True if `split.bar_count >= min_bars`.

Recommended minimums:
- Train split: 50 bars minimum for statistical significance
- Test split: 20 bars minimum for meaningful evaluation

## Validation Rules

Both `split_rolling` and `split_expanding` enforce:
1. `n_splits >= 1`
2. `0 < train_pct < 1`
3. `0 < test_pct < 1`
4. `train_pct + test_pct <= 1.0`
5. Enough bars for at least one split

Violation of any rule raises `ValueError`.

## Split Data Model

```python
@dataclass(frozen=True)
class WalkForwardSplit:
    split_id: int        # Sequential ID (0, 1, 2, ...)
    split_type: SplitType  # TRAIN, VALIDATION, TEST
    start_index: int     # Inclusive start
    end_index: int       # Exclusive end
    bar_count: int       # end_index - start_index
```

Constraints:
- `start_index >= 0`
- `end_index >= start_index`
- `bar_count == end_index - start_index`
- All fields are immutable (frozen dataclass)

## Typical Configuration

```python
# 60/20 split, 3 folds
splits = split_rolling(bars, train_pct=0.6, test_pct=0.2, n_splits=3)
# Produces: [train_0, test_0, train_1, test_1, train_2, test_2]

# Expanding window
splits = split_expanding(bars, train_pct=0.5, test_pct=0.2, n_splits=5)
# Produces: 5 pairs of (train, test)
```

## Integration with Backtest Pipeline

1. Load bars from CSV via chunked reader
2. Generate splits via `split_rolling` or `split_expanding`
3. For each test split, extract bars by index range
4. Run signal engine + trade simulator on test bars
5. Aggregate metrics across all test splits
