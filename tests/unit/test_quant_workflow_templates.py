"""Tests for Quant Workflow Templates."""
from __future__ import annotations

import pytest

from automation.workflow_templates import TEMPLATES, get_template
from core.workflow_loader import load_workflow, list_workflows, validate_workflow
from core.workflow_runtime import WorkflowRuntime


# --- Template Registry ---


def test_all_quant_templates_registered():
    assert "SIGNAL_SCAN_PIPELINE" in TEMPLATES
    assert "EXECUTION_GUARD_DOCS_SYNC" in TEMPLATES
    assert "QUANT_CLOSEOUT_PIPELINE" in TEMPLATES
    assert "SAFE_READONLY_AUDIT" in TEMPLATES


def test_template_count():
    assert len(TEMPLATES) == 7


def test_get_template():
    t = get_template("SIGNAL_SCAN_PIPELINE")
    assert t["name"] == "SIGNAL_SCAN_PIPELINE"


def test_get_template_unknown():
    with pytest.raises(ValueError):
        get_template("NONEXISTENT")


# --- SIGNAL_SCAN_PIPELINE ---


def test_signal_scan_pipeline_structure():
    t = TEMPLATES["SIGNAL_SCAN_PIPELINE"]
    assert t["mode"] == "DAG"
    assert len(t["tasks"]) == 6
    assert t["parallel_policy"]["mode"] == "DAG"
    assert "safety_policy" in t


def test_signal_scan_pipeline_deps():
    t = TEMPLATES["SIGNAL_SCAN_PIPELINE"]
    task_ids = {task["id"] for task in t["tasks"]}
    for task in t["tasks"]:
        for dep in task["deps"]:
            assert dep in task_ids


def test_signal_scan_pipeline_safety_policy():
    t = TEMPLATES["SIGNAL_SCAN_PIPELINE"]
    policy = t["safety_policy"]
    assert "SUBMIT" in policy["blocked_categories"]
    assert "LIVE_EXECUTION" in policy["blocked_categories"]
    assert "READONLY" in policy["allowed_categories"]


def test_signal_scan_pipeline_loadable():
    tasks = load_workflow("SIGNAL_SCAN_PIPELINE")["tasks"]
    assert len(tasks) == 6


# --- EXECUTION_GUARD_DOCS_SYNC ---


def test_docs_sync_structure():
    t = TEMPLATES["EXECUTION_GUARD_DOCS_SYNC"]
    assert t["mode"] == "DAG"
    assert len(t["tasks"]) == 4
    assert t["parallel_policy"]["max_agents"] == 3


def test_docs_sync_deps():
    t = TEMPLATES["EXECUTION_GUARD_DOCS_SYNC"]
    task_ids = {task["id"] for task in t["tasks"]}
    for task in t["tasks"]:
        for dep in task["deps"]:
            assert dep in task_ids


def test_docs_sync_safety_policy():
    t = TEMPLATES["EXECUTION_GUARD_DOCS_SYNC"]
    assert "SUBMIT" in t["safety_policy"]["blocked_categories"]
    assert "DOCS" in t["safety_policy"]["allowed_categories"]


# --- QUANT_CLOSEOUT_PIPELINE ---


def test_quant_closeout_structure():
    t = TEMPLATES["QUANT_CLOSEOUT_PIPELINE"]
    assert t["mode"] == "QUEUE"
    assert len(t["tasks"]) == 6
    assert t["parallel_policy"]["max_agents"] == 1


def test_quant_closeout_deps():
    t = TEMPLATES["QUANT_CLOSEOUT_PIPELINE"]
    task_ids = {task["id"] for task in t["tasks"]}
    for task in t["tasks"]:
        for dep in task["deps"]:
            assert dep in task_ids


def test_quant_closeout_sequential_chain():
    t = TEMPLATES["QUANT_CLOSEOUT_PIPELINE"]
    tasks = t["tasks"]
    for i in range(1, len(tasks)):
        assert tasks[i]["deps"] == [tasks[i - 1]["id"]]


def test_quant_closeout_safety_policy():
    t = TEMPLATES["QUANT_CLOSEOUT_PIPELINE"]
    assert "CLOSEOUT" in t["safety_policy"]["allowed_categories"]
    assert "SUBMIT" in t["safety_policy"]["blocked_categories"]


# --- YAML Loader ---


def test_load_signal_scan_yaml():
    data = load_workflow("signal_scan_pipeline")
    assert data["name"] == "SIGNAL_SCAN_PIPELINE"
    assert len(data["tasks"]) == 6


def test_validate_signal_scan():
    data = load_workflow("signal_scan_pipeline")
    errors = validate_workflow(data)
    assert errors == []


def test_list_workflows_includes_quant():
    names = list_workflows()
    assert "signal_scan_pipeline" in names
    assert "execution_guard_docs_sync" in names
    assert "quant_closeout_pipeline" in names


# --- Runtime Integration ---


def test_signal_scan_pipeline_runtime():
    rt = WorkflowRuntime(max_workers=5, mode="DAG")
    tasks = load_workflow("SIGNAL_SCAN_PIPELINE")["tasks"]
    result = rt.load_workflow(tasks, workflow_id="dogfood-signal-scan")
    assert result["valid"]
    summary = rt.run()
    assert summary["is_complete"]
    assert summary["total_tasks"] == 6


def test_docs_sync_pipeline_runtime():
    rt = WorkflowRuntime(max_workers=3, mode="DAG")
    tasks = load_workflow("EXECUTION_GUARD_DOCS_SYNC")["tasks"]
    result = rt.load_workflow(tasks, workflow_id="dogfood-docs-sync")
    assert result["valid"]
    summary = rt.run()
    assert summary["is_complete"]
    assert summary["total_tasks"] == 4


def test_quant_closeout_pipeline_runtime():
    rt = WorkflowRuntime(max_workers=1, mode="QUEUE")
    tasks = load_workflow("QUANT_CLOSEOUT_PIPELINE")["tasks"]
    result = rt.load_workflow(tasks, workflow_id="dogfood-closeout")
    assert result["valid"]
    summary = rt.run()
    assert summary["is_complete"]
    assert summary["total_tasks"] == 6
