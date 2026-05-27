"""Runtime governance audit event model — pure data objects for audit decisions.

No file I/O. No network. No live system dependency.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.governance_failure_taxonomy import (
    FailureCategory,
    FailureSeverity,
    GovernanceFailure,
)


@dataclass(frozen=True)
class RuntimeGovernanceAuditEvent:
    """Immutable audit event for a runtime governance decision."""

    event_id: str
    run_id: str
    adapter_id: str
    action: str
    verdict: str
    failure_count: int
    categories: List[str]       # sorted category values
    severities: List[str]       # sorted severity values
    metadata: Dict[str, Any]    # frozen snapshot


# ── builder ───────────────────────────────────────────────────────────


def build_runtime_governance_audit_event(
    *,
    run_id: str,
    adapter_id: str,
    action: str,
    verdict: str,
    failures: List[GovernanceFailure] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> RuntimeGovernanceAuditEvent:
    """Build an audit event from governance context.

    Pure. Deterministic. No I/O.
    """
    failures = failures or []
    meta = dict(metadata) if metadata else {}

    categories = sorted({f.category.value for f in failures})
    severities = sorted({f.severity.value for f in failures})

    event_id = _compute_event_id(
        run_id=run_id,
        adapter_id=adapter_id,
        action=action,
        verdict=verdict,
        categories=categories,
        severities=severities,
    )

    return RuntimeGovernanceAuditEvent(
        event_id=event_id,
        run_id=run_id,
        adapter_id=adapter_id,
        action=action,
        verdict=verdict,
        failure_count=len(failures),
        categories=categories,
        severities=severities,
        metadata=meta,
    )


# ── serialization ─────────────────────────────────────────────────────


def audit_event_to_dict(event: RuntimeGovernanceAuditEvent) -> Dict[str, Any]:
    """Serialize audit event to a plain dict. No I/O."""
    return {
        "event_id": event.event_id,
        "run_id": event.run_id,
        "adapter_id": event.adapter_id,
        "action": event.action,
        "verdict": event.verdict,
        "failure_count": event.failure_count,
        "categories": list(event.categories),
        "severities": list(event.severities),
        "metadata": dict(event.metadata),
    }


def audit_event_to_markdown(event: RuntimeGovernanceAuditEvent) -> str:
    """Render audit event as deterministic markdown. No timestamps. No I/O."""
    cats = ", ".join(event.categories) if event.categories else "(none)"
    sevs = ", ".join(event.severities) if event.severities else "(none)"

    lines = [
        f"## Audit Event `{event.event_id}`",
        "",
        f"- **run_id:** `{event.run_id}`",
        f"- **adapter_id:** `{event.adapter_id}`",
        f"- **action:** `{event.action}`",
        f"- **verdict:** `{event.verdict}`",
        f"- **failure_count:** {event.failure_count}",
        f"- **categories:** {cats}",
        f"- **severities:** {sevs}",
    ]

    if event.metadata:
        lines.append("")
        lines.append("### Metadata")
        for key in sorted(event.metadata):
            lines.append(f"- **{key}:** `{event.metadata[key]}`")

    return "\n".join(lines) + "\n"


# ── internal ──────────────────────────────────────────────────────────


def _compute_event_id(
    *,
    run_id: str,
    adapter_id: str,
    action: str,
    verdict: str,
    categories: List[str],
    severities: List[str],
) -> str:
    """Deterministic event_id from decision inputs. No timestamps. No random."""
    parts = [
        f"run_id={run_id}",
        f"adapter_id={adapter_id}",
        f"action={action}",
        f"verdict={verdict}",
        f"categories={','.join(categories)}",
        f"severities={','.join(severities)}",
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
