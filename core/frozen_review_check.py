"""T1442 - FrozenReviewCheck frozen dataclass.

Pure, frozen. No I/O. No network. No random. No timestamps. No env reads.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CheckType(Enum):
    """Type of review check."""
    IMPORT_BOUNDARY = "IMPORT_BOUNDARY"
    NETWORK_FREE = "NETWORK_FREE"
    CREDENTIAL_FREE = "CREDENTIAL_FREE"
    SIDE_EFFECT_FREE = "SIDE_EFFECT_FREE"
    DRY_RUN_ONLY = "DRY_RUN_ONLY"
    HUMAN_APPROVED = "HUMAN_APPROVED"


class CheckStatus(Enum):
    """Status of a review check."""
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class FrozenReviewCheck:
    """Immutable review check for a frozen file.

    Pure deterministic. No I/O. No timestamps. No network.
    """
    check_id: str
    check_name: str
    check_type: CheckType
    status: CheckStatus
    description: str


def build_review_check(
    check_id: str,
    check_name: str,
    check_type: str,
    status: str = "PENDING",
    description: str = "",
) -> FrozenReviewCheck:
    """Factory for FrozenReviewCheck with string-to-enum conversion."""
    return FrozenReviewCheck(
        check_id=check_id,
        check_name=check_name,
        check_type=CheckType(check_type),
        status=CheckStatus(status),
        description=description,
    )
