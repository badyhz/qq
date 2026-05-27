"""Tests for research reproducibility seed — T5241-T5250.

Seed normal/invalid/repeatability, stable JSON tests.
"""
from __future__ import annotations

import pytest
from core.research_reproducibility_seed import (
    stable_json, stable_json_hash, validate_seed,
    seed_determinism_check, input_hash, DEFAULT_SEED,
)


class TestReproducibilitySeedNormal:
    def test_default_seed(self):
        assert DEFAULT_SEED == 424242

    def test_validate_valid_seed(self):
        assert validate_seed(42) is True

    def test_stable_json_sorted(self):
        data = {"b": 2, "a": 1}
        result = stable_json(data)
        assert '"a"' in result
        assert result.index('"a"') < result.index('"b"')

    def test_stable_json_hash(self):
        h = stable_json_hash({"a": 1})
        assert len(h) == 64

    def test_seed_determinism(self):
        assert seed_determinism_check({"x": 1}, seed=42, n_runs=3) is True

    def test_input_hash_stable(self):
        h1 = input_hash({"a": 1, "b": 2})
        h2 = input_hash({"b": 2, "a": 1})
        assert h1 == h2


class TestReproducibilitySeedEdge:
    def test_empty_data(self):
        h = stable_json_hash({})
        assert len(h) == 64

    def test_nested_data(self):
        data = {"a": {"b": {"c": [1, 2, 3]}}}
        h = stable_json_hash(data)
        assert len(h) == 64


class TestReproducibilitySeedAdversarial:
    def test_invalid_seed_zero(self):
        assert validate_seed(0) is False

    def test_invalid_seed_negative(self):
        assert validate_seed(-1) is False

    def test_invalid_seed_string(self):
        assert validate_seed("abc") is False

    def test_different_data_different_hash(self):
        h1 = stable_json_hash({"a": 1})
        h2 = stable_json_hash({"a": 2})
        assert h1 != h2

    def test_different_seeds_same_data(self):
        assert seed_determinism_check({"x": 1}, seed=42, n_runs=3)
        assert seed_determinism_check({"x": 1}, seed=99, n_runs=3)


class TestReproducibilitySeedDeterministic:
    def test_same_input_same_hash(self):
        data = {"key": "value", "num": 42}
        hashes = {stable_json_hash(data) for _ in range(5)}
        assert len(hashes) == 1


class TestReproducibilitySeedSafetyBoundary:
    def test_no_network(self):
        import core.research_reproducibility_seed as mod
        src = open(mod.__file__).read()
        assert "requests" not in src
        assert "urllib" not in src
