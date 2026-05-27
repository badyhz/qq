"""PRD 500 backlog JSON pack — deterministic serialization of all 500 maps.

T913. Pure deterministic. No I/O. No timestamps. No random.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List

from core.prd_backlog_schema import PrdBacklog, backlog_to_dict, summarize_backlog
from core.prd_500_backlog_milestone_map import (
    build_prd_500_milestone_map,
    milestone_map_to_dict,
)
from core.prd_500_backlog_wave_map import (
    build_prd_500_wave_map,
    wave_map_to_dict,
)
from core.prd_500_backlog_batch_map import (
    build_prd_500_batch_map,
    batch_map_to_dict,
)
from core.prd_500_backlog_dependency_map import (
    build_prd_500_dependency_map,
    dependency_map_to_dict,
)
from core.prd_500_backlog_risk_map import (
    build_prd_500_risk_map,
    risk_map_to_dict,
)


# --- Dataclass ---


@dataclass(frozen=True)
class Prd500JsonPack:
    backlog: dict
    milestone_map: list
    wave_map: list
    batch_map: list
    dependency_map: dict
    risk_map: dict
    final_verdict: str
    notes: List[str]


# --- Builder ---


def build_prd_500_json_pack(backlog: PrdBacklog) -> Prd500JsonPack:
    """Build a Prd500JsonPack from a PrdBacklog. Pure deterministic."""
    backlog_dict = backlog_to_dict(backlog)

    milestone_entries = build_prd_500_milestone_map(backlog)
    milestone_list = [milestone_map_to_dict(e) for e in milestone_entries]

    wave_entries = build_prd_500_wave_map(backlog)
    wave_list = [wave_map_to_dict(e) for e in wave_entries]

    batch_entries = build_prd_500_batch_map(backlog)
    batch_list = [batch_map_to_dict(e) for e in batch_entries]

    dep_map = build_prd_500_dependency_map(backlog)
    dep_dict = dependency_map_to_dict(dep_map)

    risk_map = build_prd_500_risk_map(backlog)
    risk_dict = risk_map_to_dict(risk_map)

    # Derive final_verdict: worst of dependency + risk
    verdict_priority = {"PASS": 0, "WARN": 1, "BLOCKED": 2, "FAIL": 3}
    dep_verdict = verdict_priority.get(dep_map.final_verdict, 0)

    risk_action = risk_map.recommended_action
    if "HUMAN_REVIEW_REQUIRED" in risk_action:
        risk_verdict = 2
    elif "STAGED_EXECUTION" in risk_action:
        risk_verdict = 1
    else:
        risk_verdict = 0

    worst = max(dep_verdict, risk_verdict)
    final_verdict_map = {0: "PASS", 1: "WARN", 2: "BLOCKED", 3: "FAIL"}
    final_verdict = final_verdict_map[worst]

    notes: List[str] = []
    if dep_map.notes:
        notes.extend(dep_map.notes)
    if risk_map.notes:
        notes.extend(risk_map.notes)
    if not notes:
        notes.append("all checks passed")

    return Prd500JsonPack(
        backlog=backlog_dict,
        milestone_map=milestone_list,
        wave_map=wave_list,
        batch_map=batch_list,
        dependency_map=dep_dict,
        risk_map=risk_dict,
        final_verdict=final_verdict,
        notes=notes,
    )


# --- Serializers ---


def json_pack_to_dict(pack: Prd500JsonPack) -> Dict[str, Any]:
    """Convert Prd500JsonPack to plain dict. Pure."""
    return {
        "backlog": pack.backlog,
        "milestone_map": pack.milestone_map,
        "wave_map": pack.wave_map,
        "batch_map": pack.batch_map,
        "dependency_map": pack.dependency_map,
        "risk_map": pack.risk_map,
        "final_verdict": pack.final_verdict,
        "notes": list(pack.notes),
    }


def json_pack_to_string(pack: Prd500JsonPack) -> str:
    """Serialize Prd500JsonPack to deterministic JSON string."""
    return json.dumps(json_pack_to_dict(pack), sort_keys=True)
