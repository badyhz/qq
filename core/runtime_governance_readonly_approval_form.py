"""Runtime governance read-only approval form.

Static manual approval form data. No approval execution.
Pure, deterministic, no I/O, no timestamps, no random.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyApprovalForm:
    """Frozen approval form for read-only governance layer."""

    form_id: str
    required_checks: List[str]
    approval_statement: str
    explicit_non_authorizations: List[str]
    signer_role: str
    notes: List[str]


def build_readonly_approval_form() -> RuntimeGovernanceReadOnlyApprovalForm:
    """Build the default read-only approval form."""
    return RuntimeGovernanceReadOnlyApprovalForm(
        form_id="READONLY-APPROVAL-001",
        required_checks=[
            "permission envelope validated",
            "invariant checker passed",
            "no dangerous side effects",
            "scenario catalog reviewed",
            "regression packet passed",
            "readiness score >= B",
            "blocker summary clean",
            "evidence packet verified",
            "transition checklist complete",
        ],
        approval_statement=(
            "I approve the read-only design for the runtime governance layer. "
            "This approval is limited to read-only operations only."
        ),
        explicit_non_authorizations=[
            "Does not authorize live trading",
            "Does not authorize order placement",
            "Does not authorize secret access",
            "Does not authorize exchange connection",
            "Does not authorize planner autonomous mode",
        ],
        signer_role="Human Reviewer",
        notes=["This form must be signed before any implementation begins."],
    )


def readonly_approval_form_to_dict(
    form: RuntimeGovernanceReadOnlyApprovalForm,
) -> Dict:
    """Convert approval form to dictionary."""
    return {
        "form_id": form.form_id,
        "required_checks": list(form.required_checks),
        "approval_statement": form.approval_statement,
        "explicit_non_authorizations": list(form.explicit_non_authorizations),
        "signer_role": form.signer_role,
        "notes": list(form.notes),
    }


def readonly_approval_form_to_markdown(
    form: RuntimeGovernanceReadOnlyApprovalForm,
) -> str:
    """Convert approval form to markdown string."""
    lines = [
        f"# {form.form_id}",
        "",
        "## Approval Statement",
        "",
        form.approval_statement,
        "",
        "## Required Checks",
        "",
    ]
    for check in form.required_checks:
        lines.append(f"- [ ] {check}")
    lines += [
        "",
        "## Explicit Non-Authorizations",
        "",
    ]
    for na in form.explicit_non_authorizations:
        lines.append(f"- **{na}**")
    lines += [
        "",
        "## Signer Role",
        "",
        form.signer_role,
        "",
        "## Notes",
        "",
    ]
    for note in form.notes:
        lines.append(f"- {note}")
    return "\n".join(lines)
