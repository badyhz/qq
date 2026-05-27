"""Tests for parameter overfit suspicion — T6001-T6040.

Smooth vs spike performance tests.
"""
from __future__ import annotations

import pytest
from core.parameter_overfit_suspicion import compute_overfit_suspicion, overfit_suspicion_to_dict


class TestOverfitSuspicionNormal:
    def test_smooth_no_suspicion(self):
        r = compute_overfit_suspicion("s1", [0.5, 0.5, 0.5, 0.5, 0.5])
        assert not r.is_suspicious

    def test_spike_suspicious(self):
        r = compute_overfit_suspicion("s1", [0.1, 0.1, 5.0, 0.1, 0.1])
        assert r.is_suspicious


class TestOverfitSuspicionEdge:
    def test_insufficient_data(self):
        r = compute_overfit_suspicion("s1", [0.5])
        assert not r.is_suspicious
