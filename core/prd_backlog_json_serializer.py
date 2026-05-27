"""PRD backlog JSON serialization — stable dict output with sorted keys.

T891. Pure deterministic, no I/O, no timestamps, no random.
"""

import json
from collections import OrderedDict
from typing import Any, Dict, List

from core.prd_backlog_schema import (
    PrdBacklog,
    PrdBacklogItem,
    backlog_item_to_dict,
    backlog_to_dict,
    summarize_backlog,
)


def _sorted_dict(d: Dict[str, Any]) -> OrderedDict:
    """Recursively sort all dict keys alphabetically."""
    result = OrderedDict()
    for key in sorted(d.keys()):
        value = d[key]
        if isinstance(value, dict):
            result[key] = _sorted_dict(value)
        else:
            result[key] = value
    return result


def serialize_backlog_item_to_stable_dict(item: PrdBacklogItem) -> OrderedDict:
    """Serialize a single backlog item to a dict with sorted keys."""
    raw = backlog_item_to_dict(item)
    return _sorted_dict(raw)


def serialize_backlog_to_stable_dict(backlog: PrdBacklog) -> OrderedDict:
    """Serialize backlog to stable dict with sorted keys, summary, and milestone grouping.

    Output structure:
    {
        "backlog_id": ...,
        "items": [...sorted item dicts...],
        "milestone_groups": { milestone_id: [item dicts] },
        "notes": [...],
        "status": ...,
        "summary": { summarize_backlog output, sorted },
        "total_expected_tasks": ...
    }
    """
    items = [serialize_backlog_item_to_stable_dict(i) for i in backlog.items]

    # Build milestone-grouped view
    milestone_groups: Dict[str, List[OrderedDict]] = {}
    for item in backlog.items:
        mid = item.milestone_id
        if mid not in milestone_groups:
            milestone_groups[mid] = []
        milestone_groups[mid].append(serialize_backlog_item_to_stable_dict(item))
    sorted_milestone_groups = OrderedDict()
    for key in sorted(milestone_groups.keys()):
        sorted_milestone_groups[key] = milestone_groups[key]

    summary = _sorted_dict(summarize_backlog(backlog))

    raw = {
        "backlog_id": backlog.backlog_id,
        "items": items,
        "milestone_groups": sorted_milestone_groups,
        "notes": list(backlog.notes),
        "status": backlog.status,
        "summary": summary,
        "total_expected_tasks": backlog.total_expected_tasks,
    }
    return _sorted_dict(raw)


def serialize_backlog_collection(backlogs: List[PrdBacklog]) -> List[OrderedDict]:
    """Serialize a list of backlogs. Output sorted by backlog_id."""
    serialized = [serialize_backlog_to_stable_dict(b) for b in backlogs]
    serialized.sort(key=lambda d: d["backlog_id"])
    return serialized


def validate_serialization_roundtrip(backlog: PrdBacklog) -> bool:
    """Verify that serializing the same backlog twice produces identical output.

    Uses json.dumps(sort_keys=True) for string comparison.
    """
    first = json.dumps(serialize_backlog_to_stable_dict(backlog), sort_keys=True)
    second = json.dumps(serialize_backlog_to_stable_dict(backlog), sort_keys=True)
    return first == second
