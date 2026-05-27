"""Tests for split leakage score — T5691-T5720.

Clean, leaky, ambiguous fixtures.
"""
from __future__ import annotations

import pytest
from core.split_leakage_score import compute_leakage_score, leakage_score_to_dict


class TestLeakageScoreNormal:
    def test_clean_split(self):
        s = compute_leakage_score({"split_id": "s1", "train_end": 50, "test_start": 50, "train_start": 0})
        assert not s.has_leakage
        assert s.leakage_score == 0.0

    def test_leaky_split(self):
        s = compute_leakage_score({"split_id": "s1", "train_end": 60, "test_start": 50, "train_start": 0})
        assert s.has_leakage
        assert s.leakage_score > 0


class TestLeakageScoreDeterministic:
    def test_deterministic(self):
        split = {"split_id": "s1", "train_end": 50, "test_start": 50, "train_start": 0}
        s1 = leakage_score_to_dict(compute_leakage_score(split))
        s2 = leakage_score_to_dict(compute_leakage_score(split))
        assert s1 == s2
