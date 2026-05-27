"""Governance Registry — T1361 frozen dataclass.

Indexes all governance domains across layers.
Pure, frozen. No I/O. No network. No timestamps.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.governance_domain_entry import GovernanceDomainEntry


@dataclass(frozen=True)
class GovernanceRegistry:
    """Top-level registry of all governance domains."""
    registry_id: str
    domains: tuple  # tuple of GovernanceDomainEntry
    version: str
    created_by: str
