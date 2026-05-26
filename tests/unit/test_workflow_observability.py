import time
from core.workflow_observability import (
    WorkflowObservability,
    EventType,
)


def test_emit_event():
    obs = WorkflowObservability()
    event = obs.emit(EventType.TASK_SUBMITTED, task_id="T1", adapter_id="mock")
    assert event.event_type == EventType.TASK_SUBMITTED
    assert event.task_id == "T1"
    assert event.adapter_id == "mock"
    assert isinstance(event.timestamp, float)
    assert len(obs._events) == 1


def test_query_by_type():
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_SUBMITTED, task_id="T1")
    obs.emit(EventType.TASK_STARTED, task_id="T2")
    obs.emit(EventType.TASK_SUBMITTED, task_id="T3")
    results = obs.query(event_type=EventType.TASK_SUBMITTED)
    assert len(results) == 2
    assert all(e.event_type == EventType.TASK_SUBMITTED for e in results)


def test_query_by_task_id():
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_SUBMITTED, task_id="T1")
    obs.emit(EventType.TASK_STARTED, task_id="T1")
    obs.emit(EventType.TASK_SUBMITTED, task_id="T2")
    results = obs.query(task_id="T1")
    assert len(results) == 2
    assert all(e.task_id == "T1" for e in results)


def test_query_combined():
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_SUBMITTED, task_id="T1")
    obs.emit(EventType.TASK_STARTED, task_id="T1")
    obs.emit(EventType.TASK_SUBMITTED, task_id="T2")
    results = obs.query(event_type=EventType.TASK_SUBMITTED, task_id="T1")
    assert len(results) == 1
    assert results[0].task_id == "T1"
    assert results[0].event_type == EventType.TASK_SUBMITTED


def test_task_timeline():
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_SUBMITTED, task_id="T1")
    obs.emit(EventType.TASK_STARTED, task_id="T1")
    obs.emit(EventType.TASK_COMPLETED, task_id="T1")
    timeline = obs.timeline("T1")
    assert len(timeline) == 3
    assert timeline[0]["event"] == "task_submitted"
    assert timeline[1]["event"] == "task_started"
    assert timeline[2]["event"] == "task_completed"
    assert all("timestamp" in t for t in timeline)


def test_duration_calculation():
    obs = WorkflowObservability()
    start = time.time()
    obs.emit(EventType.TASK_STARTED, task_id="T1")
    time.sleep(0.01)
    obs.emit(EventType.TASK_COMPLETED, task_id="T1")
    duration = obs.duration_ms("T1")
    assert duration is not None
    assert duration >= 5


def test_failure_rate():
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_COMPLETED, task_id="T1")
    obs.emit(EventType.TASK_COMPLETED, task_id="T2")
    obs.emit(EventType.TASK_FAILED, task_id="T3")
    assert abs(obs.failure_rate() - 1 / 3) < 1e-9


def test_failure_rate_empty():
    obs = WorkflowObservability()
    assert obs.failure_rate() == 0.0


def test_summary_counts():
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_SUBMITTED, task_id="T1")
    obs.emit(EventType.TASK_STARTED, task_id="T1")
    obs.emit(EventType.TASK_COMPLETED, task_id="T1")
    obs.emit(EventType.TASK_FAILED, task_id="T2")
    s = obs.summary()
    assert s["total"] == 4
    assert s["counts"]["task_submitted"] == 1
    assert s["counts"]["task_completed"] == 1
    assert s["counts"]["task_failed"] == 1


def test_clear_events():
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_SUBMITTED, task_id="T1")
    obs.emit(EventType.TASK_STARTED, task_id="T1")
    obs.clear()
    assert len(obs._events) == 0
    assert obs.query() == []


def test_multiple_events_ordering():
    obs = WorkflowObservability()
    for i in range(5):
        obs.emit(EventType.TASK_SUBMITTED, task_id=f"T{i}")
    events = obs.query()
    assert len(events) == 5
    for i in range(len(events) - 1):
        assert events[i].timestamp <= events[i + 1].timestamp


def test_workflow_events():
    obs = WorkflowObservability()
    obs.emit(EventType.WORKFLOW_STARTED, task_id="W1")
    obs.emit(EventType.WORKFLOW_COMPLETED, task_id="W1")
    results = obs.query(task_id="W1")
    assert len(results) == 2
    assert results[0].event_type == EventType.WORKFLOW_STARTED
    assert results[1].event_type == EventType.WORKFLOW_COMPLETED


def test_metadata_preserved():
    obs = WorkflowObservability()
    obs.emit(
        EventType.SAFETY_VIOLATION,
        task_id="T1",
        adapter_id="mock",
        reason="budget_exceeded",
        limit=1000,
    )
    events = obs.query(event_type=EventType.SAFETY_VIOLATION)
    assert len(events) == 1
    assert events[0].metadata["reason"] == "budget_exceeded"
    assert events[0].metadata["limit"] == 1000
