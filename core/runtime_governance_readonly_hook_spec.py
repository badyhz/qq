from dataclasses import dataclass, field
from typing import Any, Dict, List

FORBIDDEN_SIDE_EFFECTS = [
    "order placement",
    "account mutation",
    "credential access",
    "network call",
    "file write",
    "planner action",
]

ALLOWED_OUTPUTS = [
    "diagnostic summary",
    "guard violation report",
    "state snapshot",
    "rule evaluation result",
    "compliance status",
]

ALLOWED_INPUTS = [
    "current positions",
    "open orders",
    "account balance",
    "risk parameters",
    "market data snapshot",
    "guard definitions",
    "governance rules",
]

FORBIDDEN_INPUTS = [
    "private keys",
    "api secrets",
    "session tokens",
]

REQUIRED_GUARDS = [
    "dry_run_enforced",
    "no_order_submission",
    "no_credential_access",
    "no_network_egress",
    "no_file_mutation",
]


@dataclass(frozen=True)
class RuntimeGovernanceReadOnlyHookSpec:
    hook_id: str
    allowed_inputs: List[str]
    forbidden_inputs: List[str]
    allowed_outputs: List[str]
    forbidden_side_effects: List[str]
    required_guards: List[str]
    status: str
    notes: List[str] = field(default_factory=list)


def build_runtime_governance_readonly_hook_spec() -> RuntimeGovernanceReadOnlyHookSpec:
    """Pure. Deterministic."""
    return RuntimeGovernanceReadOnlyHookSpec(
        hook_id="runtime_governance_readonly_v1",
        allowed_inputs=list(ALLOWED_INPUTS),
        forbidden_inputs=list(FORBIDDEN_INPUTS),
        allowed_outputs=list(ALLOWED_OUTPUTS),
        forbidden_side_effects=list(FORBIDDEN_SIDE_EFFECTS),
        required_guards=list(REQUIRED_GUARDS),
        status="defined",
        notes=["read-only hook — no mutation permitted"],
    )


def readonly_hook_spec_to_dict(spec: RuntimeGovernanceReadOnlyHookSpec) -> Dict[str, Any]:
    """Serialize."""
    return {
        "hook_id": spec.hook_id,
        "allowed_inputs": list(spec.allowed_inputs),
        "forbidden_inputs": list(spec.forbidden_inputs),
        "allowed_outputs": list(spec.allowed_outputs),
        "forbidden_side_effects": list(spec.forbidden_side_effects),
        "required_guards": list(spec.required_guards),
        "status": spec.status,
        "notes": list(spec.notes),
    }


def readonly_hook_spec_to_markdown(spec: RuntimeGovernanceReadOnlyHookSpec) -> str:
    """Deterministic markdown."""
    lines = [
        f"# Runtime Governance Read-Only Hook Spec",
        "",
        f"**Hook ID:** {spec.hook_id}",
        f"**Status:** {spec.status}",
        "",
        "## Allowed Inputs",
        "",
    ]
    for item in spec.allowed_inputs:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Forbidden Inputs")
    lines.append("")
    for item in spec.forbidden_inputs:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Allowed Outputs")
    lines.append("")
    for item in spec.allowed_outputs:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Forbidden Side Effects")
    lines.append("")
    for item in spec.forbidden_side_effects:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Required Guards")
    lines.append("")
    for item in spec.required_guards:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in spec.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)
