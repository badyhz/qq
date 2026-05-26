"""T733 — Runtime Budget Integration Tests."""
import pytest
from core.workflow_runtime import WorkflowRuntime
from core.workflow_budget import WorkflowBudget, BudgetExceeded, BudgetStatus
from core.workflow_circuit_breaker import CircuitBreaker, CircuitState
from core.workflow_observability import EventType


def test_runtime_has_budget():
    rt = WorkflowRuntime()
    assert hasattr(rt, "budget")
    assert isinstance(rt.budget, WorkflowBudget)


def test_runtime_default_budget():
    rt = WorkflowRuntime()
    b = rt.budget
    assert b.max_tokens == 1_000_000
    assert b.max_cost_usd == 100.0
    assert b.check() == BudgetStatus.OK


def test_custom_budget_injected():
    b = WorkflowBudget(max_tokens=1000, max_cost_usd=5.0)
    rt = WorkflowRuntime(budget=b)
    assert rt.budget.max_tokens == 1000
    assert rt.budget.max_cost_usd == 5.0


def test_record_budget_reduces_remaining():
    rt = WorkflowRuntime()
    before = rt.budget.remaining()
    rt.record_budget("T1", "mock", 100, 50, 0.01)
    after = rt.budget.remaining()
    assert after["tokens"] < before["tokens"]
    assert after["cost_usd"] < before["cost_usd"]
    assert rt.budget._total_cost == pytest.approx(0.01)


def test_budget_exceeded_trips_circuit():
    b = WorkflowBudget(max_cost_usd=0.001)
    cb = CircuitBreaker(failure_threshold=1)
    rt = WorkflowRuntime(budget=b, circuit_breaker=cb)
    rt.record_budget("T1", "mock", 0, 0, 0.01)
    assert rt.circuit_breaker.state == CircuitState.OPEN


def test_budget_exceeded_emits_event():
    b = WorkflowBudget(max_cost_usd=0.001)
    rt = WorkflowRuntime(budget=b)
    rt.record_budget("T1", "mock", 0, 0, 0.01)
    events = rt.observability._events
    budget_events = [e for e in events if e.event_type == EventType.BUDGET_EXCEEDED]
    assert len(budget_events) >= 1
    assert budget_events[0].task_id == "T1"


def test_budget_in_status_report():
    rt = WorkflowRuntime()
    rt.record_budget("T1", "mock", 100, 200, 0.05)
    status = rt.status()
    assert "budget" in status
    assert status["budget"]["total_tokens"] == 300
    assert status["budget"]["total_cost_usd"] == pytest.approx(0.05)
    assert status["budget"]["status"] == BudgetStatus.OK.value
