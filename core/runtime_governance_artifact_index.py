"""Runtime governance artifact index — static index of T794-T818 artifacts.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceArtifact:
    """Single artifact in the index."""
    artifact_id: str
    task_id: str
    artifact_type: str  # "core", "test", "doc"
    path: str
    purpose: str


_TASK_MODULE_MAP = {
    "T794": "runtime_governance_contract",
    "T795": "runtime_governance_dry_run_adapter",
    "T796": "runtime_governance_audit_event",
    "T797": "runtime_governance_preflight_packet",
    "T798": "runtime_governance_scenario_catalog",
    "T799": "runtime_governance_preflight_renderer",
    "T800": "runtime_governance_schema_checker",
    "T801": "runtime_governance_reason_codes",
    "T802": "runtime_governance_policy_matrix",
    "T803": "runtime_governance_invariant_checker",
    "T804": "runtime_governance_sample_factory",
    "T805": "runtime_governance_stack_manifest",
    "T806": "runtime_governance_scenario_batch_evaluator",
    "T807": "runtime_governance_regression_packet",
    "T808": "runtime_governance_readiness_score",
    "T809": "runtime_governance_blocker_summary",
    "T810": "runtime_governance_transition_checklist",
    "T811": "runtime_governance_dry_run_matrix_report",
    "T812": "runtime_governance_no_submit_evidence_packet",
    "T813": "runtime_governance_phase_control_report",
    "T814": "runtime_governance_manual_scope_packet",
    "T815": "runtime_governance_integration_risk_register",
    "T816": "runtime_governance_approval_gate_spec",
    "T817": "runtime_governance_frozen_boundary_map",
    "T818": "runtime_governance_future_task_planner",
}


def build_runtime_governance_artifact_index() -> List[RuntimeGovernanceArtifact]:
    """Build static artifact index for T794-T818. Deterministic."""
    artifacts: List[RuntimeGovernanceArtifact] = []
    for task_id in sorted(_TASK_MODULE_MAP):
        module = _TASK_MODULE_MAP[task_id]
        artifacts.append(RuntimeGovernanceArtifact(
            artifact_id=f"{task_id}_core",
            task_id=task_id,
            artifact_type="core",
            path=f"core/{module}.py",
            purpose=f"{module} implementation",
        ))
        artifacts.append(RuntimeGovernanceArtifact(
            artifact_id=f"{task_id}_test",
            task_id=task_id,
            artifact_type="test",
            path=f"tests/unit/test_{module}.py",
            purpose=f"{module} tests",
        ))
        artifacts.append(RuntimeGovernanceArtifact(
            artifact_id=f"{task_id}_doc",
            task_id=task_id,
            artifact_type="doc",
            path=f"docs/{module}.md",
            purpose=f"{module} documentation",
        ))
    return artifacts


def artifact_index_to_dict(artifacts: List[RuntimeGovernanceArtifact]) -> List[Dict[str, Any]]:
    """Serialize artifact index to list of dicts."""
    return [
        {
            "artifact_id": a.artifact_id,
            "task_id": a.task_id,
            "artifact_type": a.artifact_type,
            "path": a.path,
            "purpose": a.purpose,
        }
        for a in artifacts
    ]


def artifact_index_to_markdown(artifacts: List[RuntimeGovernanceArtifact]) -> str:
    """Render artifact index as deterministic markdown."""
    lines = [
        "# Runtime Governance Artifact Index",
        "",
        "| artifact_id | task_id | type | path |",
        "|-------------|------|------|------|",
    ]
    for a in artifacts:
        lines.append(f"| {a.artifact_id} | {a.task_id} | {a.artifact_type} | {a.path} |")
    lines.append("")
    return "\n".join(lines)


def summarize_artifact_index(artifacts: List[RuntimeGovernanceArtifact]) -> Dict[str, Any]:
    """Summarize artifact index. Deterministic."""
    by_type: Dict[str, int] = {}
    artifacts_per_task: Dict[str, int] = {}
    for a in artifacts:
        by_type[a.artifact_type] = by_type.get(a.artifact_type, 0) + 1
        artifacts_per_task[a.task_id] = artifacts_per_task.get(a.task_id, 0) + 1
    return {
        "total": len(artifacts),
        "tasks": len(artifacts_per_task),
        "by_type": dict(sorted(by_type.items())),
        "artifacts_per_task": dict(sorted(artifacts_per_task.items())),
    }
