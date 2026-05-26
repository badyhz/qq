"""Integration tests — adapter compatibility suite.

Verifies ALL adapters against the same contract, budget tracking,
retry behavior, circuit breaker, and observability events.
"""
from __future__ import annotations

import pytest

from core.async_agent_adapter import AsyncAdapterStatus, AsyncTaskResult
from core.async_agent_adapter import AsyncMockAdapter
from adapters.claude_sandbox_adapter import ClaudeSandboxAdapter
from adapters.mimo_sandbox_adapter import MiMoSandboxAdapter
from core.workflow_runtime import WorkflowRuntime
from core.workflow_budget import WorkflowBudget
from core.workflow_retry_policy import RetryPolicy
from core.workflow_circuit_breaker import CircuitBreaker, CircuitState
from core.workflow_observability import WorkflowObservability, EventType


# ---------------------------------------------------------------------------
# Shared adapter factory
# ---------------------------------------------------------------------------

ADAPTER_CLASSES = [AsyncMockAdapter, ClaudeSandboxAdapter, MiMoSandboxAdapter]


def _make_adapter(cls, **kwargs):
    """Create adapter with sane defaults for integration tests."""
    if cls is AsyncMockAdapter:
        return cls(adapter_id=kwargs.pop("adapter_id", cls.__name__), **kwargs)
    return cls(**kwargs)


# ===========================================================================
# 1. Async Contract Compliance
# ===========================================================================


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_submit_returns_string_request_id(adapter_cls):
    adapter = _make_adapter(adapter_cls)
    request_id = await adapter.submit_task("t_contract_1", "hello world")
    assert isinstance(request_id, str), f"{adapter_cls.__name__}: submit_task must return str"
    assert len(request_id) > 0


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_poll_returns_task_result(adapter_cls):
    adapter = _make_adapter(adapter_cls)
    request_id = await adapter.submit_task("t_contract_2", "test prompt")
    result = await adapter.poll(request_id)
    assert isinstance(result, AsyncTaskResult), "poll must return AsyncTaskResult"
    assert isinstance(result.status, AsyncAdapterStatus), "status must be AsyncAdapterStatus"
    assert result.status in (
        AsyncAdapterStatus.RUNNING,
        AsyncAdapterStatus.COMPLETED,
        AsyncAdapterStatus.FAILED,
        AsyncAdapterStatus.CANCELLED,
    ), f"status {result.status} not in valid set"
    assert isinstance(result.duration_ms, float)
    assert result.duration_ms >= 0.0


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_poll_returns_valid_task_id(adapter_cls):
    adapter = _make_adapter(adapter_cls)
    request_id = await adapter.submit_task("t_contract_3", "check task_id roundtrip")
    result = await adapter.poll(request_id)
    assert result.task_id == "t_contract_3", "poll must preserve task_id"


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_cancel_returns_bool(adapter_cls):
    adapter = _make_adapter(adapter_cls)
    request_id = await adapter.submit_task("t_contract_4", "cancel me")
    cancelled = await adapter.cancel(request_id)
    assert isinstance(cancelled, bool), "cancel must return bool"


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_cancel_invalid_id_returns_false(adapter_cls):
    adapter = _make_adapter(adapter_cls)
    cancelled = await adapter.cancel("nonexistent-request-id")
    assert cancelled is False, "cancel of unknown request must return False"


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_status_returns_dict(adapter_cls):
    adapter = _make_adapter(adapter_cls)
    st = await adapter.status()
    assert isinstance(st, dict), "status must return dict"
    assert "adapter_id" in st, "status dict must contain 'adapter_id'"
    assert "submitted" in st, "status dict must contain 'submitted'"


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_submit_task_id_propagation(adapter_cls):
    adapter = _make_adapter(adapter_cls)
    request_id = await adapter.submit_task("propagation_test", "check task_id propagation")
    result = await adapter.poll(request_id)
    assert result.task_id == "propagation_test"


# ===========================================================================
# 2. Budget Tracking Integration
# ===========================================================================


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_budget_records_single_task(adapter_cls):
    runtime = WorkflowRuntime()
    adapter = _make_adapter(adapter_cls)
    await adapter.submit_task("t_budget_1", "budget test")
    runtime.record_budget(
        task_id="t_budget_1",
        adapter_id=adapter.adapter_id(),
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.05,
    )
    summary = runtime.budget.summary()
    assert summary["total_entries"] == 1
    assert summary["total_tokens"] == 150
    assert abs(summary["total_cost_usd"] - 0.05) < 1e-9


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_budget_accumulates_multiple_tasks(adapter_cls):
    runtime = WorkflowRuntime()
    adapter = _make_adapter(adapter_cls)
    await adapter.submit_task("t_budget_a", "first")
    await adapter.submit_task("t_budget_b", "second")

    runtime.record_budget("t_budget_a", adapter.adapter_id(), 100, 50, 0.05)
    runtime.record_budget("t_budget_b", adapter.adapter_id(), 200, 80, 0.12)

    summary = runtime.budget.summary()
    assert summary["total_entries"] == 2
    assert summary["total_tokens"] == 430
    assert abs(summary["total_cost_usd"] - 0.17) < 1e-9
    assert summary["status"] == "ok"


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_budget_status_ok_within_limit(adapter_cls):
    runtime = WorkflowRuntime(budget=WorkflowBudget(max_cost_usd=10.0))
    adapter = _make_adapter(adapter_cls)
    await adapter.submit_task("t_budget_ok", "within limit")
    runtime.record_budget("t_budget_ok", adapter.adapter_id(), 10, 5, 0.01)
    assert runtime.budget.check().value == "ok"


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_budget_per_task_breakdown(adapter_cls):
    runtime = WorkflowRuntime()
    adapter = _make_adapter(adapter_cls)
    await adapter.submit_task("t_break", "breakdown test")
    runtime.record_budget("t_break", adapter.adapter_id(), 100, 50, 0.05)
    pt = runtime.budget.per_task_budget("t_break")
    assert pt["task_id"] == "t_break"
    assert pt["entries"] == 1
    assert pt["tokens"] == 150
    assert abs(pt["cost_usd"] - 0.05) < 1e-9


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_budget_per_adapter_breakdown(adapter_cls):
    runtime = WorkflowRuntime()
    adapter = _make_adapter(adapter_cls)
    await adapter.submit_task("t_padapt", "adapter breakdown")
    runtime.record_budget("t_padapt", adapter.adapter_id(), 100, 50, 0.05)
    pa = runtime.budget.per_adapter_budget(adapter.adapter_id())
    assert pa["adapter_id"] == adapter.adapter_id()
    assert pa["entries"] == 1


# ===========================================================================
# 3. Retry Behavior
# ===========================================================================


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_fail_prob_1_returns_failed(adapter_cls):
    adapter = _make_adapter(adapter_cls, fail_prob=1.0)
    request_id = await adapter.submit_task("t_retry_fail", "will fail")
    result = await adapter.poll(request_id)
    # MiMoSandboxAdapter retries internally; with max_retries=3 and fail_prob=1.0,
    # all retries eventually fail
    assert result.status == AsyncAdapterStatus.FAILED


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_fail_prob_0_returns_completed(adapter_cls):
    adapter = _make_adapter(adapter_cls, fail_prob=0.0)
    request_id = await adapter.submit_task("t_retry_ok", "will succeed")
    result = await adapter.poll(request_id)
    assert result.status == AsyncAdapterStatus.COMPLETED


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_retry_state_tracks_failure(adapter_cls):
    """Verify runtime retry state tracks failures from adapter via run_async."""
    policy = RetryPolicy(max_attempts=2, base_backoff=0.0, max_backoff=0.0)
    runtime = WorkflowRuntime(retry_policy=policy)
    adapter = _make_adapter(adapter_cls, fail_prob=1.0)
    runtime.set_adapter(adapter)

    runtime.load_workflow([{"id": "t_retry_state", "deps": []}])
    summary = await runtime.run_async(adapter)

    assert "t_retry_state" in runtime._retry_states
    state = runtime._retry_states["t_retry_state"]
    assert state.attempt > 0


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_success_resets_retry_path(adapter_cls):
    """A fresh adapter with fail_prob=0 succeeds cleanly via run_async."""
    policy = RetryPolicy(max_attempts=2, base_backoff=0.0, max_backoff=0.0)
    runtime = WorkflowRuntime(retry_policy=policy)
    adapter = _make_adapter(adapter_cls, fail_prob=0.0)
    runtime.set_adapter(adapter)

    runtime.load_workflow([{"id": "t_retry_success", "deps": []}])
    summary = await runtime.run_async(adapter)

    # No retry states should exist since task succeeded first attempt
    st = runtime.status()
    assert st["retry_states"] == {} or all(
        s["attempts"] == 0 for s in st["retry_states"].values()
    )


# ===========================================================================
# 4. Circuit Breaker Integration
# ===========================================================================


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_circuit_breaker_opens_after_threshold(adapter_cls):
    """Verify circuit breaker opens when failures exceed threshold."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=999.0)
    policy = RetryPolicy(max_attempts=1, base_backoff=0.0, max_backoff=0.0)
    runtime = WorkflowRuntime(circuit_breaker=cb, retry_policy=policy)
    adapter = _make_adapter(adapter_cls, fail_prob=1.0)
    runtime.set_adapter(adapter)

    # Simulate repeated failures crossing the threshold
    for i in range(3):
        cb.record_failure(f"t_cb_{i}_failed")

    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_circuit_breaker_blocks_when_open(adapter_cls):
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=999.0)
    # Force open
    cb.record_failure("force1")
    cb.record_failure("force2")
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_circuit_breaker_closes_after_success(adapter_cls):
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=999.0)
    cb.record_failure("f1")
    assert cb.state == CircuitState.CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    # Failure count should reset
    assert cb._failure_count == 0


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_circuit_breaker_half_open_recovery(adapter_cls):
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=999.0, half_open_max=1)
    cb.record_failure("trip it")
    assert cb.state == CircuitState.OPEN
    # Manually transition to half_open to test recovery path
    cb._transition(CircuitState.HALF_OPEN, "test half_open")
    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


# ===========================================================================
# 5. Observability Events
# ===========================================================================


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_observability_task_started_event(adapter_cls):
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_STARTED, task_id="t_obs_started")
    events = obs.query(event_type=EventType.TASK_STARTED, task_id="t_obs_started")
    assert len(events) == 1
    assert events[0].task_id == "t_obs_started"


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_observability_task_completed_event(adapter_cls):
    obs = WorkflowObservability()
    adapter = _make_adapter(adapter_cls)
    request_id = await adapter.submit_task("t_obs_completed", "complete me")
    result = await adapter.poll(request_id)
    if result.status == AsyncAdapterStatus.COMPLETED:
        obs.emit(EventType.TASK_COMPLETED, task_id="t_obs_completed")
    events = obs.query(event_type=EventType.TASK_COMPLETED, task_id="t_obs_completed")
    assert len(events) == 1
    assert events[0].task_id == "t_obs_completed"


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_observability_task_failed_event(adapter_cls):
    obs = WorkflowObservability()
    adapter = _make_adapter(adapter_cls, fail_prob=1.0)
    request_id = await adapter.submit_task("t_obs_failed", "will fail")
    result = await adapter.poll(request_id)
    if result.status == AsyncAdapterStatus.FAILED:
        obs.emit(EventType.TASK_FAILED, task_id="t_obs_failed")
    events = obs.query(event_type=EventType.TASK_FAILED, task_id="t_obs_failed")
    assert len(events) == 1
    assert events[0].task_id == "t_obs_failed"


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_observability_full_lifecycle(adapter_cls):
    """Full lifecycle: submit -> started -> complete -> completed."""
    obs = WorkflowObservability()
    adapter = _make_adapter(adapter_cls, fail_prob=0.0)
    request_id = await adapter.submit_task("t_lifecycle", "lifecycle")
    obs.emit(EventType.TASK_STARTED, task_id="t_lifecycle")
    result = await adapter.poll(request_id)
    if result.status == AsyncAdapterStatus.COMPLETED:
        obs.emit(EventType.TASK_COMPLETED, task_id="t_lifecycle")

    events = obs.task_events("t_lifecycle")
    event_types = [e.event_type for e in events]
    assert EventType.TASK_STARTED in event_types
    assert EventType.TASK_COMPLETED in event_types


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_observability_timeline_ordering(adapter_cls):
    """Verify event timeline is in correct chronological order."""
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_STARTED, task_id="t_timeline")
    obs.emit(EventType.TASK_FAILED, task_id="t_timeline")
    timeline = obs.timeline("t_timeline")
    assert len(timeline) == 2
    assert timeline[0]["event"] == "task_started"
    assert timeline[1]["event"] == "task_failed"
    assert timeline[0]["timestamp"] <= timeline[1]["timestamp"]


@pytest.mark.anyio
@pytest.mark.parametrize("adapter_cls", ADAPTER_CLASSES, ids=lambda c: c.__name__)
async def test_observability_failure_rate(adapter_cls):
    obs = WorkflowObservability()
    obs.emit(EventType.TASK_COMPLETED, task_id="a")
    obs.emit(EventType.TASK_COMPLETED, task_id="b")
    obs.emit(EventType.TASK_FAILED, task_id="c")
    assert abs(obs.failure_rate() - 1 / 3) < 1e-9
