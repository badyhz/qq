"""Governance Domain Entry — T1362 frozen dataclass.

Single domain within a governance registry.
Pure, frozen. No I/O. No network. No timestamps.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceDomainEntry:
    """One governance domain indexed in the registry."""
    domain_id: str
    domain_name: str
    task_range: str
    layer_name: str
    doc_count: int
    model_count: int
    test_count: int
    status: str
