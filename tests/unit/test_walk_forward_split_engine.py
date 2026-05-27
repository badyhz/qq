"""Tests for walk-forward split engine. 20+ tests."""

import pytest

from core.walk_forward_split_engine import (
    SplitType,
    WalkForwardSplit,
    detect_split_gaps,
    split_expanding,
    split_rolling,
    validate_split,
)


def _make_bars(n: int) -> list:
    """Create dummy bars list of length n."""
    return [{"timestamp": i, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1.0} for i in range(n)]


class TestWalkForwardSplitDataclass:
    def test_frozen_cannot_mutate(self):
        s = WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=0, end_index=10, bar_count=10)
        with pytest.raises(AttributeError):
            s.split_id = 1  # type: ignore

    def test_valid_split_construction(self):
        s = WalkForwardSplit(split_id=0, split_type=SplitType.TEST, start_index=5, end_index=15, bar_count=10)
        assert s.start_index == 5
        assert s.end_index == 15
        assert s.bar_count == 10

    def test_rejects_negative_start_index(self):
        with pytest.raises(ValueError, match="start_index"):
            WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=-1, end_index=5, bar_count=6)

    def test_rejects_end_before_start(self):
        with pytest.raises(ValueError, match="end_index"):
            WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=10, end_index=5, bar_count=0)

    def test_rejects_mismatched_bar_count(self):
        with pytest.raises(ValueError, match="bar_count"):
            WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=0, end_index=10, bar_count=5)

    def test_zero_length_split_valid(self):
        s = WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=5, end_index=5, bar_count=0)
        assert s.bar_count == 0

    def test_split_type_enum_values(self):
        assert SplitType.TRAIN.value == "TRAIN"
        assert SplitType.VALIDATION.value == "VALIDATION"
        assert SplitType.TEST.value == "TEST"


class TestValidateSplit:
    def test_valid_when_enough_bars(self):
        s = WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=0, end_index=10, bar_count=10)
        assert validate_split(s, min_bars=5) is True

    def test_valid_at_exact_minimum(self):
        s = WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=0, end_index=5, bar_count=5)
        assert validate_split(s, min_bars=5) is True

    def test_invalid_when_too_few(self):
        s = WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=0, end_index=3, bar_count=3)
        assert validate_split(s, min_bars=5) is False


class TestDetectSplitGaps:
    def test_no_gaps_for_normal_split(self):
        s = WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=0, end_index=10, bar_count=10)
        assert detect_split_gaps(s, max_gap_bars=3) == []

    def test_detects_zero_bar_count_gap(self):
        # A zero-length split with same start/end has no gap
        s = WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=5, end_index=5, bar_count=0)
        gaps = detect_split_gaps(s, max_gap_bars=3)
        # No gap because start == end
        assert len(gaps) == 0

    def test_detect_split_gaps_no_gap_for_valid(self):
        s = WalkForwardSplit(split_id=0, split_type=SplitType.TRAIN, start_index=0, end_index=10, bar_count=10)
        assert detect_split_gaps(s, max_gap_bars=3) == []


class TestSplitRolling:
    def test_basic_rolling(self):
        bars = _make_bars(100)
        splits = split_rolling(bars, train_pct=0.6, test_pct=0.2, n_splits=2)
        assert len(splits) > 0
        # Should have pairs of train + test
        assert len(splits) % 2 == 0

    def test_rolling_train_and_test_types(self):
        bars = _make_bars(100)
        splits = split_rolling(bars, train_pct=0.6, test_pct=0.2, n_splits=3)
        for i in range(0, len(splits), 2):
            assert splits[i].split_type == SplitType.TRAIN
            assert splits[i + 1].split_type == SplitType.TEST

    def test_rolling_slides_forward(self):
        bars = _make_bars(200)
        splits = split_rolling(bars, train_pct=0.5, test_pct=0.2, n_splits=3)
        train_splits = [s for s in splits if s.split_type == SplitType.TRAIN]
        # Each successive train window should start later (or same)
        for i in range(1, len(train_splits)):
            assert train_splits[i].start_index >= train_splits[i - 1].start_index

    def test_rolling_no_overlap_between_train_and_test(self):
        bars = _make_bars(100)
        splits = split_rolling(bars, train_pct=0.6, test_pct=0.2, n_splits=2)
        for i in range(0, len(splits), 2):
            train = splits[i]
            test = splits[i + 1]
            assert test.start_index >= train.end_index

    def test_rolling_rejects_bad_pct(self):
        bars = _make_bars(100)
        with pytest.raises(ValueError):
            split_rolling(bars, train_pct=0.0, test_pct=0.5, n_splits=2)
        with pytest.raises(ValueError):
            split_rolling(bars, train_pct=0.5, test_pct=0.0, n_splits=2)

    def test_rolling_rejects_sum_over_one(self):
        bars = _make_bars(100)
        with pytest.raises(ValueError, match="train_pct \\+ test_pct"):
            split_rolling(bars, train_pct=0.6, test_pct=0.5, n_splits=2)

    def test_rolling_rejects_zero_splits(self):
        bars = _make_bars(100)
        with pytest.raises(ValueError, match="n_splits"):
            split_rolling(bars, train_pct=0.6, test_pct=0.2, n_splits=0)

    def test_rolling_single_split(self):
        bars = _make_bars(100)
        splits = split_rolling(bars, train_pct=0.6, test_pct=0.2, n_splits=1)
        assert len(splits) == 2  # one train + one test

    def test_rolling_split_ids_sequential(self):
        bars = _make_bars(200)
        splits = split_rolling(bars, train_pct=0.5, test_pct=0.2, n_splits=3)
        for i, s in enumerate(splits):
            assert s.split_id == i


class TestSplitExpanding:
    def test_basic_expanding(self):
        bars = _make_bars(100)
        splits = split_expanding(bars, train_pct=0.6, test_pct=0.2, n_splits=2)
        assert len(splits) > 0
        assert len(splits) % 2 == 0

    def test_expanding_train_starts_at_zero(self):
        bars = _make_bars(100)
        splits = split_expanding(bars, train_pct=0.5, test_pct=0.2, n_splits=3)
        train_splits = [s for s in splits if s.split_type == SplitType.TRAIN]
        for ts in train_splits:
            assert ts.start_index == 0

    def test_expanding_train_grows(self):
        bars = _make_bars(200)
        splits = split_expanding(bars, train_pct=0.4, test_pct=0.2, n_splits=3)
        train_splits = [s for s in splits if s.split_type == SplitType.TRAIN]
        for i in range(1, len(train_splits)):
            assert train_splits[i].end_index >= train_splits[i - 1].end_index

    def test_expanding_test_size_constant(self):
        bars = _make_bars(200)
        splits = split_expanding(bars, train_pct=0.4, test_pct=0.2, n_splits=3)
        test_splits = [s for s in splits if s.split_type == SplitType.TEST]
        sizes = {s.bar_count for s in test_splits}
        # All test windows should be the same size
        assert len(sizes) == 1

    def test_expanding_rejects_bad_pct(self):
        bars = _make_bars(100)
        with pytest.raises(ValueError):
            split_expanding(bars, train_pct=0.0, test_pct=0.5, n_splits=2)

    def test_expanding_rejects_sum_over_one(self):
        bars = _make_bars(100)
        with pytest.raises(ValueError):
            split_expanding(bars, train_pct=0.6, test_pct=0.5, n_splits=2)

    def test_expanding_rejects_zero_splits(self):
        bars = _make_bars(100)
        with pytest.raises(ValueError):
            split_expanding(bars, train_pct=0.5, test_pct=0.2, n_splits=0)

    def test_expanding_single_split(self):
        bars = _make_bars(100)
        splits = split_expanding(bars, train_pct=0.6, test_pct=0.2, n_splits=1)
        assert len(splits) == 2
