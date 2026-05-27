from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumRiskCommitIsolation:
    """T1217 - frozen dataclass for commit isolation policy."""

    must_not_mix_with_high_risk: bool
    explicit_file_list_required: bool
    verify_no_frozen: bool
