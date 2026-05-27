"""Governance Layer Index — T1363 frozen dataclass.

Aggregated index of all governance layers.
Pure, frozen. No I/O. No network. No timestamps.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceLayerIndex:
    """Index aggregating all governance layers."""
    index_id: str
    layers: tuple  # tuple of GovernanceLayerEntry
    total_domains: int
    total_models: int
    total_docs: int
    total_tests: int
