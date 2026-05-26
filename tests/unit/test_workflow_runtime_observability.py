"""T736 — Runtime observability integration tests."""

from core.workflow_runtime import WorkflowRuntime
from core.workflow_observability import EventType


def test_runtime_has_observability():
    rt = WorkflowRuntime()
    assert hasattr(rt, "observability")
    assert hasattr(rt.observability, "emit")
    assert hasattr(rt.observability, "query")


def test_load_workflow_emits_events():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "T1", "deps": []}])
    events = rt.observability.query(event_type=EventType.WORKFLOW_STARTED)
    assert len(events) >= 1
    inner = events[0].metadata.get("metadata", {})
    assert inner.get("task_count") == 1


def test_run_emits_task_events():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "T1", "deps": []}])
    rt.run()
    completed = rt.observability.query(event_type=EventType.TASK_COMPLETED)
    assert len(completed) >= 1
    assert completed[0].task_id == "T1"


def test_run_step_emits_started_completed():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "T1", "deps": []}])
    step = rt.run_step()
    started = rt.observability.query(event_type=EventType.TASK_STARTED)
    completed = rt.observability.query(event_type=EventType.TASK_COMPLETED)
    assert len(started) >= 1
    assert len(completed) >= 1
    assert started[0].task_id == "T1"
    assert completed[0].task_id == "T1"


def test_safety_violation_emitted():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "submit_order", "deps": []}])
    violations = rt.observability.query(event_type=EventType.SAFETY_VIOLATION)
    assert len(violations) >= 1
    inner = violations[0].metadata.get("metadata", {})
    assert "submit_order" in inner.get("detail", "")


def test_observability_in_status_report():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "T1", "deps": []}])
    status = rt.status()
    assert "observability" in status
    assert "total" in status["observability"]
    assert status["observability"]["total"] >= 1


def test_observability_summary_in_run_result():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "T1", "deps": []}])
    result = rt.run()
    assert "observability_summary" in result
    summary = result["observability_summary"]
    assert "total" in summary
    assert "counts" in summary
    assert summary["total"] >= 3  # WORKFLOW_STARTED x2 + TASK_COMPLETED + WORKFLOW_COMPLETED
