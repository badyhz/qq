"""T1346 - Tests for medium operational review models."""
from __future__ import annotations

import pytest

from core.medium_operational_review import MediumOperationalReview
from core.medium_operational_command_policy import MediumOperationalCommandPolicy
from core.medium_operational_artifact_policy import MediumOperationalArtifactPolicy
from core.medium_operational_review_verdict import (
    MediumOperationalReviewVerdict,
    VALID_VERDICTS,
    build_verdict,
)


class TestMediumOperationalReview:
    def test_create_review(self):
        r = MediumOperationalReview(
            review_id="MR1",
            scripts=("s1.py", "s2.py"),
            policies=("p1",),
            verdict="HOLD",
        )
        assert r.review_id == "MR1"
        assert r.script_count() == 2
        assert r.policy_count() == 1

    def test_immutable(self):
        r = MediumOperationalReview(
            review_id="MR2", scripts=(), policies=(), verdict="DENIED"
        )
        with pytest.raises(AttributeError):
            r.verdict = "APPROVED"  # type: ignore[misc]

    def test_script_set(self):
        r = MediumOperationalReview(
            review_id="MR3",
            scripts=("a.py", "b.py", "a.py"),
            policies=(),
            verdict="HOLD",
        )
        assert r.script_set() == frozenset({"a.py", "b.py"})

    def test_is_approved_denied(self):
        approved = MediumOperationalReview("MR4", (), (), "APPROVED")
        denied = MediumOperationalReview("MR5", (), (), "DENIED")
        assert approved.is_approved()
        assert denied.is_denied()
        assert not approved.is_denied()


class TestMediumOperationalCommandPolicy:
    def test_create_policy(self):
        p = MediumOperationalCommandPolicy(
            policy_id="CP1",
            allowed_commands=("ls", "cat"),
            forbidden_commands=("rm",),
            dry_run_only=True,
        )
        assert p.policy_id == "CP1"
        assert p.requires_dry_run()

    def test_immutable(self):
        p = MediumOperationalCommandPolicy("CP2", (), (), False)
        with pytest.raises(AttributeError):
            p.dry_run_only = True  # type: ignore[misc]

    def test_command_allowed_forbidden(self):
        p = MediumOperationalCommandPolicy(
            "CP3", ("ls",), ("rm", "curl"), False
        )
        assert p.is_command_allowed("ls")
        assert not p.is_command_allowed("rm")
        assert p.is_command_forbidden("rm")
        assert not p.is_command_forbidden("ls")


class TestMediumOperationalArtifactPolicy:
    def test_create_policy(self):
        p = MediumOperationalArtifactPolicy(
            policy_id="AP1",
            allowed_write_paths=("logs/",),
            forbidden_write_paths=("core/",),
        )
        assert p.policy_id == "AP1"

    def test_immutable(self):
        p = MediumOperationalArtifactPolicy("AP2", (), ())
        with pytest.raises(AttributeError):
            p.policy_id = "X"  # type: ignore[misc]


class TestMediumOperationalReviewVerdict:
    def test_build_valid_verdict(self):
        v = build_verdict("HOLD", "waiting", ())
        assert v.verdict == "HOLD"
        assert v.is_hold()

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValueError, match="Invalid verdict"):
            build_verdict("BOGUS", "", ())

    def test_approved_with_violations_raises(self):
        with pytest.raises(ValueError, match="Cannot approve with violations"):
            build_verdict("APPROVED", "", ("v1",))

    def test_approved_without_violations(self):
        v = build_verdict("APPROVED", "all clear", ())
        assert v.is_approved()
        assert not v.has_violations()
