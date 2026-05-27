"""Tests for bootstrap research sampler — T7361-T7400.

Seed, repeatability, small sample tests.
"""
from __future__ import annotations

import pytest
from core.bootstrap_research_sampler import deterministic_bootstrap_sample, compute_bootstrap_statistic


class TestBootstrapSamplerNormal:
    def test_generates_samples(self):
        samples, seed = deterministic_bootstrap_sample([1, 2, 3, 4, 5], n_iterations=10, seed=42)
        assert len(samples) == 10

    def test_statistic(self):
        samples, _ = deterministic_bootstrap_sample([1, 2, 3], n_iterations=5, seed=42)
        stats = compute_bootstrap_statistic(samples)
        assert len(stats) == 5


class TestBootstrapSamplerEdge:
    def test_single_value(self):
        samples, _ = deterministic_bootstrap_sample([42], n_iterations=3, seed=42)
        assert all(s == [42] for s in samples)


class TestBootstrapSamplerDeterministic:
    def test_same_seed_same_samples(self):
        data = [1, 2, 3, 4, 5]
        s1, _ = deterministic_bootstrap_sample(data, n_iterations=10, seed=42)
        s2, _ = deterministic_bootstrap_sample(data, n_iterations=10, seed=42)
        assert s1 == s2

    def test_different_seed_different_samples(self):
        data = [1, 2, 3, 4, 5]
        s1, _ = deterministic_bootstrap_sample(data, n_iterations=10, seed=42)
        s2, _ = deterministic_bootstrap_sample(data, n_iterations=10, seed=99)
        assert s1 != s2
