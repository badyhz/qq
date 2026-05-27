"""Governance Registry Verdict — T1367 frozen dataclass + build_verdict.

Pure validation of registry completeness and consistency.
No I/O. No network. No timestamps.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.governance_registry import GovernanceRegistry
    from core.governance_layer_index import GovernanceLayerIndex


@dataclass(frozen=True)
class GovernanceRegistryVerdict:
    """Verdict on registry completeness and consistency."""
    verdict: str  # PASS / WARN / FAIL
    notes: str
    missing_domains: tuple  # tuple of domain_id strings
    inconsistencies: tuple  # tuple of description strings


def build_verdict(
    registry: GovernanceRegistry,
    layer_index: GovernanceLayerIndex,
) -> GovernanceRegistryVerdict:
    """Pure function: validate registry against layer index.

    Checks:
    - All layer domains exist in registry
    - Registry domain counts match layer index totals
    - No duplicate domain_ids in registry
    """
    notes_parts: list[str] = []
    missing: list[str] = []
    inconsistencies: list[str] = []

    registry_domain_ids = {d.domain_id for d in registry.domains}
    layer_domain_ids: set[str] = set()
    for layer in layer_index.layers:
        for did in layer.domains:
            layer_domain_ids.add(did)

    # Check for domains in layer index but not in registry
    for did in sorted(layer_domain_ids):
        if did not in registry_domain_ids:
            missing.append(did)

    # Check for duplicate domain_ids
    seen: set[str] = set()
    for d in registry.domains:
        if d.domain_id in seen:
            inconsistencies.append(f"Duplicate domain_id: {d.domain_id}")
        seen.add(d.domain_id)

    # Check totals
    if len(registry.domains) != layer_index.total_domains:
        inconsistencies.append(
            f"Domain count mismatch: registry={len(registry.domains)}, "
            f"index={layer_index.total_domains}"
        )

    # Determine verdict
    if missing or inconsistencies:
        verdict = "FAIL"
        notes_parts.append(f"{len(missing)} missing, {len(inconsistencies)} inconsistencies")
    else:
        verdict = "PASS"
        notes_parts.append("All domains accounted for, no inconsistencies")

    return GovernanceRegistryVerdict(
        verdict=verdict,
        notes="; ".join(notes_parts),
        missing_domains=tuple(missing),
        inconsistencies=tuple(inconsistencies),
    )
