"""Integration tests for Runtime Dogfood Runner.

Exercises WorkflowRuntime against quant templates (SIGNAL_SCAN_PIPELINE, SAFE_READONLY_AUDIT).
Simulation only. No real trading, no real API calls.
"""
from __future__ import annotations

import pytest

from core.workflow_runtime import WorkflowRuntime
from automation.workflow_templates import TEMPLATES


# --- SIGNAL_SCAN_PIPELINE ---


def test_signal_scan_pipeline_completes():
    """Run SIGNAL_SCAN_PIPELINE through WorkflowRuntime and verify completion."""
    template = TEMPLATES["SIGNAL_SCAN_PIPELINE"]
    rt = WorkflowRuntime(max_workers=5, mode=template.get("mode", "DAG"))

    load = rt.load_workflow(template["tasks"], workflow_id="SIGNAL_SCAN_PIPELINE")
    assert load["valid"], f"Load failed: {load}"

    result = rt.run()
    assert result["is_complete"]
    assert result["total_tasks"] == 6
    assert result["completed"] == 6


def test_signal_scan_pipeline_all_tasks_pass():
    """Verify all SIGNAL_SCAN_PIPELINE tasks complete with PASS status."""
    template = TEMPLATES["SIGNAL_SCAN_PIPELINE"]
    rt = WorkflowRuntime(max_workers=5, mode=template.get("mode", "DAG"))

    rt.load_workflow(template["tasks"], workflow_id="SIGNAL_SCAN_PIPELINE")
    rt.run()

    status = rt.status()
    assert status["status_counts"].get("PASS") == 6


def test_signal_scan_pipeline_observability_events():
    """Verify observability events were emitted for SIGNAL_SCAN_PIPELINE."""
    template = TEMPLATES["SIGNAL_SCAN_PIPELINE"]
    rt = WorkflowRuntime(max_workers=5, mode=template.get("mode", "DAG"))

    rt.load_workflow(template["tasks"], workflow_id="SIGNAL_SCAN_PIPELINE")
    result = rt.run()

    obs = result["observability_summary"]
    assert obs["total"] > 0
    assert obs["counts"].get("workflow_started", 0) >= 1
    assert obs["counts"].get("workflow_completed", 0) >= 1


# --- SAFE_READONLY_AUDIT ---


def test_safe_readonly_audit_completes():
    """Run SAFE_READONLY_AUDIT through WorkflowRuntime and verify completion."""
    template = TEMPLATES["SAFE_READONLY_AUDIT"]
    rt = WorkflowRuntime(max_workers=5, mode=template.get("mode", "DAG"))

    load = rt.load_workflow(template["tasks"], workflow_id="SAFE_READONLY_AUDIT")
    assert load["valid"], f"Load failed: {load}"

    result = rt.run()
    assert result["is_complete"]
    assert result["total_tasks"] == 5
    assert result["completed"] == 5


def test_safe_readonly_audit_all_tasks_pass():
    """Verify all SAFE_READONLY_AUDIT tasks complete with PASS status."""
    template = TEMPLATES["SAFE_READONLY_AUDIT"]
    rt = WorkflowRuntime(max_workers=5, mode=template.get("mode", "DAG"))

    rt.load_workflow(template["tasks"], workflow_id="SAFE_READONLY_AUDIT")
    rt.run()

    status = rt.status()
    assert status["status_counts"].get("PASS") == 5


def test_safe_readonly_audit_observability_events():
    """Verify observability events were emitted for SAFE_READONLY_AUDIT."""
    template = TEMPLATES["SAFE_READONLY_AUDIT"]
    rt = WorkflowRuntime(max_workers=5, mode=template.get("mode", "DAG"))

    rt.load_workflow(template["tasks"], workflow_id="SAFE_READONLY_AUDIT")
    result = rt.run()

    obs = result["observability_summary"]
    assert obs["total"] > 0
    assert obs["counts"].get("workflow_started", 0) >= 1
    assert obs["counts"].get("workflow_completed", 0) >= 1


# --- BUDGET TRACKING ---


def test_budget_tracking_records_and_summarizes():
    """Verify budget tracking works: record_budget + budget summary."""
    template = TEMPLATES["SIGNAL_SCAN_PIPELINE"]
    rt = WorkflowRuntime(max_workers=5, mode=template.get("mode", "DAG"))

    rt.load_workflow(template["tasks"], workflow_id="SIGNAL_SCAN_PIPELINE")

    # Record budget entries
    rt.record_budget("fetch_market_data", "adapter_0", 500, 200, 0.01)
    rt.record_budget("compute_indicators", "adapter_1", 800, 300, 0.02)

    status = rt.status()
    budget = status["budget"]
    assert budget["total_entries"] == 2
    assert budget["total_tokens"] == 1800
    assert budget["total_cost_usd"] == pytest.approx(0.03, abs=1e-6)
    assert budget["status"] == "ok"

    # Run should still report budget status
    result = rt.run()
    assert result["budget_status"] == "ok"


# --- CIRCUIT BREAKER ---


def test_circuit_breaker_starts_closed():
    """Verify circuit breaker starts in CLOSED state."""
    rt = WorkflowRuntime(max_workers=5, mode="DAG")
    assert rt.circuit_breaker.state.value == "closed"

    template = TEMPLATES["SIGNAL_SCAN_PIPELINE"]
    rt.load_workflow(template["tasks"], workflow_id="SIGNAL_SCAN_PIPELINE")
    result = rt.run()

    # After successful run, circuit stays closed
    assert result["circuit_state"] == "closed"


def test_circuit_breaker_status_summary():
    """Verify circuit breaker status summary structure."""
    rt = WorkflowRuntime(max_workers=5, mode="DAG")
    status = rt.status()
    cb = status["circuit_breaker"]

    assert cb["state"] == "closed"
    assert cb["failure_count"] == 0
    assert cb["success_count"] == 0
    assert "failure_threshold" in cb
    assert "recovery_timeout" in cb
