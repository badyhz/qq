from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumRiskDryRunRequirement:
    """T1214 - frozen dataclass for dry-run requirement."""

    script_name: str
    default_mode: str
    requires_human_flag_for_live: bool
    requires_approval_for_testnet: bool
