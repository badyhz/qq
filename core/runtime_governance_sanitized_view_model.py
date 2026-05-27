"""Runtime governance sanitized view model — expose governance data with field-level redaction.

Views: preflight_summary, regression_summary, safety_summary, artifact_summary.
No secrets / account balances / raw orders allowed (sensitivity=secret fields always allowed=False).
Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceSanitizedField:
    """Single field in a sanitized view."""
    name: str
    value_type: str
    sensitivity: str  # "public", "internal", "sensitive", "secret"
    allowed: bool
    redaction_rule: str


@dataclass(frozen=True)
class RuntimeGovernanceSanitizedView:
    """Immutable sanitized view of governance data."""
    view_id: str
    fields: List[RuntimeGovernanceSanitizedField]
    verdict: str
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# View definitions — secret fields always have allowed=False
# ---------------------------------------------------------------------------

_PREFLIGHT_SUMMARY_FIELDS: List[RuntimeGovernanceSanitizedField] = [
    RuntimeGovernanceSanitizedField("preflight_pass", "bool", "public", True, "none"),
    RuntimeGovernanceSanitizedField("total_checks", "int", "public", True, "none"),
    RuntimeGovernanceSanitizedField("critical_failures", "int", "public", True, "none"),
    RuntimeGovernanceSanitizedField("recommended_action", "str", "public", True, "none"),
    RuntimeGovernanceSanitizedField("by_category", "dict", "internal", True, "none"),
    RuntimeGovernanceSanitizedField("by_source", "dict", "internal", True, "none"),
    RuntimeGovernanceSanitizedField("api_key", "str", "secret", False, "redact_full"),
    RuntimeGovernanceSanitizedField("api_secret", "str", "secret", False, "redact_full"),
    RuntimeGovernanceSanitizedField("account_balance", "float", "secret", False, "redact_full"),
]

_REGRESSION_SUMMARY_FIELDS: List[RuntimeGovernanceSanitizedField] = [
    RuntimeGovernanceSanitizedField("regression_pass", "bool", "public", True, "none"),
    RuntimeGovernanceSanitizedField("total_tests", "int", "public", True, "none"),
    RuntimeGovernanceSanitizedField("failures", "int", "public", True, "none"),
    RuntimeGovernanceSanitizedField("skipped", "int", "public", True, "none"),
    RuntimeGovernanceSanitizedField("duration_seconds", "float", "internal", True, "none"),
    RuntimeGovernanceSanitizedField("failure_details", "list", "internal", True, "truncate_500"),
    RuntimeGovernanceSanitizedField("api_key", "str", "secret", False, "redact_full"),
    RuntimeGovernanceSanitizedField("api_secret", "str", "secret", False, "redact_full"),
]

_SAFETY_SUMMARY_FIELDS: List[RuntimeGovernanceSanitizedField] = [
    RuntimeGovernanceSanitizedField("safety_pass", "bool", "public", True, "none"),
    RuntimeGovernanceSanitizedField("risk_score", "float", "public", True, "none"),
    RuntimeGovernanceSanitizedField("circuit_breaker_active", "bool", "public", True, "none"),
    RuntimeGovernanceSanitizedField("max_drawdown_pct", "float", "internal", True, "none"),
    RuntimeGovernanceSanitizedField("position_limits", "dict", "internal", True, "none"),
    RuntimeGovernanceSanitizedField("raw_orders", "list", "secret", False, "redact_full"),
    RuntimeGovernanceSanitizedField("account_balance", "float", "secret", False, "redact_full"),
    RuntimeGovernanceSanitizedField("credential_tokens", "list", "secret", False, "redact_full"),
]

_ARTIFACT_SUMMARY_FIELDS: List[RuntimeGovernanceSanitizedField] = [
    RuntimeGovernanceSanitizedField("artifact_count", "int", "public", True, "none"),
    RuntimeGovernanceSanitizedField("verified_count", "int", "public", True, "none"),
    RuntimeGovernanceSanitizedField("pending_count", "int", "public", True, "none"),
    RuntimeGovernanceSanitizedField("artifact_types", "dict", "internal", True, "none"),
    RuntimeGovernanceSanitizedField("checksum_summary", "str", "internal", True, "none"),
    RuntimeGovernanceSanitizedField("signing_key", "str", "secret", False, "redact_full"),
    RuntimeGovernanceSanitizedField("private_key", "str", "secret", False, "redact_full"),
]

_VIEWS: Dict[str, tuple] = {
    "preflight_summary": (_PREFLIGHT_SUMMARY_FIELDS, "PASS"),
    "regression_summary": (_REGRESSION_SUMMARY_FIELDS, "PASS"),
    "safety_summary": (_SAFETY_SUMMARY_FIELDS, "PASS"),
    "artifact_summary": (_ARTIFACT_SUMMARY_FIELDS, "PASS"),
}


def build_runtime_governance_sanitized_view(view_id: str) -> RuntimeGovernanceSanitizedView:
    """Build view by id. Raises ValueError for unknown id. Pure. Deterministic."""
    if view_id not in _VIEWS:
        raise ValueError(f"Unknown sanitized view id: {view_id!r}. Valid: {sorted(_VIEWS)}")
    fields, verdict = _VIEWS[view_id]
    # Verify no secret field is accidentally allowed
    for f in fields:
        if f.sensitivity == "secret" and f.allowed:
            raise ValueError(
                f"Policy violation: secret field {f.name!r} in view {view_id!r} must have allowed=False"
            )
    return RuntimeGovernanceSanitizedView(
        view_id=view_id,
        fields=list(fields),
        verdict=verdict,
    )


def sanitized_view_to_dict(view: RuntimeGovernanceSanitizedView) -> Dict[str, Any]:
    """Serialize sanitized view to dict. Pure. Deterministic."""
    return {
        "view_id": view.view_id,
        "fields": [
            {
                "name": f.name,
                "value_type": f.value_type,
                "sensitivity": f.sensitivity,
                "allowed": f.allowed,
                "redaction_rule": f.redaction_rule,
            }
            for f in view.fields
        ],
        "verdict": view.verdict,
        "notes": list(view.notes),
    }


def sanitized_view_to_markdown(view: RuntimeGovernanceSanitizedView) -> str:
    """Render sanitized view as deterministic markdown. No timestamps."""
    lines = [
        f"# Sanitized View: {view.view_id}",
        "",
        f"**Verdict:** {view.verdict}",
        "",
        "## Fields",
        "",
        "| Name | Type | Sensitivity | Allowed | Redaction |",
        "|------|------|-------------|---------|-----------|",
    ]
    for f in view.fields:
        allowed_str = "yes" if f.allowed else "**NO**"
        lines.append(
            f"| {f.name} | {f.value_type} | {f.sensitivity} | {allowed_str} | {f.redaction_rule} |"
        )
    lines.append("")
    if view.notes:
        lines.append("## Notes")
        lines.append("")
        for note in view.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


def summarize_sanitized_view(view: RuntimeGovernanceSanitizedView) -> Dict[str, Any]:
    """Summarize sanitized view. Pure. Deterministic."""
    total = len(view.fields)
    allowed_count = sum(1 for f in view.fields if f.allowed)
    blocked_count = total - allowed_count
    by_sensitivity: Dict[str, int] = {}
    for f in view.fields:
        by_sensitivity[f.sensitivity] = by_sensitivity.get(f.sensitivity, 0) + 1
    return {
        "view_id": view.view_id,
        "verdict": view.verdict,
        "total_fields": total,
        "allowed_fields": allowed_count,
        "blocked_fields": blocked_count,
        "by_sensitivity": dict(sorted(by_sensitivity.items())),
        "has_notes": len(view.notes) > 0,
    }
