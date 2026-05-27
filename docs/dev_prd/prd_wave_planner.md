# PRD Wave Planner — T875

## Purpose

Split a `PrdMilestone` into execution waves. Each wave is a bounded batch of tasks with risk-aware parallelism and route selection.

## Data Model

### PrdWave (frozen dataclass)

| Field                | Type       | Description                              |
|----------------------|------------|------------------------------------------|
| wave_id              | str        | e.g. `MS-T001-T025-W0`                  |
| milestone_id         | str        | Parent milestone ID                      |
| task_ids             | List[str]  | Tasks in this wave                       |
| max_parallel_agents  | int        | Max concurrent agents (risk-dependent)   |
| dependency_notes     | List[str]  | External dependency warnings             |
| risk_level           | str        | LOW / MEDIUM / HIGH / FROZEN             |
| recommended_route    | str        | mimo2.5 / mimo2.5pro / HUMAN_ONLY       |
| notes                | List[str]  | Wave metadata                            |

## Parallelism Rules

| Risk    | Max Parallel Agents |
|---------|---------------------|
| LOW     | 8                   |
| MEDIUM  | 8                   |
| HIGH    | 3                   |
| FROZEN  | 0                   |

## Route Selection

| Condition                    | Route       |
|------------------------------|-------------|
| FROZEN                       | HUMAN_ONLY  |
| HIGH or external deps        | mimo2.5pro  |
| LOW/MEDIUM, no ext deps      | mimo2.5     |

## Functions

- `plan_waves_for_milestone(milestone, max_tasks_per_wave=10)` - Core splitter
- `wave_to_dict(wave)` / `waves_to_dict(waves)` - Dict serialization
- `wave_to_markdown(wave)` / `waves_to_markdown(waves)` - Markdown output
- `summarize_waves(waves)` - Aggregate stats

## Constraints

- Pure, deterministic, no I/O, no timestamps, no random
- Default max 10 tasks per wave
- Task order preserved from milestone
