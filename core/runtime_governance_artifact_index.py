"""Runtime governance artifact index — index of all governance artifacts.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceArtifactEntry:
    """Single artifact index entry."""

    artifact_id: str
    name: str
    path: str
    status: str  # "PRESENT" / "MISSING" / "STALE"


@dataclass(frozen=True)
class RuntimeGovernanceArtifactIndex:
    """Immutable artifact index for runtime governance."""

    title: str
    artifacts: List[RuntimeGovernanceArtifactEntry]
    verdict: str  # "PASS" / "WARN" / "FAIL"
    notes: List[str] = field(default_factory=list)


_DEFAULT_ARTIFACTS: List[Dict[str, str]] = [
    {"artifact_id": "A1", "name": "stack_manifest", "path": "core/runtime_governance_stack_manifest.py", "status": "PRESENT"},
    {"artifact_id": "A2", "name": "regression_packet", "path": "core/runtime_governance_regression_packet.py", "status": "PRESENT"},
    {"artifact_id": "A3", "name": "phase_control_report", "path": "core/runtime_governance_phase_control_report.py", "status": "PRESENT"},
    {"artifact_id": "A4", "name": "integration_risk_register", "path": "core/runtime_governance_integration_risk_register.py", "status": "PRESENT"},
    {"artifact_id": "A5", "name": "artifact_index", "path": "core/runtime_governance_artifact_index.py", "status": "PRESENT"},
    {"artifact_id": "A6", "name": "closeout_checklist", "path": "core/runtime_governance_closeout_checklist.py", "status": "PRESENT"},
    {"artifact_id": "A7", "name": "manual_scope_packet", "path": "core/runtime_governance_manual_scope_packet.py", "status": "PRESENT"},
]


def build_runtime_governance_artifact_index(
    *,
    title: str = "Runtime Governance Artifact Index",
    artifacts: List[RuntimeGovernanceArtifactEntry] | None = None,
    verdict: str | None = None,
    notes: List[str] | None = None,
) -> RuntimeGovernanceArtifactIndex:
    """Build artifact index. Pure. No I/O.

    Defaults produce an index with all artifacts present (PASS).
    """
    if artifacts is None:
        artifacts = [
            RuntimeGovernanceArtifactEntry(**spec)
            for spec in _DEFAULT_ARTIFACTS
        ]

    eff_verdict = verdict if verdict is not None else _compute_verdict(artifacts)

    return RuntimeGovernanceArtifactIndex(
        title=title,
        artifacts=artifacts,
        verdict=eff_verdict,
        notes=list(notes) if notes else [],
    )


def summarize_artifact_index(index: RuntimeGovernanceArtifactIndex) -> Dict[str, Any]:
    """Summarize artifact index counts. Deterministic."""
    by_status: Dict[str, int] = {}
    for a in index.artifacts:
        by_status[a.status] = by_status.get(a.status, 0) + 1

    return {
        "total": len(index.artifacts),
        "by_status": dict(sorted(by_status.items())),
        "verdict": index.verdict,
    }


def artifact_index_to_dict(index: RuntimeGovernanceArtifactIndex) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "title": index.title,
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "name": a.name,
                "path": a.path,
                "status": a.status,
            }
            for a in index.artifacts
        ],
        "verdict": index.verdict,
        "notes": list(index.notes),
    }


def artifact_index_to_markdown(index: RuntimeGovernanceArtifactIndex) -> str:
    """Render as deterministic markdown. No timestamps."""
    lines: List[str] = [f"# {index.title}", ""]
    lines.append(f"**Verdict:** {index.verdict}")
    lines.append("")
    lines.append("| ID | Name | Path | Status |")
    lines.append("|----|------|------|--------|")
    for a in index.artifacts:
        lines.append(f"| {a.artifact_id} | {a.name} | {a.path} | {a.status} |")
    lines.append("")
    if index.notes:
        lines.append("## Notes")
        lines.append("")
        for note in index.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


# ── internal ───────────────────────────────────────────────────────


def _compute_verdict(artifacts: List[RuntimeGovernanceArtifactEntry]) -> str:
    has_missing = any(a.status == "MISSING" for a in artifacts)
    has_stale = any(a.status == "STALE" for a in artifacts)
    if has_missing:
        return "FAIL"
    if has_stale:
        return "WARN"
    return "PASS"
