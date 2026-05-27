"""T828 — Permission envelope for runtime governance."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class RuntimeGovernancePermissionEnvelope:
    allow_read: bool
    allow_write: bool
    allow_network: bool
    allow_order: bool
    allow_account_mutation: bool
    allow_secret_access: bool
    reason: str
    verdict: str  # "PASS" or "BLOCKED"


_PERMISSION_PRESETS: Dict[str, Dict[str, bool]] = {
    "readonly_safe": {
        "allow_read": True,
        "allow_write": False,
        "allow_network": False,
        "allow_order": False,
        "allow_account_mutation": False,
        "allow_secret_access": False,
    },
    "write_blocked": {
        "allow_read": True,
        "allow_write": True,
        "allow_network": False,
        "allow_order": False,
        "allow_account_mutation": False,
        "allow_secret_access": False,
    },
    "network_blocked": {
        "allow_read": True,
        "allow_write": False,
        "allow_network": True,
        "allow_order": False,
        "allow_account_mutation": False,
        "allow_secret_access": False,
    },
    "order_blocked": {
        "allow_read": True,
        "allow_write": False,
        "allow_network": False,
        "allow_order": True,
        "allow_account_mutation": False,
        "allow_secret_access": False,
    },
    "secret_blocked": {
        "allow_read": True,
        "allow_write": False,
        "allow_network": False,
        "allow_order": False,
        "allow_account_mutation": False,
        "allow_secret_access": True,
    },
}


def build_runtime_governance_permission_envelope(
    kind: str,
) -> RuntimeGovernancePermissionEnvelope:
    """Build by kind. Raises ValueError for unknown kind."""
    if kind not in _PERMISSION_PRESETS:
        raise ValueError(f"Unknown permission envelope kind: {kind!r}")
    preset = _PERMISSION_PRESETS[kind]
    verdict = evaluate_permission_envelope_raw(**preset)
    return RuntimeGovernancePermissionEnvelope(
        **preset,
        reason=f"preset:{kind}",
        verdict=verdict,
    )


def evaluate_permission_envelope_raw(
    allow_read: bool,
    allow_write: bool,
    allow_network: bool,
    allow_order: bool,
    allow_account_mutation: bool,
    allow_secret_access: bool,
) -> str:
    """Return PASS or BLOCKED based on flags."""
    if not allow_read:
        return "BLOCKED"
    dangerous = allow_write or allow_network or allow_order or allow_account_mutation or allow_secret_access
    return "PASS" if not dangerous else "BLOCKED"


def evaluate_permission_envelope(
    envelope: RuntimeGovernancePermissionEnvelope,
) -> str:
    """Return PASS or BLOCKED."""
    return evaluate_permission_envelope_raw(
        allow_read=envelope.allow_read,
        allow_write=envelope.allow_write,
        allow_network=envelope.allow_network,
        allow_order=envelope.allow_order,
        allow_account_mutation=envelope.allow_account_mutation,
        allow_secret_access=envelope.allow_secret_access,
    )


def permission_envelope_to_dict(
    envelope: RuntimeGovernancePermissionEnvelope,
) -> Dict[str, Any]:
    """Serialize."""
    return {
        "allow_read": envelope.allow_read,
        "allow_write": envelope.allow_write,
        "allow_network": envelope.allow_network,
        "allow_order": envelope.allow_order,
        "allow_account_mutation": envelope.allow_account_mutation,
        "allow_secret_access": envelope.allow_secret_access,
        "reason": envelope.reason,
        "verdict": envelope.verdict,
    }


def permission_envelope_to_markdown(
    envelope: RuntimeGovernancePermissionEnvelope,
) -> str:
    """Deterministic markdown."""
    lines = [
        "# Permission Envelope",
        "",
        f"- **verdict**: {envelope.verdict}",
        f"- **reason**: {envelope.reason}",
        "",
        "## Permissions",
        "",
        f"| Permission | Allowed |",
        f"|---|---|",
        f"| read | {envelope.allow_read} |",
        f"| write | {envelope.allow_write} |",
        f"| network | {envelope.allow_network} |",
        f"| order | {envelope.allow_order} |",
        f"| account_mutation | {envelope.allow_account_mutation} |",
        f"| secret_access | {envelope.allow_secret_access} |",
    ]
    return "\n".join(lines) + "\n"
