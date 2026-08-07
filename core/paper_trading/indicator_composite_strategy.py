"""Compatibility type retained for the recovered Market Accelerator port.

The standalone INDICATOR_COMPOSITE_V1 entry/exit strategy was rejected by
multi-period public-history research and is intentionally removed.  This module
keeps only the small enum already imported by the authoritative accelerator
port, avoiding a new compatibility file during convergence.

No strategy entry, exit, risk, account, order, Testnet or Live behavior lives
here.
"""
from __future__ import annotations

from enum import Enum


class AccelerationRegime(str, Enum):
    """Normalized Market Accelerator / 疾速500 regimes."""

    IDLE = "IDLE"
    START = "START"
    FAST = "FAST"
    EXTREME = "EXTREME"
    DECELERATING = "DECELERATING"
