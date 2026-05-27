from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyStackComponent:
    task_id: str
    name: str
    module_path: str
    test_path: str
    doc_path: str
    status: str  # "PASS"


_COMPONENTS: List[RuntimeGovernanceReadOnlyStackComponent] = [
    RuntimeGovernanceReadOnlyStackComponent(
        task_id="T826",
        name="runtime_governance_contract",
        module_path="core/runtime_governance_contract.py",
        test_path="tests/unit/test_runtime_governance_contract.py",
        doc_path="docs/runtime_governance_contract.md",
        status="PASS",
    ),
    RuntimeGovernanceReadOnlyStackComponent(
        task_id="T827",
        name="runtime_governance_dry_run_adapter",
        module_path="core/runtime_governance_dry_run_adapter.py",
        test_path="tests/unit/test_runtime_governance_dry_run_adapter.py",
        doc_path="docs/runtime_governance_dry_run_adapter.md",
        status="PASS",
    ),
    RuntimeGovernanceReadOnlyStackComponent(
        task_id="T828",
        name="runtime_governance_dry_run_matrix_report",
        module_path="core/runtime_governance_dry_run_matrix_report.py",
        test_path="tests/unit/test_runtime_governance_dry_run_matrix_report.py",
        doc_path="docs/runtime_governance_dry_run_matrix_report.md",
        status="PASS",
    ),
    RuntimeGovernanceReadOnlyStackComponent(
        task_id="T829",
        name="runtime_governance_frozen_boundary_map",
        module_path="core/runtime_governance_frozen_boundary_map.py",
        test_path="tests/unit/test_runtime_governance_frozen_boundary_map.py",
        doc_path="docs/runtime_governance_frozen_boundary_map.md",
        status="PASS",
    ),
    RuntimeGovernanceReadOnlyStackComponent(
        task_id="T830",
        name="runtime_governance_engineering_closeout_bundle",
        module_path="core/runtime_governance_engineering_closeout_bundle.py",
        test_path="tests/unit/test_runtime_governance_engineering_closeout_bundle.py",
        doc_path="docs/runtime_governance_engineering_closeout_bundle.md",
        status="PASS",
    ),
    RuntimeGovernanceReadOnlyStackComponent(
        task_id="T831",
        name="runtime_governance_final_closeout_doc",
        module_path="core/runtime_governance_final_closeout_doc.py",
        test_path="tests/unit/test_runtime_governance_final_closeout_doc.py",
        doc_path="docs/runtime_governance_final_closeout_doc.md",
        status="PASS",
    ),
    RuntimeGovernanceReadOnlyStackComponent(
        task_id="T832",
        name="runtime_governance_final_status_report",
        module_path="core/runtime_governance_final_status_report.py",
        test_path="tests/unit/test_runtime_governance_final_status_report.py",
        doc_path="docs/runtime_governance_final_status_report.md",
        status="PASS",
    ),
    RuntimeGovernanceReadOnlyStackComponent(
        task_id="T833",
        name="runtime_governance_readonly_stack_manifest",
        module_path="core/runtime_governance_readonly_stack_manifest.py",
        test_path="tests/unit/test_runtime_governance_readonly_stack_manifest.py",
        doc_path="docs/runtime_governance_readonly_stack_manifest.md",
        status="PASS",
    ),
]


def build_readonly_stack_manifest() -> List[RuntimeGovernanceReadOnlyStackComponent]:
    """Build manifest for T826-T833. Deterministic."""
    return list(_COMPONENTS)


def readonly_stack_manifest_to_dict(
    manifest: List[RuntimeGovernanceReadOnlyStackComponent],
) -> List[Dict[str, Any]]:
    """Serialize manifest to list of dicts."""
    return [
        {
            "task_id": c.task_id,
            "name": c.name,
            "module_path": c.module_path,
            "test_path": c.test_path,
            "doc_path": c.doc_path,
            "status": c.status,
        }
        for c in manifest
    ]


def readonly_stack_manifest_to_markdown(
    manifest: List[RuntimeGovernanceReadOnlyStackComponent],
) -> str:
    """Deterministic markdown table."""
    lines = [
        "# Runtime Governance Read-Only Stack Manifest",
        "",
        "| Task | Name | Module | Test | Doc | Status |",
        "|------|------|--------|------|-----|--------|",
    ]
    for c in manifest:
        lines.append(
            f"| {c.task_id} | {c.name} | {c.module_path} | {c.test_path} | {c.doc_path} | {c.status} |"
        )
    lines.append("")
    return "\n".join(lines)


def summarize_readonly_stack_manifest(
    manifest: List[RuntimeGovernanceReadOnlyStackComponent],
) -> Dict[str, Any]:
    """Summarize manifest counts."""
    total = len(manifest)
    pass_count = sum(1 for c in manifest if c.status == "PASS")
    fail_count = total - pass_count
    return {
        "total": total,
        "pass": pass_count,
        "fail": fail_count,
        "all_pass": fail_count == 0,
        "task_ids": [c.task_id for c in manifest],
    }
