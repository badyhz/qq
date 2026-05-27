"""Runtime governance blocker summary — summarize blockers from preflight packets.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.runtime_governance_preflight_packet import RuntimeGovernancePreflightPacket
from core.governance_failure_taxonomy import FailureCategory, FailureSeverity


@dataclass(frozen=True)
class RuntimeGovernanceBlocker:
    """Single blocker item (compatibility)."""
    blocker_id: str
    action: str
    message: str
    severity: str


@dataclass(frozen=True)
class RuntimeGovernanceBlockerSummary:
    """Immutable blocker summary."""
    total_blockers: int
    critical_blockers: int
    policy_blockers: int
    by_category: Dict[str, int]
    by_source: Dict[str, int]
    recommended_action: str  # "PROCEED" / "REVIEW" / "BLOCK"
    notes: List[str] = field(default_factory=list)

    @property
    def action(self) -> str:
        """Alias for recommended_action."""
        return self.recommended_action


def summarize_runtime_governance_blockers(
    packet: RuntimeGovernancePreflightPacket | None = None,
    *,
    blockers: List[RuntimeGovernanceBlocker] | None = None,
) -> RuntimeGovernanceBlockerSummary:
    """Summarize blockers from a preflight packet or blocker list. Pure. Deterministic."""
    if blockers is not None:
        # Direct blocker list mode
        by_category: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        critical_count = 0
        policy_count = 0
        for b in blockers:
            if b.severity == "critical":
                critical_count += 1
            if b.action == "BLOCK":
                policy_count += 1
        total = len(blockers)
        if critical_count > 0 or policy_count > 0:
            action = "BLOCK"
        elif total > 0:
            action = "REVIEW"
        else:
            action = "PROCEED"
        return RuntimeGovernanceBlockerSummary(
            total_blockers=total,
            critical_blockers=critical_count,
            policy_blockers=policy_count,
            by_category=by_category,
            by_source=by_source,
            recommended_action=action,
        )
    if packet is None:
        return RuntimeGovernanceBlockerSummary(
            total_blockers=0,
            critical_blockers=0,
            policy_blockers=0,
            by_category={},
            by_source={},
            recommended_action="PROCEED",
        )
    failures = packet.dry_run_result.contract_result.failures

    by_category: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    critical_count = 0
    policy_count = 0

    for f in failures:
        cat = f.category.value
        by_category[cat] = by_category.get(cat, 0) + 1
        if f.source:
            by_source[f.source] = by_source.get(f.source, 0) + 1
        if f.severity == FailureSeverity.CRITICAL:
            critical_count += 1
        if f.category == FailureCategory.POLICY_BLOCK:
            policy_count += 1

    total = len(failures)

    if critical_count > 0 or policy_count > 0:
        action = "BLOCK"
    elif total > 0:
        action = "REVIEW"
    else:
        action = "PROCEED"

    return RuntimeGovernanceBlockerSummary(
        total_blockers=total,
        critical_blockers=critical_count,
        policy_blockers=policy_count,
        by_category=dict(sorted(by_category.items())),
        by_source=dict(sorted(by_source.items())),
        recommended_action=action,
    )


def blocker_summary_to_dict(summary: RuntimeGovernanceBlockerSummary) -> Dict[str, Any]:
    """Serialize to dict. Pure."""
    return {
        "total_blockers": summary.total_blockers,
        "critical_blockers": summary.critical_blockers,
        "policy_blockers": summary.policy_blockers,
        "by_category": dict(summary.by_category),
        "by_source": dict(summary.by_source),
        "recommended_action": summary.recommended_action,
    }


def blocker_summary_to_markdown(summary: RuntimeGovernanceBlockerSummary) -> str:
    """Render as deterministic markdown. No timestamps."""
    lines = [
        "# Runtime Governance Blocker Summary",
        "",
        f"**Recommended Action:** {summary.recommended_action}",
        f"**Total Blockers:** {summary.total_blockers}",
        f"**Critical:** {summary.critical_blockers}",
        f"**Policy:** {summary.policy_blockers}",
        "",
    ]
    if summary.by_category:
        lines.append("## By Category")
        lines.append("")
        for cat, count in summary.by_category.items():
            lines.append(f"- {cat}: {count}")
        lines.append("")
    if summary.by_source:
        lines.append("## By Source")
        lines.append("")
        for src, count in summary.by_source.items():
            lines.append(f"- {src}: {count}")
        lines.append("")
    return "\n".join(lines)
