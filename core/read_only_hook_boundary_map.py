"""Read-only hook boundary map — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class BoundaryEntry:
    component: str
    access_level: str  # "allowed", "forbidden", "restricted"
    reason: str


def build_boundary_map() -> List[BoundaryEntry]:
    return [
        BoundaryEntry("data_feed", "forbidden", "Read-only hooks must not trigger data fetches"),
        BoundaryEntry("signal_engine", "forbidden", "Signal generation is a mutation path"),
        BoundaryEntry("risk_manager", "restricted", "Query-only; no state changes permitted"),
        BoundaryEntry("execution", "forbidden", "Execution triggers real orders"),
        BoundaryEntry("order_manager", "forbidden", "Order mutations are write operations"),
        BoundaryEntry("trade_logger", "restricted", "Read-only query of logged trades allowed"),
        BoundaryEntry("config_loader", "allowed", "Reading config is safe for read-only hooks"),
        BoundaryEntry("logger", "restricted", "Log reading allowed; log writing is a side effect"),
        BoundaryEntry("evidence_recorder", "allowed", "Evidence records are read-only artifacts"),
        BoundaryEntry("prd_task_model", "allowed", "Task model queries are read-only"),
    ]


def boundary_entry_to_dict(entry: BoundaryEntry) -> dict:
    return {
        "component": entry.component,
        "access_level": entry.access_level,
        "reason": entry.reason,
    }
