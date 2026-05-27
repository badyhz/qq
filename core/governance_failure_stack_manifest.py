"""Governance failure stack manifest — pure data model.

Describes expected modules/tests/docs as data only.
No repo scanning. No file I/O. No network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class ComponentStatus(Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"


@dataclass(frozen=True)
class GovernanceStackComponent:
    task_id: str
    name: str
    module_path: str
    test_path: str
    doc_path: str
    status: ComponentStatus
    notes: str = ""


@dataclass(frozen=True)
class GovernanceStackManifest:
    title: str
    components: List[GovernanceStackComponent]
    total_components: int
    completed_components: int
    missing_components: int
    verdict: str


# ── expected components (stable order) ─────────────────────────────


_EXPECTED_COMPONENTS: List[Dict[str, str]] = [
    {
        "task_id": "T786",
        "name": "taxonomy",
        "module_path": "core/governance_failure_taxonomy.py",
        "test_path": "tests/unit/test_governance_failure_taxonomy.py",
        "doc_path": "docs/governance_failure_taxonomy.md",
    },
    {
        "task_id": "T787",
        "name": "report",
        "module_path": "core/governance_failure_report.py",
        "test_path": "tests/unit/test_governance_failure_report.py",
        "doc_path": "docs/governance_failure_report.md",
    },
    {
        "task_id": "T788",
        "name": "snapshot",
        "module_path": "core/governance_failure_snapshot.py",
        "test_path": "tests/unit/test_governance_failure_snapshot.py",
        "doc_path": "docs/governance_failure_reporting_stack.md",
    },
    {
        "task_id": "T789",
        "name": "regression_packet",
        "module_path": "core/governance_failure_regression_packet.py",
        "test_path": "tests/unit/test_governance_failure_regression_packet.py",
        "doc_path": "docs/governance_failure_reporting_stack.md",
    },
]


# ── pure functions ─────────────────────────────────────────────────


def build_expected_governance_stack_manifest(
    statuses: Dict[str, ComponentStatus] | None = None,
) -> GovernanceStackManifest:
    """Build manifest with expected governance stack components.

    ``statuses`` maps task_id -> ComponentStatus.
    Defaults to COMPLETE for all expected components.
    Deterministic. No I/O.
    """
    if statuses is None:
        statuses = {}

    components: List[GovernanceStackComponent] = []
    for spec in _EXPECTED_COMPONENTS:
        tid = spec["task_id"]
        status = statuses.get(tid, ComponentStatus.COMPLETE)
        components.append(
            GovernanceStackComponent(
                task_id=tid,
                name=spec["name"],
                module_path=spec["module_path"],
                test_path=spec["test_path"],
                doc_path=spec["doc_path"],
                status=status,
            )
        )

    completed = sum(1 for c in components if c.status == ComponentStatus.COMPLETE)
    missing = sum(1 for c in components if c.status == ComponentStatus.MISSING)
    verdict = _compute_manifest_verdict(components)

    return GovernanceStackManifest(
        title="Governance Failure Stack Manifest",
        components=components,
        total_components=len(components),
        completed_components=completed,
        missing_components=missing,
        verdict=verdict,
    )


def manifest_to_dict(manifest: GovernanceStackManifest) -> Dict[str, Any]:
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
                "status": c.status.value,
                "notes": c.notes,
            }
            for c in manifest.components
        ],
        "total_components": manifest.total_components,
        "completed_components": manifest.completed_components,
        "missing_components": manifest.missing_components,
        "verdict": manifest.verdict,
    }


def manifest_to_markdown(manifest: GovernanceStackManifest) -> str:
    """Render manifest as deterministic markdown. Stable ordering, no timestamps."""
    lines: List[str] = []

    lines.append(f"# {manifest.title}")
    lines.append("")
    lines.append(f"**Verdict:** {manifest.verdict}")
    lines.append(
        f"**Components:** {manifest.completed_components}/{manifest.total_components} complete"
    )
    lines.append(f"**Missing:** {manifest.missing_components}")
    lines.append("")

    lines.append("| Task | Name | Module | Status |")
    lines.append("|------|------|--------|--------|")
    for c in manifest.components:
        lines.append(f"| {c.task_id} | {c.name} | {c.module_path} | {c.status.value} |")
    lines.append("")

    return "\n".join(lines)


def summarize_manifest(manifest: GovernanceStackManifest) -> Dict[str, Any]:
    """Summarize manifest counts. Deterministic."""
    by_status: Dict[str, int] = {}
    for c in manifest.components:
        s = c.status.value
        by_status[s] = by_status.get(s, 0) + 1

    return {
        "total": manifest.total_components,
        "completed": manifest.completed_components,
        "missing": manifest.missing_components,
        "by_status": dict(sorted(by_status.items())),
        "verdict": manifest.verdict,
    }


# ── internal ───────────────────────────────────────────────────────


def _compute_manifest_verdict(components: List[GovernanceStackComponent]) -> str:
    has_missing = any(c.status == ComponentStatus.MISSING for c in components)
    has_partial = any(c.status == ComponentStatus.PARTIAL for c in components)
    if has_missing:
        return "FAIL"
    if has_partial:
        return "WARN"
    return "PASS"
