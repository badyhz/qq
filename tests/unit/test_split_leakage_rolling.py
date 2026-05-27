"""Tests for split leakage rolling — T5601-T5630.

Valid, overlap, missing boundary tests.
"""
from __future__ import annotations

import pytest
from core.split_leakage_rolling import validate_rolling_splits, rolling_splits_to_dict


class TestRollingSplitNormal:
    def test_valid_splits(self):
        splits = [
            {"split_id": "s1", "train_start": 0, "train_end": 50, "test_start": 50, "test_end": 100},
            {"split_id": "s2", "train_start": 100, "train_end": 150, "test_start": 150, "test_end": 200},
        ]
        results = validate_rolling_splits(splits)
        assert all(r.valid for r in results)
        assert all(r.no_overlap for r in results)

    def test_empty_splits(self):
        results = validate_rolling_splits([])
        assert results == ()


class TestRollingSplitEdge:
    def test_single_split(self):
        splits = [{"split_id": "s1", "train_start": 0, "train_end": 50, "test_start": 50, "test_end": 100}]
        results = validate_rolling_splits(splits)
        assert results[0].valid


class TestRollingSplitAdversarial:
    def test_overlap_fails(self):
        splits = [{"split_id": "s1", "train_start": 0, "train_end": 60, "test_start": 50, "test_end": 100}]
        results = validate_rolling_splits(splits)
        assert not results[0].valid
        assert not results[0].no_overlap

    def test_empty_train_fails(self):
        splits = [{"split_id": "s1", "train_start": 50, "train_end": 50, "test_start": 50, "test_end": 100}]
        results = validate_rolling_splits(splits)
        assert not results[0].valid


class TestRollingSplitDeterministic:
    def test_deterministic(self):
        splits = [{"split_id": "s1", "train_start": 0, "train_end": 50, "test_start": 50, "test_end": 100}]
        r1 = validate_rolling_splits(splits)
        r2 = validate_rolling_splits(splits)
        assert rolling_splits_to_dict(r1) == rolling_splits_to_dict(r2)
