"""Runtime governance stack manifest — pure data model.

Describes expected modules/tests/docs as data only.
No repo scanning. No file I/O. No network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceStackComponent:
    task_id: str
    name: str
    module_path: str
    test_path: str
    doc_path: str
    status: str  # "PASS", "WARN", "FAIL"
    notes: str = ""


@dataclass(frozen=True)
class RuntimeGovernanceStackManifest:
    title: str
    components: List[RuntimeGovernanceStackComponent]
    total_components: int
    completed_components: int
    verdict: str


# ── expected components (stable order) ─────────────────────────────

_EXPECTED_COMPONENTS: List[Dict[str, str]] = [
    {
        "task_id": "T794",
        "name": "runtime_governance_contract",
        "module_path": "core/runtime_governance_contract.py",
        "test_path": "tests/unit/test_runtime_governance_contract.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T795",
        "name": "runtime_governance_dry_run_adapter",
        "module_path": "core/runtime_governance_dry_run_adapter.py",
        "test_path": "tests/unit/test_runtime_governance_dry_run_adapter.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T796",
        "name": "runtime_governance_audit_event",
        "module_path": "core/runtime_governance_audit_event.py",
        "test_path": "tests/unit/test_runtime_governance_audit_event.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T797",
        "name": "runtime_governance_preflight_packet",
        "module_path": "core/runtime_governance_preflight_packet.py",
        "test_path": "tests/unit/test_runtime_governance_preflight_packet.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T798",
        "name": "runtime_governance_scenario_catalog",
        "module_path": "core/runtime_governance_scenario_catalog.py",
        "test_path": "tests/unit/test_runtime_governance_scenario_catalog.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T799",
        "name": "runtime_governance_preflight_renderer",
        "module_path": "core/runtime_governance_preflight_renderer.py",
        "test_path": "tests/unit/test_runtime_governance_preflight_renderer.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T800",
        "name": "runtime_governance_schema_checker",
        "module_path": "core/runtime_governance_schema_checker.py",
        "test_path": "tests/unit/test_runtime_governance_schema_checker.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T801",
        "name": "runtime_governance_reason_codes",
        "module_path": "core/runtime_governance_reason_codes.py",
        "test_path": "tests/unit/test_runtime_governance_reason_codes.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T802",
        "name": "runtime_governance_policy_matrix",
        "module_path": "core/runtime_governance_policy_matrix.py",
        "test_path": "tests/unit/test_runtime_governance_policy_matrix.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T803",
        "name": "runtime_governance_invariant_checker",
        "module_path": "core/runtime_governance_invariant_checker.py",
        "test_path": "tests/unit/test_runtime_governance_invariant_checker.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T804",
        "name": "runtime_governance_sample_factory",
        "module_path": "core/runtime_governance_sample_factory.py",
        "test_path": "tests/unit/test_runtime_governance_sample_factory.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
    {
        "task_id": "T805",
        "name": "runtime_governance_stack_manifest",
        "module_path": "core/runtime_governance_stack_manifest.py",
        "test_path": "tests/unit/test_runtime_governance_stack_manifest.py",
        "doc_path": "docs/runtime_governance_stack_manifest.md",
        "status": "PASS",
    },
]


# ── pure functions ─────────────────────────────────────────────────


def build_expected_runtime_governance_stack_manifest(
    overrides: Dict[str, str] | None = None,
) -> RuntimeGovernanceStackManifest:
    """Build manifest with expected runtime governance stack components.

    ``overrides`` maps task_id -> status string ("PASS", "WARN", "FAIL").
    Defaults to "PASS" for all expected components.
    Deterministic. No I/O.
    """
    if overrides is None:
        overrides = {}

    components: List[RuntimeGovernanceStackComponent] = []
    for spec in _EXPECTED_COMPONENTS:
        tid = spec["task_id"]
        status = overrides.get(tid, spec["status"])
        components.append(
            RuntimeGovernanceStackComponent(
                task_id=tid,
                name=spec["name"],
                module_path=spec["module_path"],
                test_path=spec["test_path"],
                doc_path=spec["doc_path"],
                status=status,
            )
        )

    completed = sum(1 for c in components if c.status == "PASS")
    verdict = _compute_verdict(components)

    return RuntimeGovernanceStackManifest(
        title="Runtime Governance Stack Manifest",
        components=components,
        total_components=len(components),
        completed_components=completed,
        verdict=verdict,
    )


def runtime_manifest_to_dict(manifest: RuntimeGovernanceStackManifest) -> Dict[str, Any]:
    """Serialize manifest to a plain dict. Deterministic."""
    return {
        "title": manifest.title,
        "components": [
            {
                "task_id": c.task_id,
                "name": c.name,
                "module_path": c.module_path,
                "test_path": c.test_path,
                "doc_path": c.doc_path,
                "status": c.status,
                "notes": c.notes,
            }
            for c in manifest.components
        ],
        "total_components": manifest.total_components,
        "completed_components": manifest.completed_components,
        "verdict": manifest.verdict,
    }


def runtime_manifest_to_markdown(manifest: RuntimeGovernanceStackManifest) -> str:
    """Render manifest as deterministic markdown. Stable ordering, no timestamps."""
    lines: List[str] = []

    lines.append(f"# {manifest.title}")
    lines.append("")
    lines.append(f"**Verdict:** {manifest.verdict}")
    lines.append(
        f"**Components:** {manifest.completed_components}/{manifest.total_components} PASS"
    )
    lines.append("")

    lines.append("| Task | Name | Module | Status |")
    lines.append("|------|------|--------|--------|")
    for c in manifest.components:
        lines.append(f"| {c.task_id} | {c.name} | {c.module_path} | {c.status} |")
    lines.append("")

    return "\n".join(lines)


def summarize_runtime_manifest(manifest: RuntimeGovernanceStackManifest) -> Dict[str, Any]:
    """Summarize manifest counts. Deterministic."""
    by_status: Dict[str, int] = {}
    for c in manifest.components:
        by_status[c.status] = by_status.get(c.status, 0) + 1

    return {
        "total": manifest.total_components,
        "completed": manifest.completed_components,
        "by_status": dict(sorted(by_status.items())),
        "verdict": manifest.verdict,
    }


# ── internal ───────────────────────────────────────────────────────


def _compute_verdict(components: List[RuntimeGovernanceStackComponent]) -> str:
    has_fail = any(c.status == "FAIL" for c in components)
    has_warn = any(c.status == "WARN" for c in components)
    if has_fail:
        return "FAIL"
    if has_warn:
        return "WARN"
    return "PASS"
