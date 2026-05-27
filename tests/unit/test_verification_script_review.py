"""T1347 - Tests for verification script review models."""
from __future__ import annotations

import pytest

from core.verification_script_review import VerificationScriptReview
from core.verification_script_import_policy import VerificationScriptImportPolicy
from core.verification_script_dry_run_proof import VerificationScriptDryRunProof
from core.verification_script_review_verdict import (
    VerificationScriptReviewVerdict,
    VALID_VERDICTS,
    build_verdict,
)
from core.verification_script_promotion_checklist import VerificationScriptPromotionChecklist


class TestVerificationScriptReview:
    def test_create_review(self):
        r = VerificationScriptReview("VR1", "test.py", ("import_check",), "pass")
        assert r.review_id == "VR1"
        assert r.script_name == "test.py"
        assert r.check_count() == 1
        assert r.is_pass()

    def test_immutable(self):
        r = VerificationScriptReview("VR2", "x.py", (), "hold")
        with pytest.raises(AttributeError):
            r.verdict = "pass"  # type: ignore[misc]

    def test_has_check(self):
        r = VerificationScriptReview("VR3", "y.py", ("a", "b"), "fail")
        assert r.has_check("a")
        assert not r.has_check("c")

    def test_verdict_states(self):
        assert VerificationScriptReview("V", "s", (), "pass").is_pass()
        assert VerificationScriptReview("V", "s", (), "hold").is_hold()
        assert VerificationScriptReview("V", "s", (), "fail").is_fail()


class TestVerificationScriptImportPolicy:
    def test_create_policy(self):
        p = VerificationScriptImportPolicy(
            "IP1", ("os", "sys"), ("subprocess",), ("socket",)
        )
        assert p.policy_id == "IP1"
        assert p.allowed_count() == 2
        assert p.forbidden_count() == 1

    def test_immutable(self):
        p = VerificationScriptImportPolicy("IP2", (), (), ())
        with pytest.raises(AttributeError):
            p.policy_id = "X"  # type: ignore[misc]

    def test_is_allowed_forbidden(self):
        p = VerificationScriptImportPolicy("IP3", ("os",), ("subprocess",), ())
        assert p.is_allowed("os")
        assert not p.is_allowed("subprocess")
        assert p.is_forbidden("subprocess")

    def test_validate_import(self):
        p = VerificationScriptImportPolicy("IP4", (), ("rm",), ("socket",))
        assert p.validate_import("os") == "allowed"
        assert p.validate_import("rm") == "forbidden"
        assert p.validate_import("socket") == "high_risk"


class TestVerificationScriptDryRunProof:
    def test_create_proof(self):
        pr = VerificationScriptDryRunProof("DP1", "test.py", "stdout", ("ref1",))
        assert pr.proof_id == "DP1"
        assert pr.is_stdout_proof()
        assert pr.has_evidence()

    def test_immutable(self):
        pr = VerificationScriptDryRunProof("DP2", "x.py", "log", ())
        with pytest.raises(AttributeError):
            pr.proof_type = "file"  # type: ignore[misc]

    def test_proof_types(self):
        assert VerificationScriptDryRunProof("D", "s", "stdout", ()).is_stdout_proof()
        assert VerificationScriptDryRunProof("D", "s", "log", ()).is_log_proof()
        assert VerificationScriptDryRunProof("D", "s", "file", ()).is_file_proof()
        assert VerificationScriptDryRunProof("D", "s", "composite", ()).is_composite()


class TestVerificationScriptReviewVerdict:
    def test_build_pass_verdict(self):
        v = build_verdict("pass", "ok", ())
        assert v.is_pass()
        assert not v.has_failures()

    def test_build_fail_verdict(self):
        v = build_verdict("fail", "bad", ("check1",))
        assert v.is_fail()
        assert v.failure_count() == 1

    def test_pass_with_failures_raises(self):
        with pytest.raises(ValueError, match="pass.*failed checks"):
            build_verdict("pass", "", ("c1",))

    def test_fail_without_failures_raises(self):
        with pytest.raises(ValueError, match="fail.*at least one"):
            build_verdict("fail", "", ())

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValueError, match="Invalid verdict"):
            build_verdict("bogus", "", ())


class TestVerificationScriptPromotionChecklist:
    def test_create_checklist(self):
        c = VerificationScriptPromotionChecklist("CL1", ("a", "b", "c"), True, 2)
        assert c.total_items() == 3
        assert c.remaining() == 1
        assert not c.is_complete()
        assert not c.is_promotable()

    def test_immutable(self):
        c = VerificationScriptPromotionChecklist("CL2", (), True, 0)
        with pytest.raises(AttributeError):
            c.completed_count = 5  # type: ignore[misc]

    def test_complete_checklist(self):
        c = VerificationScriptPromotionChecklist("CL3", ("a",), True, 1)
        assert c.is_complete()
        assert c.is_promotable()
        assert c.completion_ratio() == 1.0
