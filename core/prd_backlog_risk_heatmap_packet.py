"""PRD backlog risk heatmap packet.

T893. Pure deterministic, no I/O, no timestamps, no random.
Generates a risk heatmap showing risk distribution across milestones and waves.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.prd_backlog_schema import PrdBacklogItem

# Risk level display order
RISK_ORDER: Tuple[str, ...] = ("LOW", "MEDIUM", "HIGH", "FROZEN")


# --- Dataclasses ---


@dataclass(frozen=True)
class PrdRiskHeatmapCell:
    milestone_id: str
    wave_id: str
    risk_level: str
    task_count: int
    task_ids: Tuple[str, ...]


@dataclass(frozen=True)
class PrdRiskHeatmapPacket:
    packet_id: str
    total_tasks: int
    cells: Tuple[PrdRiskHeatmapCell, ...]
    risk_summary: Dict[str, int]
    notes: Tuple[str, ...]


# --- Generator ---


def generate_risk_heatmap(items: List[PrdBacklogItem]) -> PrdRiskHeatmapPacket:
    """Group items by (milestone_id, wave_id, risk_level) into heatmap cells.

    Pure, deterministic. Returns sorted cells and risk summary.
    """
    groups: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
    for item in items:
        key = (item.milestone_id, item.wave_id, item.risk_level)
        groups[key].append(item.task_id)

    # Build cells
    cells: List[PrdRiskHeatmapCell] = []
    for (milestone_id, wave_id, risk_level), task_ids in groups.items():
        sorted_ids = tuple(sorted(task_ids))
        cells.append(
            PrdRiskHeatmapCell(
                milestone_id=milestone_id,
                wave_id=wave_id,
                risk_level=risk_level,
                task_count=len(sorted_ids),
                task_ids=sorted_ids,
            )
        )

    # Sort by milestone, then wave, then risk level
    risk_rank = {r: i for i, r in enumerate(RISK_ORDER)}
    cells.sort(
        key=lambda c: (
            c.milestone_id,
            c.wave_id,
            risk_rank.get(c.risk_level, 999),
        )
    )

    # Compute risk summary
    risk_summary: Dict[str, int] = {}
    for cell in cells:
        risk_summary[cell.risk_level] = risk_summary.get(cell.risk_level, 0) + cell.task_count

    notes: List[str] = []
    if not items:
        notes.append("No items provided")

    return PrdRiskHeatmapPacket(
        packet_id="risk-heatmap-001",
        total_tasks=len(items),
        cells=tuple(cells),
        risk_summary=risk_summary,
        notes=tuple(notes),
    )


# --- Serializers ---


def risk_heatmap_to_dict(packet: PrdRiskHeatmapPacket) -> Dict[str, Any]:
    """Convert packet to plain dict."""
    return {
        "packet_id": packet.packet_id,
        "total_tasks": packet.total_tasks,
        "cells": [
            {
                "milestone_id": c.milestone_id,
                "wave_id": c.wave_id,
                "risk_level": c.risk_level,
                "task_count": c.task_count,
                "task_ids": list(c.task_ids),
            }
            for c in packet.cells
        ],
        "risk_summary": dict(packet.risk_summary),
        "notes": list(packet.notes),
    }


def risk_heatmap_to_markdown(packet: PrdRiskHeatmapPacket) -> str:
    """Render heatmap as markdown table: milestone | wave | LOW | MEDIUM | HIGH | FROZEN."""
    lines: List[str] = []
    lines.append("# PRD Risk Heatmap")
    lines.append("")
    lines.append(f"**Total tasks:** {packet.total_tasks}")
    lines.append("")

    if packet.notes:
        for note in packet.notes:
            lines.append(f"- {note}")
        lines.append("")

    # Collect all (milestone, wave) pairs in display order
    pair_order: List[Tuple[str, str]] = []
    pair_seen: set = set()
    for cell in packet.cells:
        key = (cell.milestone_id, cell.wave_id)
        if key not in pair_seen:
            pair_seen.add(key)
            pair_order.append(key)

    if not pair_order:
        lines.append("_No data_")
        return "\n".join(lines)

    # Build lookup: (milestone, wave, risk) -> count
    lookup: Dict[Tuple[str, str, str], int] = {}
    for cell in packet.cells:
        lookup[(cell.milestone_id, cell.wave_id, cell.risk_level)] = cell.task_count

    # Table header
    lines.append("| Milestone | Wave | LOW | MEDIUM | HIGH | FROZEN |")
    lines.append("|---|---|---|---|---|---|")

    # Table rows
    for milestone_id, wave_id in pair_order:
        low = lookup.get((milestone_id, wave_id, "LOW"), 0)
        medium = lookup.get((milestone_id, wave_id, "MEDIUM"), 0)
        high = lookup.get((milestone_id, wave_id, "HIGH"), 0)
        frozen = lookup.get((milestone_id, wave_id, "FROZEN"), 0)
        lines.append(
            f"| {milestone_id} | {wave_id} | {low} | {medium} | {high} | {frozen} |"
        )

    # Summary row
    lines.append(
        f"| **TOTAL** | | "
        f"{packet.risk_summary.get('LOW', 0)} | "
        f"{packet.risk_summary.get('MEDIUM', 0)} | "
        f"{packet.risk_summary.get('HIGH', 0)} | "
        f"{packet.risk_summary.get('FROZEN', 0)} |"
    )
    lines.append("")

    return "\n".join(lines)
