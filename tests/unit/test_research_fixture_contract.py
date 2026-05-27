"""Tests for research fixture contract — T5221-T5230.

Normal, edge, adversarial tests.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from core.research_fixture_contract import (
    FIXTURE_CLASSES, FIXTURE_SUBDIRS, discover_fixtures,
    validate_fixture_integrity,
)


class TestFixtureContractNormal:
    def test_fixture_classes_count(self):
        assert len(FIXTURE_CLASSES) == 6

    def test_fixture_classes_names(self):
        expected = {"base", "adversarial", "negative_control", "regime", "bootstrap", "expected"}
        assert set(FIXTURE_CLASSES) == expected

    def test_discover_fixtures(self):
        base = Path("tests/fixtures/research_quality")
        if base.exists():
            infos = discover_fixtures(base)
            assert len(infos) > 0


class TestFixtureContractEdge:
    def test_discover_nonexistent_dir(self):
        infos = discover_fixtures(Path("/tmp/nonexistent_fixtures"))
        assert all(not i.exists for i in infos)


class TestFixtureContractAdversarial:
    def test_validate_missing_classes(self):
        issues = validate_fixture_integrity(Path("/tmp/nonexistent"))
        assert len(issues) == len(FIXTURE_CLASSES)


class TestFixtureContractSafetyBoundary:
    def test_no_network_fixtures(self):
        for cls in FIXTURE_CLASSES:
            assert "network" not in cls.lower()
            assert "live" not in cls.lower()
