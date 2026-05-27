"""T1384 - HumanReviewEvidenceCheck frozen dataclass."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class EvidenceMatchStatus(Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"


@dataclass(frozen=True)
class HumanReviewEvidenceCheck:
    check_id: str
    evidence_type: str
    expected: str
    actual: str
    match_status: EvidenceMatchStatus
