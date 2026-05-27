# PRD 500 Backlog Risk Map

**T909.** Deterministic risk summary for 500+ item backlogs.

## Purpose

Summarize backlog risk distribution and recommend execution posture.

## Module

`core/prd_500_backlog_risk_map.py`

## Data

- `Prd500RiskMap` (frozen dataclass): counts by risk level, human review count, recommended action, notes.

## Functions

| Function | Input | Output |
|---|---|---|
| `build_prd_500_risk_map` | `PrdBacklog` | `Prd500RiskMap` |
| `risk_map_to_dict` | `Prd500RiskMap` | `dict` |
| `risk_map_to_markdown` | `Prd500RiskMap` | `str` |

## Rules

- Count items by `risk_level`: LOW, MEDIUM, HIGH, FROZEN.
- `human_review_required_count` = FROZEN + HIGH count.
- `recommended_action`:
  - frozen > 0: `"HUMAN_REVIEW_REQUIRED before any execution"`
  - high > 0: `"STAGED_EXECUTION with human review for HIGH"`
  - else: `"PROCEED with standard safety"`

## Constraints

Pure deterministic. No I/O. No timestamps. No random.
