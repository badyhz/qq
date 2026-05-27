"""PRD 500 backlog markdown pack — aggregate all map sections into one pack.

T912. Pure deterministic. No I/O. No timestamps. No random.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_backlog_schema import PrdBacklog
from core.prd_500_backlog_milestone_map import (
    build_prd_500_milestone_map,
    milestone_map_to_markdown,
)
from core.prd_500_backlog_wave_map import (
    build_prd_500_wave_map,
    wave_map_to_markdown,
)
from core.prd_500_backlog_batch_map import (
    build_prd_500_batch_map,
    batch_map_to_markdown,
)
from core.prd_500_backlog_dependency_map import (
    build_prd_500_dependency_map,
    dependency_map_to_markdown,
)
from core.prd_500_backlog_risk_map import (
    build_prd_500_risk_map,
    risk_map_to_markdown,
)


# --- Dataclass ---


@dataclass(frozen=True)
class Prd500MarkdownPack:
    title: str
    sections: List[str]
    item_count: int
    final_verdict: str
    notes: List[str]


# --- Verdict logic ---


def _resolve_verdict(
    dep_verdict: str,
    frozen_count: int,
    high_count: int,
) -> str:
    """Resolve final verdict from dependency map and risk counts."""
    if dep_verdict == "FAIL":
        return "FAIL"
    if frozen_count > 0:
        return "BLOCKED"
    if dep_verdict == "BLOCKED":
        return "BLOCKED"
    if high_count > 0:
        return "WARN"
    if dep_verdict == "WARN":
        return "WARN"
    return "PASS"


# --- Builder ---


def build_prd_500_markdown_pack(backlog: PrdBacklog) -> Prd500MarkdownPack:
    """Build markdown pack from backlog. Pure deterministic."""
    item_count = len(backlog.items)
    sections: List[str] = []
    notes: List[str] = []

    # Section 1: Summary
    summary_lines: List[str] = []
    summary_lines.append("# PRD 500 Backlog Summary")
    summary_lines.append("")
    summary_lines.append(f"- **Title:** {backlog.backlog_id}")
    summary_lines.append(f"- **Item count:** {item_count}")
    summary_lines.append(f"- **Expected tasks:** {backlog.total_expected_tasks}")
    summary_lines.append(f"- **Backlog status:** {backlog.status}")
    if backlog.notes:
        summary_lines.append("- **Notes:**")
        for note in backlog.notes:
            summary_lines.append(f"  - {note}")
    summary_lines.append("")
    sections.append("\n".join(summary_lines))

    # Section 2: Milestone map
    milestone_entries = build_prd_500_milestone_map(backlog)
    milestone_parts: List[str] = []
    milestone_parts.append("# Milestone Map")
    milestone_parts.append("")
    for entry in milestone_entries:
        milestone_parts.append(milestone_map_to_markdown(entry))
    sections.append("\n".join(milestone_parts))

    # Section 3: Wave map
    wave_entries = build_prd_500_wave_map(backlog)
    wave_parts: List[str] = []
    wave_parts.append("# Wave Map")
    wave_parts.append("")
    for entry in wave_entries:
        wave_parts.append(wave_map_to_markdown(entry))
    sections.append("\n".join(wave_parts))

    # Section 4: Batch map
    batch_entries = build_prd_500_batch_map(backlog)
    batch_parts: List[str] = []
    batch_parts.append("# Batch Map")
    batch_parts.append("")
    for entry in batch_entries:
        batch_parts.append(batch_map_to_markdown(entry))
    sections.append("\n".join(batch_parts))

    # Section 5: Dependency map
    dep_map = build_prd_500_dependency_map(backlog)
    sections.append(dependency_map_to_markdown(dep_map))

    # Section 6: Risk map
    risk_map = build_prd_500_risk_map(backlog)
    sections.append(risk_map_to_markdown(risk_map))

    # Final verdict
    final_verdict = _resolve_verdict(
        dep_verdict=dep_map.final_verdict,
        frozen_count=risk_map.frozen_count,
        high_count=risk_map.high_count,
    )

    if dep_map.notes:
        notes.extend(dep_map.notes)
    if risk_map.notes:
        notes.extend(risk_map.notes)
    if not notes:
        notes.append("no issues")

    return Prd500MarkdownPack(
        title=backlog.backlog_id,
        sections=sections,
        item_count=item_count,
        final_verdict=final_verdict,
        notes=notes,
    )


# --- Serializers ---


def markdown_pack_to_dict(pack: Prd500MarkdownPack) -> Dict[str, Any]:
    """Convert pack to dict. Pure."""
    return {
        "title": pack.title,
        "section_count": len(pack.sections),
        "item_count": pack.item_count,
        "final_verdict": pack.final_verdict,
        "notes": list(pack.notes),
    }


def markdown_pack_to_markdown(pack: Prd500MarkdownPack) -> str:
    """Convert pack to single markdown string. Pure."""
    lines: List[str] = []
    lines.append(f"# {pack.title} — Markdown Pack")
    lines.append("")
    lines.append(f"- **Items:** {pack.item_count}")
    lines.append(f"- **Sections:** {len(pack.sections)}")
    lines.append(f"- **Verdict:** {pack.final_verdict}")
    lines.append("")
    for section in pack.sections:
        lines.append(section)
        lines.append("")
        lines.append("---")
        lines.append("")
    if pack.notes:
        lines.append("## Pack Notes")
        lines.append("")
        for note in pack.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
