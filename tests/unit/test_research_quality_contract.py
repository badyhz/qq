"""Tests for research quality contract — T5201-T5210.

Normal, edge, adversarial, deterministic, safety boundary tests.
"""
from __future__ import annotations

import pytest
from core.research_quality_contract import (
    DEFAULT_CONTRACT, QualityContract, RELEASE_HOLD_VALUE,
    SAFETY_FLAGS, FORBIDDEN_IMPORTS, assert_contract_valid,
)


class TestQualityContractNormal:
    def test_default_contract_valid(self):
        assert DEFAULT_CONTRACT.is_valid()

    def test_default_contract_hold(self):
        assert DEFAULT_CONTRACT.release_hold == "HOLD"

    def test_default_contract_advisory(self):
        assert DEFAULT_CONTRACT.advisory_only is True

    def test_default_contract_human_review(self):
        assert DEFAULT_CONTRACT.human_review_required is True

    def test_contract_to_dict(self):
        d = DEFAULT_CONTRACT.to_dict()
        assert d["release_hold"] == "HOLD"
        assert d["advisory_only"] is True
        assert d["human_review_required"] is True
        assert d["valid"] is True
        assert d["violations"] == []

    def test_safety_flags_all_true(self):
        for k, v in SAFETY_FLAGS.items():
            assert v is True, f"{k} must be True"

    def test_assert_valid(self):
        assert_contract_valid(DEFAULT_CONTRACT)


class TestQualityContractEdge:
    def test_custom_contract_valid(self):
        c = QualityContract(release_hold="HOLD", advisory_only=True, human_review_required=True)
        assert c.is_valid()

    def test_contract_version(self):
        assert DEFAULT_CONTRACT.quality_gate_version


class TestQualityContractAdversarial:
    def test_non_hold_contract_invalid(self):
        c = QualityContract(release_hold="RELEASE")
        assert not c.is_valid()

    def test_non_advisory_contract_invalid(self):
        c = QualityContract(advisory_only=False)
        assert not c.is_valid()

    def test_non_human_review_contract_invalid(self):
        c = QualityContract(human_review_required=False)
        assert not c.is_valid()

    def test_assert_invalid_raises(self):
        c = QualityContract(release_hold="BAD")
        with pytest.raises(ValueError):
            assert_contract_valid(c)

    def test_violations_non_hold(self):
        c = QualityContract(release_hold="BAD")
        violations = c.violations()
        assert any("HOLD" in v for v in violations)

    def test_violations_non_advisory(self):
        c = QualityContract(advisory_only=False)
        violations = c.violations()
        assert any("advisory_only" in v for v in violations)

    def test_forbidden_imports_no_network(self):
        assert "requests" in FORBIDDEN_IMPORTS
        assert "websocket" in FORBIDDEN_IMPORTS
        assert "binance" in FORBIDDEN_IMPORTS

    def test_forbidden_imports_no_runtime(self):
        assert "runtime" in FORBIDDEN_IMPORTS
        assert "planner" in FORBIDDEN_IMPORTS


class TestQualityContractDeterministic:
    def test_contract_deterministic(self):
        c1 = QualityContract()
        c2 = QualityContract()
        assert c1.to_dict() == c2.to_dict()

    def test_dict_order_stable(self):
        d = DEFAULT_CONTRACT.to_dict()
        keys = list(d.keys())
        assert keys == sorted(keys) or keys == list(QualityContract().to_dict().keys())


class TestQualityContractSafetyBoundary:
    def test_release_hold_always_hold(self):
        assert RELEASE_HOLD_VALUE == "HOLD"

    def test_contract_frozen(self):
        with pytest.raises(AttributeError):
            DEFAULT_CONTRACT.release_hold = "BAD"

    def test_safety_flags_complete(self):
        required = {"no_live", "no_submit", "no_exchange", "no_runtime_integration",
                    "no_planner_integration", "no_network"}
        assert required == set(SAFETY_FLAGS.keys())
