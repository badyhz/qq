"""T1448 - Tests for FrozenFileRiskRequirement and FrozenRiskRequirementChecklist."""
from __future__ import annotations

import pytest


class TestFrozenFileRiskRequirement:
    """Tests for FrozenFileRiskRequirement (T1443)."""

    def test_create_requirement_frozen(self):
        from core.frozen_file_risk_requirement import build_risk_requirement

        req = build_risk_requirement(
            requirement_id="RR-001",
            risk_class="HIGH",
            requirement_name="Static analysis",
            required_evidence=("report",),
            mandatory=True,
            human_approval_needed=True,
        )
        assert req.requirement_id == "RR-001"
        assert req.risk_class == "HIGH"
        assert req.mandatory is True
        assert req.human_approval_needed is True

    def test_requirement_immutability(self):
        from core.frozen_file_risk_requirement import build_risk_requirement

        req = build_risk_requirement(requirement_id="RR-002", risk_class="MEDIUM", requirement_name="test")
        with pytest.raises(AttributeError):
            req.mandatory = False  # type: ignore[misc]

    def test_requirement_invalid_risk_class(self):
        from core.frozen_file_risk_requirement import build_risk_requirement

        with pytest.raises(ValueError, match="Invalid risk_class"):
            build_risk_requirement(requirement_id="RR-003", risk_class="LOW", requirement_name="bad")

    def test_requirement_defaults(self):
        from core.frozen_file_risk_requirement import build_risk_requirement

        req = build_risk_requirement(requirement_id="RR-004", risk_class="HIGH", requirement_name="x")
        assert req.required_evidence == ()
        assert req.mandatory is True
        assert req.human_approval_needed is False


class TestFrozenRiskRequirementChecklist:
    """Tests for FrozenRiskRequirementChecklist (T1444)."""

    def test_create_checklist_frozen(self):
        from core.frozen_file_risk_requirement import build_risk_requirement
        from core.frozen_risk_requirement_checklist import build_checklist

        req = build_risk_requirement(requirement_id="RR-01", risk_class="HIGH", requirement_name="a")
        cl = build_checklist(
            checklist_id="CL-001",
            file_path="core/x.py",
            risk_class="HIGH",
            requirements=(req,),
        )
        assert cl.checklist_id == "CL-001"
        assert cl.total_count == 1
        assert cl.completed_count == 0

    def test_checklist_immutability(self):
        from core.frozen_risk_requirement_checklist import build_checklist

        cl = build_checklist(checklist_id="CL-002", file_path="core/x.py", risk_class="HIGH")
        with pytest.raises(AttributeError):
            cl.completed_count = 1  # type: ignore[misc]

    def test_checklist_not_complete_when_zero(self):
        from core.frozen_risk_requirement_checklist import build_checklist

        cl = build_checklist(checklist_id="CL-003", file_path="core/x.py", risk_class="MEDIUM")
        assert cl.is_complete is False

    def test_checklist_complete_when_fulfilled(self):
        from core.frozen_file_risk_requirement import build_risk_requirement
        from core.frozen_risk_requirement_checklist import build_checklist

        req = build_risk_requirement(requirement_id="RR-10", risk_class="HIGH", requirement_name="x")
        cl = build_checklist(
            checklist_id="CL-004",
            file_path="core/x.py",
            risk_class="HIGH",
            requirements=(req,),
            completed_count=1,
        )
        assert cl.is_complete is True

    def test_checklist_high_vs_medium_requirements_differ(self):
        from core.frozen_review_packet_generator import generate_review_packet

        high = generate_review_packet("core/live_runner.py", "HIGH")
        medium = generate_review_packet("scripts/run_foo.py", "MEDIUM")
        assert len(high.evidence_requirements) != len(medium.evidence_requirements)

    def test_checklist_mandatory_flags(self):
        from core.frozen_file_risk_requirement import build_risk_requirement

        req_mand = build_risk_requirement(requirement_id="RR-20", risk_class="HIGH", requirement_name="x", mandatory=True)
        req_opt = build_risk_requirement(requirement_id="RR-21", risk_class="MEDIUM", requirement_name="y", mandatory=False)
        assert req_mand.mandatory is True
        assert req_opt.mandatory is False

    def test_checklist_human_approval_flags(self):
        from core.frozen_file_risk_requirement import build_risk_requirement

        req = build_risk_requirement(
            requirement_id="RR-30",
            risk_class="HIGH",
            requirement_name="z",
            human_approval_needed=True,
        )
        assert req.human_approval_needed is True
