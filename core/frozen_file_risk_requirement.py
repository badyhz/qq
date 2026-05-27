"""T1443 - FrozenFileRiskRequirement frozen dataclass.

Pure, frozen. No I/O. No network. No random. No timestamps. No env reads.
"""
from __future__ import annotations

from dataclasses import dataclass


VALID_RISK_CLASSES = ("HIGH", "MEDIUM")


@dataclass(frozen=True)
class FrozenFileRiskRequirement:
    """Immutable risk requirement for a frozen file review.

    Pure deterministic. No I/O. No timestamps. No network.
    """
    requirement_id: str
    risk_class: str
    requirement_name: str
    required_evidence: tuple[str, ...]
    mandatory: bool
    human_approval_needed: bool


def build_risk_requirement(
    requirement_id: str,
    risk_class: str,
    requirement_name: str,
    required_evidence: tuple[str, ...] = (),
    mandatory: bool = True,
    human_approval_needed: bool = False,
) -> FrozenFileRiskRequirement:
    """Factory for FrozenFileRiskRequirement with validation."""
    if risk_class not in VALID_RISK_CLASSES:
        raise ValueError(f"Invalid risk_class: {risk_class}. Must be one of {VALID_RISK_CLASSES}")
    return FrozenFileRiskRequirement(
        requirement_id=requirement_id,
        risk_class=risk_class,
        requirement_name=requirement_name,
        required_evidence=required_evidence,
        mandatory=mandatory,
        human_approval_needed=human_approval_needed,
    )
