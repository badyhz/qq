from __future__ import annotations

import pytest

from core.medium_risk_review import MediumRiskReview
from core.medium_risk_script_kind import MediumRiskScriptKind, validate_kind
from core.medium_risk_review_verdict import MediumRiskReviewVerdict, build_verdict


class TestMediumRiskReview:
    def test_create_review_frozen(self) -> None:
        r = MediumRiskReview(
            review_id="MR-001",
            scripts=("s1.py",),
            policies=("p1",),
            verdict="PASS",
        )
        assert r.review_id == "MR-001"
        with pytest.raises(AttributeError):
            r.review_id = "X"  # type: ignore[misc]

    def test_scripts_tuple(self) -> None:
        r = MediumRiskReview(
            review_id="MR-002",
            scripts=("a.py", "b.py"),
            policies=(),
            verdict="FAIL",
        )
        assert len(r.scripts) == 2

    def test_policies_tuple(self) -> None:
        r = MediumRiskReview(
            review_id="MR-003",
            scripts=(),
            policies=("policy-a", "policy-b", "policy-c"),
            verdict="HOLD",
        )
        assert len(r.policies) == 3


class TestMediumRiskScriptKind:
    def test_valid_kinds(self) -> None:
        for kind in ("OPERATIONAL", "VERIFICATION", "SHADOW", "TESTNET", "REMEDIATION"):
            result = validate_kind(kind)
            assert result == kind

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_kind("UNKNOWN")

    def test_frozen_dataclass_values(self) -> None:
        k = MediumRiskScriptKind()
        assert k.OPERATIONAL == "OPERATIONAL"
        assert k.VERIFICATION == "VERIFICATION"
        assert k.SHADOW == "SHADOW"


class TestMediumRiskReviewVerdict:
    def test_build_verdict_pass(self) -> None:
        v = build_verdict("PASS")
        assert v.verdict == "PASS"
        assert len(v.issues) == 0

    def test_build_verdict_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            build_verdict("INVALID")

    def test_verdict_frozen(self) -> None:
        v = build_verdict("FAIL", issues=("i1",), notes=("n1",))
        assert v.verdict == "FAIL"
        assert v.issues == ("i1",)
        with pytest.raises(AttributeError):
            v.verdict = "X"  # type: ignore[misc]
