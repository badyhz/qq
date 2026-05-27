"""Tests for split rejection reasons — T5751-T5780.

Reason code coverage tests.
"""
from __future__ import annotations

import pytest
from core.split_rejection_reasons import build_rejection, rejections_to_dict, REJECTION_REASON_CODES


class TestSplitRejectionNormal:
    def test_build_rejection(self):
        r = build_rejection("s1", "TRAIN_TEST_OVERLAP")
        assert r.split_id == "s1"
        assert r.severity == "BLOCK"

    def test_reason_codes_coverage(self):
        assert len(REJECTION_REASON_CODES) >= 8


class TestSplitRejectionDeterministic:
    def test_deterministic(self):
        r1 = rejections_to_dict((build_rejection("s1", "OVERLAP"),))
        r2 = rejections_to_dict((build_rejection("s1", "OVERLAP"),))
        assert r1 == r2
