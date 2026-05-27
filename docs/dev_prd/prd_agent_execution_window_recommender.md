# T879 — PRD Agent Execution Window Recommender

## Purpose

Recommend safe task execution window sizes based on risk level and dependency density.

## Status

- T879: DONE

## Location

- `core/prd_agent_execution_window_recommender.py`
- `tests/unit/test_prd_agent_execution_window_recommender.py`

## Dataclass

### PrdExecutionWindowRecommendation (frozen=True)

| Field | Type | Description |
|---|---|---|
| risk_level | str | LOW / MEDIUM / HIGH / FROZEN |
| dependency_density | str | low / medium / high |
| recommended_task_count_min | int | Minimum tasks in window |
| recommended_task_count_max | int | Maximum tasks in window |
| recommended_agent_count_max | int | Max concurrent agents |
| recommended_route | str | Recommended model route |
| hard_stop_required | bool | Whether human gate is required |
| notes | List[str] | Warnings and context |

## Window Table

| Risk | Density | Min-Max Tasks | Max Agents | Route |
|---|---|---|---|---|
| LOW | low | 20-50 | 8 | mimo2.5pro or mimo2.5 |
| LOW | medium | 15-40 | 7 | mimo2.5pro or mimo2.5 |
| LOW | high | 10-30 | 6 | mimo2.5pro |
| MEDIUM | low | 10-30 | 6 | mimo2.5pro |
| MEDIUM | medium | 8-25 | 5 | mimo2.5pro |
| MEDIUM | high | 5-20 | 4 | mimo2.5pro |
| HIGH | low | 3-10 | 3 | mimo2.5pro with human review |
| HIGH | medium | 2-8 | 2 | mimo2.5pro with human review |
| HIGH | high | 1-5 | 2 | mimo2.5pro with human review |
| FROZEN | * | 0 | 0 | HUMAN_ONLY |

## Functions

### recommend_execution_window(risk_level, dependency_density) -> PrdExecutionWindowRecommendation

Lookup table call. Validates inputs. Pure, deterministic.

### recommend_window_for_tasks(items: List[PrdBacklogItem]) -> PrdExecutionWindowRecommendation

- Selects highest risk level from items.
- Computes dependency density: ratio of items with dependencies.
  - >= 50%: high
  - >= 20%: medium
  - < 20%: low
- Empty list defaults to LOW/low.

### execution_window_to_dict(rec) -> Dict

Serialize to plain dict. Notes is a copy (safe to mutate).

### execution_window_to_markdown(rec) -> str

Render as markdown table with optional notes section.

## Rules

- Pure: no I/O, no timestamps, no random.
- Frozen dataclass: immutable after construction.
- FROZEN blocks all automation (0 tasks, 0 agents, HUMAN_ONLY).
- HIGH requires hard stop / human review.
- Mixed tasks: highest risk wins.
- Dependency density thresholds: 0.2 (medium), 0.5 (high).

## Tests

```bash
python3 -m pytest tests/unit/test_prd_agent_execution_window_recommender.py -v
```

23 tests. All pass. Coverage: all risk levels, all density levels, empty input, mixed risk, frozen dataclass, serializer copy safety, determinism.
