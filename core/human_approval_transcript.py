"""T1453 - HumanApprovalTranscript frozen dataclass.

Pure, frozen, deterministic. No I/O. No random.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from core.transcript_step import TranscriptStep


@dataclass(frozen=True)
class HumanApprovalTranscript:
    """Immutable record of human approval process.

    Pure, frozen. No I/O. No random. Timestamp is passed in, not generated.
    """
    transcript_id: str
    file_path: str
    reviewer_id: str
    steps: Tuple[TranscriptStep, ...]
    final_decision: str
    timestamp_iso: str
