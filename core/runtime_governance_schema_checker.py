"""Pure structural schema checks for serialized runtime governance objects.

No JSON schema dependency. Deterministic expected field lists.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceSchemaCheck:
    ok: bool
    object_type: str
    missing_fields: List[str]  # sorted
    unexpected_fields: List[str]  # sorted
    notes: List[str]


_RUNTIME_INPUT_EXPECTED = frozenset({
    "run_id",
    "adapter_id",
    "mode",
    "requested_action",
    "symbol",
    "environment",
    "allow_network",
    "allow_submit",
    "allow_file_io",
    "metadata",
})

_PREFLIGHT_PACKET_EXPECTED = frozenset({
    "input",
    "dry_run_result",
    "audit_event",
    "final_verdict",
    "proceed",
    "notes",
})


def _build_check(
    object_type: str,
    data: Dict[str, Any],
    expected: frozenset,
) -> RuntimeGovernanceSchemaCheck:
    actual = frozenset(data.keys())
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    ok = not missing and not unexpected
    notes: List[str] = []
    if missing:
        notes.append(f"missing {len(missing)} field(s)")
    if unexpected:
        notes.append(f"unexpected {len(unexpected)} field(s)")
    return RuntimeGovernanceSchemaCheck(
        ok=ok,
        object_type=object_type,
        missing_fields=missing,
        unexpected_fields=unexpected,
        notes=notes,
    )


def check_runtime_input_dict_schema(data: Dict[str, Any]) -> RuntimeGovernanceSchemaCheck:
    """Check a runtime input dict has exactly the expected fields."""
    return _build_check("runtime_input", data, _RUNTIME_INPUT_EXPECTED)


def check_preflight_packet_dict_schema(data: Dict[str, Any]) -> RuntimeGovernanceSchemaCheck:
    """Check a preflight packet dict has exactly the expected fields."""
    return _build_check("preflight_packet", data, _PREFLIGHT_PACKET_EXPECTED)


def schema_check_to_dict(check: RuntimeGovernanceSchemaCheck) -> Dict[str, Any]:
    """Serialize a schema check to a plain dict."""
    return {
        "ok": check.ok,
        "object_type": check.object_type,
        "missing_fields": list(check.missing_fields),
        "unexpected_fields": list(check.unexpected_fields),
        "notes": list(check.notes),
    }


def schema_check_to_markdown(check: RuntimeGovernanceSchemaCheck) -> str:
    """Serialize a schema check to deterministic markdown."""
    status = "PASS" if check.ok else "FAIL"
    lines = [
        f"# Schema Check: {check.object_type}",
        "",
        f"**Status:** {status}",
    ]
    if check.missing_fields:
        lines.append("")
        lines.append("**Missing fields:**")
        for f in check.missing_fields:
            lines.append(f"- {f}")
    if check.unexpected_fields:
        lines.append("")
        lines.append("**Unexpected fields:**")
        for f in check.unexpected_fields:
            lines.append(f"- {f}")
    if check.notes:
        lines.append("")
        lines.append("**Notes:**")
        for n in check.notes:
            lines.append(f"- {n}")
    lines.append("")
    return "\n".join(lines)
