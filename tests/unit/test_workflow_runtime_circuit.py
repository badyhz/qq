"""Integration tests for WorkflowRuntime circuit breaker integration."""
from core.workflow_runtime import WorkflowRuntime
from core.workflow_circuit_breaker import CircuitBreaker, CircuitState
from core.workflow_budget import WorkflowBudget


def test_runtime_has_circuit_breaker():
    rt = WorkflowRuntime()
    assert hasattr(rt, "circuit_breaker")


def test_runtime_default_circuit_breaker():
    rt = WorkflowRuntime()
    assert isinstance(rt.circuit_breaker, CircuitBreaker)
    assert rt.circuit_breaker.state == CircuitState.CLOSED


def test_custom_circuit_breaker_injected():
    cb = CircuitBreaker(failure_threshold=2)
    rt = WorkflowRuntime(circuit_breaker=cb)
    assert rt.circuit_breaker is cb
    assert rt.circuit_breaker.failure_threshold == 2


def test_successful_run_circuit_stays_closed():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "T1", "deps": []}])
    result = rt.run()
    assert rt.circuit_breaker.state == CircuitState.CLOSED
    assert result["circuit_state"] == CircuitState.CLOSED.value


def test_budget_exceeded_opens_circuit():
    b = WorkflowBudget(max_cost_usd=0.001)
    rt = WorkflowRuntime(budget=b, circuit_breaker=CircuitBreaker(failure_threshold=1))
    rt.record_budget("T1", "mock", 0, 0, 0.01)
    assert rt.circuit_breaker.state == CircuitState.OPEN


def test_circuit_open_blocks_run_step():
    cb = CircuitBreaker(failure_threshold=0)
    cb.trip("test")
    rt = WorkflowRuntime(circuit_breaker=cb)
    rt.load_workflow([{"id": "T1", "deps": []}])
    step = rt.run_step()
    assert rt.circuit_breaker.state == CircuitState.OPEN
    assert "T1" in step["assigned"]
    # T1 was blocked — not in execution log
    assert len(rt.execution_log) == 0


def test_circuit_breaker_in_status_report():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "T1", "deps": []}])
    rt.run()
    status = rt.status()
    assert "circuit_breaker" in status
    assert "state" in status["circuit_breaker"]
    assert "failure_threshold" in status["circuit_breaker"]
