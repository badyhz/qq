"""Workflow Loader — load workflow definitions from YAML files."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


TEMPLATE_DIR = Path(__file__).parent.parent / "automation" / "workflow_templates"

REQUIRED_FIELDS = ["name", "description", "mode", "tasks", "parallel_policy"]
VALID_MODES = {"DAG", "QUEUE", "CLOSEOUT"}


def load_yaml(path: str | Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def validate_workflow(data: dict) -> list[str]:
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if "mode" in data and data["mode"] not in VALID_MODES:
        errors.append(f"Invalid mode: {data['mode']}. Valid: {VALID_MODES}")

    if "tasks" in data:
        if not isinstance(data["tasks"], list):
            errors.append("Tasks must be a list")
        else:
            task_ids = set()
            for i, task in enumerate(data["tasks"]):
                if "id" not in task:
                    errors.append(f"Task {i} missing 'id'")
                else:
                    if task["id"] in task_ids:
                        errors.append(f"Duplicate task id: {task['id']}")
                    task_ids.add(task["id"])

                if "deps" in task:
                    if not isinstance(task["deps"], list):
                        errors.append(f"Task {task.get('id', i)} deps must be a list")
                    else:
                        for dep in task["deps"]:
                            if dep not in task_ids and dep != task.get("id"):
                                pass  # forward ref ok

    if "parallel_policy" in data:
        policy = data["parallel_policy"]
        if "mode" not in policy:
            errors.append("parallel_policy missing 'mode'")
        if "max_agents" not in policy:
            errors.append("parallel_policy missing 'max_agents'")

    return errors


def normalize_workflow_name(name: str) -> str:
    """Normalize workflow name: lowercase, strip, replace dashes/spaces with underscores."""
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def load_workflow(name: str) -> dict:
    """Load a workflow template by name (case-insensitive).

    Tries YAML first, then Python dict templates from automation.workflow_templates.
    """
    normalized = normalize_workflow_name(name)

    # Try YAML file
    path = TEMPLATE_DIR / f"{normalized}.yaml"
    if path.exists():
        data = load_yaml(path)
        errors = validate_workflow(data)
        if errors:
            raise ValueError(f"Invalid workflow '{name}': {errors}")
        return data

    # Fall back to Python dict templates
    try:
        from automation.workflow_templates import TEMPLATES
        # Try uppercased key first, then normalized
        upper = normalized.upper()
        if upper in TEMPLATES:
            return TEMPLATES[upper]
        for key in TEMPLATES:
            if key.upper() == upper:
                return TEMPLATES[key]
    except ImportError:
        pass

    raise FileNotFoundError(
        f"Workflow template not found: {name!r} "
        f"(tried {path} and automation.workflow_templates)"
    )


def list_workflows() -> list[str]:
    """List all available workflow names (YAML + Python templates)."""
    names = set()
    if TEMPLATE_DIR.exists():
        for f in TEMPLATE_DIR.glob("*.yaml"):
            names.add(f.stem)
    try:
        from automation.workflow_templates import TEMPLATES
        names.update(k.lower() for k in TEMPLATES)
    except ImportError:
        pass
    return sorted(names)


def load_workflow_tasks(name: str) -> list[dict]:
    data = load_workflow(name)
    return data.get("tasks", [])
