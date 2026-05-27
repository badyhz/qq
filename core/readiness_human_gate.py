from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HumanGateType(Enum):
    APPROVAL = "APPROVAL"
    REVIEW = "REVIEW"
    RELEASE = "RELEASE"


@dataclass(frozen=True)
class ReadinessHumanGate:
    """Frozen human gate. No I/O, no timestamps."""

    gate_id: str
    gate_type: HumanGateType
    required_evidence: tuple  # tuple of str
    approved: bool
