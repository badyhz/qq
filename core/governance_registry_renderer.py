"""Governance Registry Renderer — T1368 pure markdown renderers.

Pure functions. No I/O. No network. No timestamps.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.governance_registry import GovernanceRegistry
    from core.governance_domain_entry import GovernanceDomainEntry
    from core.governance_layer_index import GovernanceLayerIndex
    from core.governance_registry_verdict import GovernanceRegistryVerdict


def render_governance_registry_md(registry: GovernanceRegistry) -> str:
    """Render GovernanceRegistry to markdown."""
    lines: list[str] = []
    lines.append("## Governance Registry")
    lines.append("")
    lines.append(f"- **Registry ID:** {registry.registry_id}")
    lines.append(f"- **Version:** {registry.version}")
    lines.append(f"- **Created By:** {registry.created_by}")
    lines.append(f"- **Domain Count:** {len(registry.domains)}")
    lines.append("")
    if registry.domains:
        lines.append("### Domains")
        lines.append("")
        lines.append("| Domain ID | Name | Task Range | Layer | Docs | Models | Tests | Status |")
        lines.append("|-----------|------|------------|-------|------|--------|-------|--------|")
        for d in registry.domains:
            lines.append(
                f"| {d.domain_id} | {d.domain_name} | {d.task_range} | "
                f"{d.layer_name} | {d.doc_count} | {d.model_count} | "
                f"{d.test_count} | {d.status} |"
            )
        lines.append("")
    return "\n".join(lines)


def render_governance_domain_entry_md(entry: GovernanceDomainEntry) -> str:
    """Render GovernanceDomainEntry to markdown."""
    lines: list[str] = []
    lines.append("## Governance Domain Entry")
    lines.append("")
    lines.append(f"- **Domain ID:** {entry.domain_id}")
    lines.append(f"- **Name:** {entry.domain_name}")
    lines.append(f"- **Task Range:** {entry.task_range}")
    lines.append(f"- **Layer:** {entry.layer_name}")
    lines.append(f"- **Docs:** {entry.doc_count}")
    lines.append(f"- **Models:** {entry.model_count}")
    lines.append(f"- **Tests:** {entry.test_count}")
    lines.append(f"- **Status:** {entry.status}")
    lines.append("")
    return "\n".join(lines)


def render_governance_layer_index_md(index: GovernanceLayerIndex) -> str:
    """Render GovernanceLayerIndex to markdown."""
    lines: list[str] = []
    lines.append("## Governance Layer Index")
    lines.append("")
    lines.append(f"- **Index ID:** {index.index_id}")
    lines.append(f"- **Total Domains:** {index.total_domains}")
    lines.append(f"- **Total Models:** {index.total_models}")
    lines.append(f"- **Total Docs:** {index.total_docs}")
    lines.append(f"- **Total Tests:** {index.total_tests}")
    lines.append(f"- **Layer Count:** {len(index.layers)}")
    lines.append("")
    if index.layers:
        lines.append("### Layers")
        lines.append("")
        for layer in index.layers:
            lines.append(f"#### {layer.name}")
            lines.append("")
            lines.append(f"- **Layer ID:** {layer.layer_id}")
            lines.append(f"- **Task Range:** {layer.task_range}")
            lines.append(f"- **Description:** {layer.description}")
            lines.append(f"- **Hard Stop:** {layer.hard_stop}")
            lines.append(f"- **Domains:** {', '.join(layer.domains) if layer.domains else 'none'}")
            lines.append("")
    return "\n".join(lines)


def render_governance_registry_verdict_md(verdict: GovernanceRegistryVerdict) -> str:
    """Render GovernanceRegistryVerdict to markdown."""
    lines: list[str] = []
    lines.append("## Governance Registry Verdict")
    lines.append("")
    lines.append(f"- **Verdict:** {verdict.verdict}")
    lines.append(f"- **Notes:** {verdict.notes}")
    lines.append("")
    if verdict.missing_domains:
        lines.append("### Missing Domains")
        for did in verdict.missing_domains:
            lines.append(f"- {did}")
        lines.append("")
    if verdict.inconsistencies:
        lines.append("### Inconsistencies")
        for inc in verdict.inconsistencies:
            lines.append(f"- {inc}")
        lines.append("")
    return "\n".join(lines)
