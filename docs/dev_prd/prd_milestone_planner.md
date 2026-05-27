# PRD Milestone Planner — T874

## Purpose

Group backlog items into execution milestones with risk aggregation and execution mode recommendation.

## Dataclass

### PrdMilestone (frozen=True)

| Field | Type | Description |
|---|---|---|
| milestone_id | str | Auto-generated: `MS-{first_task}-{last_task}` |
| title | str | Human-readable label |
| task_ids | List[str] | Ordered task IDs in this milestone |
| risk_level | str | Aggregated: FROZEN > HIGH > MEDIUM > LOW |
| status | str | Milestone status (defaults to NOT_STARTED) |
| dependencies | List[str] | External dependencies (not satisfied within milestone) |
| recommended_execution_mode | str | SMALL_BATCH / PRO_MULTI_WAVE / HUMAN_REVIEW_REQUIRED |
| notes | List[str] | Auto-generated metadata notes |

## Functions

### plan_milestones_from_backlog(items, max_tasks_per_milestone=50) -> List[PrdMilestone]

Core planner. Sorts items by task number, splits into chunks of max size, computes risk and execution mode per chunk.

### milestone_to_dict / milestones_to_dict

Serialize to plain dicts.

### milestone_to_markdown / milestones_to_markdown

Deterministic markdown output.

### summarize_milestones(milestones) -> Dict

Returns counts: total_milestones, total_tasks, risk_counts, execution_mode_counts.

## Risk Aggregation Rules

1. Any FROZEN item => milestone is FROZEN
2. Else any HIGH => milestone is HIGH
3. Else any MEDIUM => milestone is MEDIUM
4. Else LOW

## Execution Mode Rules

| Condition | Mode |
|---|---|
| risk == FROZEN | HUMAN_REVIEW_REQUIRED |
| task_count <= 15 | SMALL_BATCH |
| task_count 16-50 | PRO_MULTI_WAVE |

## Constraints

- Pure, deterministic, no I/O, no timestamps, no random.
- Preserves task order by task number.
