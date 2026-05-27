"""Pure spec for future manual approval gate."""
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceApprovalGateSpec:
    gate_id: str
    required_inputs: List[str]
    required_evidence: List[str]
    forbidden_conditions: List[str]
    approval_modes: List[str]
    notes: str


def build_runtime_governance_approval_gate_spec() -> RuntimeGovernanceApprovalGateSpec:
    return RuntimeGovernanceApprovalGateSpec(
        gate_id="runtime_governance_manual_gate",
        required_inputs=["preflight_packet", "regression_packet", "phase_control_report"],
        required_evidence=["no_submit_evidence", "readiness_score", "blocker_summary"],
        forbidden_conditions=["any_blocker_action_BLOCK", "no_submit_evidence_FAIL", "readiness_grade_F"],
        approval_modes=["manual_review_only", "dry_run_only", "testnet_simulated_only"],
        notes="No live approval mode. Human must explicitly authorize.",
    )


def approval_gate_spec_to_dict(spec: RuntimeGovernanceApprovalGateSpec) -> Dict:
    return {
        "gate_id": spec.gate_id,
        "required_inputs": list(spec.required_inputs),
        "required_evidence": list(spec.required_evidence),
        "forbidden_conditions": list(spec.forbidden_conditions),
        "approval_modes": list(spec.approval_modes),
        "notes": spec.notes,
    }


def approval_gate_spec_to_markdown(spec: RuntimeGovernanceApprovalGateSpec) -> str:
    lines = [
        f"# {spec.gate_id}",
        "",
        "## Required Inputs",
        "",
        *(f"- {i}" for i in spec.required_inputs),
        "",
        "## Required Evidence",
        "",
        *(f"- {e}" for e in spec.required_evidence),
        "",
        "## Forbidden Conditions",
        "",
        *(f"- {c}" for c in spec.forbidden_conditions),
        "",
        "## Approval Modes",
        "",
        *(f"- {m}" for m in spec.approval_modes),
        "",
        "## Notes",
        "",
        spec.notes,
    ]
    return "\n".join(lines) + "\n"
