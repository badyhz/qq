# PRD 500 Backlog Wave Map — T906

## Purpose

Group a 500-task backlog into execution waves. Each wave is bounded by `max_tasks_per_wave` (default 25). Waves are grouped by milestone, then split into chunks. Risk level drives parallelism caps and routing.

## Files

- `core/prd_500_backlog_wave_map.py` — dataclass + builder + serializers
- `tests/unit/test_prd_500_backlog_wave_map.py` — unit tests

## Key Rules

| Risk     | max_parallel_agents | recommended_route                  |
|----------|---------------------|------------------------------------|
| FROZEN   | 0                   | HUMAN_ONLY                         |
| HIGH     | 3                   | mimo2.5pro with human review       |
| MEDIUM   | 8                   | mimo2.5pro                         |
| LOW      | 8                   | mimo2.5pro or mimo2.5              |

- Mixed-risk milestones: dominant (highest) risk wins for the entire milestone.
- Wave IDs: `{milestone_id}-W{index}`.
- Deterministic: no I/O, no timestamps, no random.

## API

```python
from core.prd_500_backlog_wave_map import (
    build_prd_500_wave_map,
    wave_map_to_dict,
    wave_map_to_markdown,
    summarize_wave_map,
)

entries = build_prd_500_wave_map(backlog, max_tasks_per_wave=25)
summary = summarize_wave_map(entries)
```
