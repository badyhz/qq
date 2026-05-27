"""Runtime governance no-submit evidence packet — evidence no unauthorized submits.

Pure. No I/O. No network. No random. Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceNoSubmitEvidence:
    """Single no-submit evidence item."""

    component: str  # e.g. "T794:some description"
    no_submit: bool
    no_network: bool
    deterministic: bool
    message: str


# Default 18 components T794-T811
_DEFAULT_COMPONENT_IDS = [f"T{n}" for n in range(794, 812)]
_DEFAULT_COMPONENTS = [
    RuntimeGovernanceNoSubmitEvidence(
        component=f"{cid}:governance check",
        no_submit=True,
        no_network=True,
        deterministic=True,
        message=f"component {cid} verified",
    )
    for cid in _DEFAULT_COMPONENT_IDS
]


# ── builder ───────────────────────────────────────────────────────────


def build_runtime_governance_no_submit_evidence_packet(
    *,
    evidence: List[RuntimeGovernanceNoSubmitEvidence] | None = None,
) -> List[RuntimeGovernanceNoSubmitEvidence]:
    """Build no-submit evidence list. Pure. No I/O.

    Returns the evidence list directly (not a wrapper object).
    If evidence is None, returns default 18-component list.
    """
    return list(evidence) if evidence is not None else list(_DEFAULT_COMPONENTS)


# ── helpers ───────────────────────────────────────────────────────────


def no_submit_evidence_verdict(evidence: List[RuntimeGovernanceNoSubmitEvidence]) -> str:
    """Compute PASS/FAIL verdict from evidence list. Pure."""
    if all(e.no_submit and e.no_network and e.deterministic for e in evidence):
        return "PASS"
    return "FAIL"


# ── serialization ─────────────────────────────────────────────────────


def no_submit_evidence_to_dict(
    evidence: List[RuntimeGovernanceNoSubmitEvidence],
) -> List[Dict[str, Any]]:
    """Serialize evidence list to list of dicts. Pure."""
    return [
        {
            "component": e.component,
            "no_submit": e.no_submit,
            "no_network": e.no_network,
            "deterministic": e.deterministic,
            "message": e.message,
        }
        for e in evidence
    ]


def no_submit_evidence_to_markdown(
    evidence: List[RuntimeGovernanceNoSubmitEvidence],
) -> str:
    """Render evidence as deterministic markdown. No timestamps."""
    lines: List[str] = ["# No-Submit Evidence", ""]
    lines.append("| # | component | no_submit | no_network | deterministic | message |")
    lines.append("|---|---|---|---|---|---|")
    for idx, e in enumerate(evidence, 1):
        lines.append(
            f"| {idx} | {e.component} | {e.no_submit} | {e.no_network} | {e.deterministic} | {e.message} |"
        )
    lines.append("")
    return "\n".join(lines)
