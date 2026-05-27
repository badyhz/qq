"""Governance Layer Entry — T1364 frozen dataclass.

Single layer within a governance layer index.
Pure, frozen. No I/O. No network. No timestamps.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceLayerEntry:
    """One governance layer in the index."""
    layer_id: str
    name: str
    task_range: str
    description: str
    domains: tuple  # tuple of domain_id strings
    hard_stop: str
