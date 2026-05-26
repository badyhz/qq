"""Tests for Workflow Loader."""
from __future__ import annotations

import os

import pytest

from core.workflow_loader import (
    load_workflow,
    load_workflow_tasks,
    list_workflows,
    validate_workflow,
)


def test_list_workflows():
    workflows = list_workflows()
    assert "safe_readonly_audit" in workflows
    assert "guard_injection_batch" in workflows
    assert "docs_sync_wave" in workflows
    assert "engineering_closeout" in workflows


def test_load_workflow():
    data = load_workflow("safe_readonly_audit")
    assert data["name"] == "SAFE_READONLY_AUDIT"
    assert data["mode"] == "DAG"
    assert len(data["tasks"]) == 5


def test_load_workflow_tasks():
    tasks = load_workflow_tasks("guard_injection_batch")
    assert len(tasks) == 5
    assert tasks[0]["id"] == "inject_scripts"


def test_validate_workflow_valid():
    data = {
        "name": "test",
        "description": "test workflow",
        "mode": "DAG",
        "tasks": [{"id": "T1", "deps": []}],
        "parallel_policy": {"mode": "DAG", "max_agents": 5, "rules": []},
    }
    errors = validate_workflow(data)
    assert errors == []


def test_validate_workflow_missing_name():
    data = {"description": "test", "mode": "DAG", "tasks": [], "parallel_policy": {"mode": "DAG", "max_agents": 5, "rules": []}}
    errors = validate_workflow(data)
    assert any("name" in e for e in errors)


def test_validate_workflow_invalid_mode():
    data = {"name": "test", "description": "test", "mode": "INVALID", "tasks": [], "parallel_policy": {"mode": "DAG", "max_agents": 5, "rules": []}}
    errors = validate_workflow(data)
    assert any("mode" in e for e in errors)


def test_validate_workflow_duplicate_task_ids():
    data = {
        "name": "test",
        "description": "test",
        "mode": "DAG",
        "tasks": [{"id": "T1", "deps": []}, {"id": "T1", "deps": []}],
        "parallel_policy": {"mode": "DAG", "max_agents": 5, "rules": []},
    }
    errors = validate_workflow(data)
    assert any("Duplicate" in e for e in errors)


def test_load_nonexistent():
    with pytest.raises(FileNotFoundError):
        load_workflow("nonexistent_workflow")


def test_all_yaml_files_valid():
    from pathlib import Path
    template_dir = Path(__file__).parent.parent.parent / "automation" / "workflow_templates"
    for yaml_file in template_dir.glob("*.yaml"):
        data = load_workflow(yaml_file.stem)
        assert "name" in data
        assert "tasks" in data
