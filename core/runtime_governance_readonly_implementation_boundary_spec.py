"""T843: Runtime governance read-only implementation boundary spec.

Pure spec. No implementation. No I/O. No timestamps. No random.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyImplementationBoundary:
    boundary_id: str
    allowed_file_pattern: str
    forbidden_file_pattern: str
    allowed_operation: str
    forbidden_operation: str
    notes: List[str]


def build_readonly_implementation_boundary_spec() -> List[RuntimeGovernanceReadOnlyImplementationBoundary]:
    """Build the canonical read-only implementation boundary spec."""
    return [
        RuntimeGovernanceReadOnlyImplementationBoundary(
            boundary_id="core_modules",
            allowed_file_pattern="core/runtime_governance_readonly_*.py",
            forbidden_file_pattern="core/live_runner.py",
            allowed_operation="pure function",
            forbidden_operation="I/O",
            notes=["Core modules must be pure functions with no side effects"],
        ),
        RuntimeGovernanceReadOnlyImplementationBoundary(
            boundary_id="test_modules",
            allowed_file_pattern="tests/unit/test_runtime_governance_readonly_*.py",
            forbidden_file_pattern="tests/integration/*",
            allowed_operation="assert",
            forbidden_operation="network",
            notes=["Tests must be unit-only, no network access"],
        ),
        RuntimeGovernanceReadOnlyImplementationBoundary(
            boundary_id="docs",
            allowed_file_pattern="docs/runtime_governance_readonly_*.md",
            forbidden_file_pattern="docs/live_*",
            allowed_operation="documentation",
            forbidden_operation="secrets",
            notes=["Documentation must not contain secrets or live config"],
        ),
        RuntimeGovernanceReadOnlyImplementationBoundary(
            boundary_id="config",
            allowed_file_pattern="config.yaml",
            forbidden_file_pattern=".env",
            allowed_operation="read",
            forbidden_operation="write",
            notes=["Config is read-only at runtime, never written"],
        ),
        RuntimeGovernanceReadOnlyImplementationBoundary(
            boundary_id="scripts",
            allowed_file_pattern="scripts/readonly_*.py",
            forbidden_file_pattern="scripts/live_*.py",
            allowed_operation="dry-run",
            forbidden_operation="submit",
            notes=["Scripts must be dry-run only, never submit real orders"],
        ),
    ]


def readonly_boundary_spec_to_dict(
    boundaries: List[RuntimeGovernanceReadOnlyImplementationBoundary],
) -> List[Dict]:
    """Convert boundary spec to list of dicts."""
    return [
        {
            "boundary_id": b.boundary_id,
            "allowed_file_pattern": b.allowed_file_pattern,
            "forbidden_file_pattern": b.forbidden_file_pattern,
            "allowed_operation": b.allowed_operation,
            "forbidden_operation": b.forbidden_operation,
            "notes": list(b.notes),
        }
        for b in boundaries
    ]


def readonly_boundary_spec_to_markdown(
    boundaries: List[RuntimeGovernanceReadOnlyImplementationBoundary],
) -> str:
    """Convert boundary spec to markdown table."""
    lines = [
        "# Runtime Governance Read-Only Implementation Boundary Spec",
        "",
        "| boundary_id | allowed_file_pattern | forbidden_file_pattern | allowed_operation | forbidden_operation | notes |",
        "|---|---|---|---|---|---|",
    ]
    for b in boundaries:
        notes_str = "; ".join(b.notes)
        lines.append(
            f"| {b.boundary_id} | {b.allowed_file_pattern} | {b.forbidden_file_pattern} "
            f"| {b.allowed_operation} | {b.forbidden_operation} | {notes_str} |"
        )
    lines.append("")
    return "\n".join(lines)
