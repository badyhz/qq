# PRD Task Risk Classifier

## Purpose

Classify task risk from title, notes, allowed files, and forbidden files. Pure, deterministic, no I/O.

## Risk Levels

| Level | Condition | allowed_for_agent |
|-------|-----------|-------------------|
| FROZEN | Contains: live trading, real submit, secrets, api key, exchange client, account mutation, planner autonomous | false |
| HIGH | Contains: runtime integration, hook implementation, file writer, cli execution, network | true |
| MEDIUM | Contains: validator, parser, prompt generator, dependency graph | true |
| LOW | Default (docs/tests/static report) | true |

## API

```python
from core.prd_task_risk_classifier import (
    classify_prd_task_risk,
    classify_backlog_item_risk,
    risk_classification_to_dict,
    risk_classification_to_markdown,
)

# Direct classification
result = classify_prd_task_risk(
    task_id="T001",
    title="Build YAML parser",
    notes=["needs validation"],
    allowed_files=["src/parse.py"],
)

# From backlog item (dict or object)
result = classify_backlog_item_risk({"task_id": "T002", "title": "Write docs"})

# Serialize
risk_classification_to_dict(result)
risk_classification_to_markdown(result)
```

## Dataclass

`PrdTaskRiskClassification` (frozen=True):
- task_id: str
- risk_level: str
- reasons: List[str]
- recommended_controls: List[str]
- allowed_for_agent: bool
