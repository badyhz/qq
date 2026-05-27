"""Tests for runtime governance approval gate spec."""
import pytest

from core.runtime_governance_approval_gate_spec import (
    RuntimeGovernanceApprovalGateSpec,
    approval_gate_spec_to_dict,
    approval_gate_spec_to_markdown,
    build_runtime_governance_approval_gate_spec,
)


class TestBuildSpec:
    def test_returns_frozen_dataclass(self):
        spec = build_runtime_governance_approval_gate_spec()
        assert isinstance(spec, RuntimeGovernanceApprovalGateSpec)
        with pytest.raises(AttributeError):
            spec.gate_id = "x"

    def test_gate_id(self):
        spec = build_runtime_governance_approval_gate_spec()
        assert spec.gate_id == "runtime_governance_manual_gate"

    def test_required_inputs(self):
        spec = build_runtime_governance_approval_gate_spec()
        assert spec.required_inputs == ["preflight_packet", "regression_packet", "phase_control_report"]

    def test_required_evidence(self):
        spec = build_runtime_governance_approval_gate_spec()
        assert spec.required_evidence == ["no_submit_evidence", "readiness_score", "blocker_summary"]

    def test_forbidden_conditions(self):
        spec = build_runtime_governance_approval_gate_spec()
        assert spec.forbidden_conditions == [
            "any_blocker_action_BLOCK",
            "no_submit_evidence_FAIL",
            "readiness_grade_F",
        ]

    def test_approval_modes_no_live(self):
        spec = build_runtime_governance_approval_gate_spec()
        assert "live" not in " ".join(spec.approval_modes)
        assert spec.approval_modes == ["manual_review_only", "dry_run_only", "testnet_simulated_only"]

    def test_notes(self):
        spec = build_runtime_governance_approval_gate_spec()
        assert "Human must explicitly authorize" in spec.notes


class TestToDict:
    def test_keys(self):
        spec = build_runtime_governance_approval_gate_spec()
        d = approval_gate_spec_to_dict(spec)
        assert set(d.keys()) == {"gate_id", "required_inputs", "required_evidence", "forbidden_conditions", "approval_modes", "notes"}

    def test_values_match(self):
        spec = build_runtime_governance_approval_gate_spec()
        d = approval_gate_spec_to_dict(spec)
        assert d["gate_id"] == spec.gate_id
        assert d["required_inputs"] == spec.required_inputs
        assert d["required_evidence"] == spec.required_evidence
        assert d["forbidden_conditions"] == spec.forbidden_conditions
        assert d["approval_modes"] == spec.approval_modes
        assert d["notes"] == spec.notes

    def test_returns_new_lists(self):
        spec = build_runtime_governance_approval_gate_spec()
        d = approval_gate_spec_to_dict(spec)
        d["required_inputs"].append("x")
        assert len(spec.required_inputs) == 3


class TestToMarkdown:
    def test_contains_gate_id_heading(self):
        spec = build_runtime_governance_approval_gate_spec()
        md = approval_gate_spec_to_markdown(spec)
        assert "# runtime_governance_manual_gate" in md

    def test_contains_all_sections(self):
        spec = build_runtime_governance_approval_gate_spec()
        md = approval_gate_spec_to_markdown(spec)
        for section in ["Required Inputs", "Required Evidence", "Forbidden Conditions", "Approval Modes", "Notes"]:
            assert f"## {section}" in md

    def test_contains_required_inputs(self):
        spec = build_runtime_governance_approval_gate_spec()
        md = approval_gate_spec_to_markdown(spec)
        for item in spec.required_inputs:
            assert f"- {item}" in md

    def test_contains_notes(self):
        spec = build_runtime_governance_approval_gate_spec()
        md = approval_gate_spec_to_markdown(spec)
        assert spec.notes in md

    def test_ends_with_newline(self):
        spec = build_runtime_governance_approval_gate_spec()
        md = approval_gate_spec_to_markdown(spec)
        assert md.endswith("\n")
