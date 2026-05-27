"""T1454 - TranscriptStep frozen dataclass.

Pure, frozen, deterministic. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Union


class StepType(Enum):
    """Transcript step types."""
    REVIEW_START = "REVIEW_START"
    CHECK_PASS = "CHECK_PASS"
    CHECK_FAIL = "CHECK_FAIL"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    RISK_ACKNOWLEDGED = "RISK_ACKNOWLEDGED"
    DECISION_MADE = "DECISION_MADE"


@dataclass(frozen=True)
class TranscriptStep:
    """Single step in a human approval transcript.

    Pure, frozen. No I/O. No random. No timestamps generated internally.
    """
    step_id: str
    step_type: StepType
    description: str
    step_data: Union[Dict[str, object], str]
