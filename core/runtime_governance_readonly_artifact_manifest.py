"""T854: Runtime governance read-only artifact manifest.

Static manifest for T826-T853 artifacts. No I/O, deterministic.
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyArtifact:
    task_id: str
    artifact_type: str  # "core", "test", "doc"
    path: str
    purpose: str


_TASK_NAMES = {
    "T826": "hook_spec",
    "T827": "adapter_contract",
    "T828": "permission_envelope",
    "T829": "sanitized_view_model",
    "T830": "side_effect_declaration",
    "T831": "scenario_catalog",
    "T832": "invariant_checker",
    "T833": "stack_manifest",
    "T834": "scenario_evaluator",
    "T835": "regression_packet",
    "T836": "readiness_score",
    "T837": "blocker_summary",
    "T838": "phase_control_report",
    "T839": "evidence_packet",
    "T840": "transition_checklist",
    "T841": "closeout_bundle",
    "T842": "manual_review_packet",
    "T843": "implementation_boundary_spec",
    "T844": "approval_form",
    "T845": "rollback_plan",
    "T846": "observability_design",
    "T847": "threat_model",
    "T848": "future_task_queue",
    "T849": "engineering_closeout",
    "T850": "final_status_report",
    "T851": "verification_command_plan",
    "T852": "route_recommendation",
    "T853": "final_closeout_doc",
}


def build_readonly_artifact_manifest() -> List[RuntimeGovernanceReadOnlyArtifact]:
    """Build the full static artifact manifest for T826-T853."""
    artifacts: List[RuntimeGovernanceReadOnlyArtifact] = []
    for task_num in range(826, 854):
        tid = f"T{task_num}"
        name = _TASK_NAMES[tid]
        artifacts.append(
            RuntimeGovernanceReadOnlyArtifact(
                task_id=tid,
                artifact_type="core",
                path=f"core/runtime_governance_readonly_{name}.py",
                purpose=f"Core implementation for {name}",
            )
        )
        artifacts.append(
            RuntimeGovernanceReadOnlyArtifact(
                task_id=tid,
                artifact_type="test",
                path=f"tests/unit/test_runtime_governance_readonly_{name}.py",
                purpose=f"Tests for {name}",
            )
        )
        artifacts.append(
            RuntimeGovernanceReadOnlyArtifact(
                task_id=tid,
                artifact_type="doc",
                path=f"docs/runtime_governance_readonly_{name}.md",
                purpose=f"Documentation for {name}",
            )
        )
    return artifacts


def readonly_artifact_manifest_to_dict(
    artifacts: List[RuntimeGovernanceReadOnlyArtifact],
) -> List[Dict]:
    """Convert artifact list to list of dicts."""
    return [
        {
            "task_id": a.task_id,
            "artifact_type": a.artifact_type,
            "path": a.path,
            "purpose": a.purpose,
        }
        for a in artifacts
    ]


def readonly_artifact_manifest_to_markdown(
    artifacts: List[RuntimeGovernanceReadOnlyArtifact],
) -> str:
    """Render artifact manifest as a markdown table."""
    lines = ["# Runtime Governance Read-Only Artifact Manifest", ""]
    lines.append("| Task ID | Type | Path | Purpose |")
    lines.append("|---------|------|------|---------|")
    for a in artifacts:
        lines.append(f"| {a.task_id} | {a.artifact_type} | {a.path} | {a.purpose} |")
    return "\n".join(lines)


def summarize_readonly_artifact_manifest(
    artifacts: List[RuntimeGovernanceReadOnlyArtifact],
) -> Dict:
    """Summarize artifact manifest counts."""
    total = len(artifacts)
    by_type: Dict[str, int] = {}
    by_task: Dict[str, int] = {}
    for a in artifacts:
        by_type[a.artifact_type] = by_type.get(a.artifact_type, 0) + 1
        by_task[a.task_id] = by_task.get(a.task_id, 0) + 1
    return {"total": total, "by_type": by_type, "by_task": by_task}
