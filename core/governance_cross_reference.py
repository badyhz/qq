"""Governance Cross Reference — T1366 frozen dataclass.

Cross-reference between governance domains.
Pure, frozen. No I/O. No network. No timestamps.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceCrossReference:
    """A cross-reference link between two governance domains."""
    ref_id: str
    source_domain: str
    target_domain: str
    relationship: str
    description: str
