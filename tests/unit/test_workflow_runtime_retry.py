from core.workflow_runtime import WorkflowRuntime
from core.workflow_retry_policy import RetryPolicy, TaskRetryState, FailureType


def test_runtime_has_retry_policy():
    rt = WorkflowRuntime()
    assert hasattr(rt, 'retry_policy')
    assert isinstance(rt.retry_policy, RetryPolicy)


def test_runtime_default_retry_policy():
    rt = WorkflowRuntime()
    assert rt.retry_policy.max_attempts == 3
    assert rt.retry_policy.timeout_seconds == 30.0


def test_custom_retry_policy_injected():
    p = RetryPolicy(max_attempts=5, timeout_seconds=60.0)
    rt = WorkflowRuntime(retry_policy=p)
    assert rt.retry_policy.max_attempts == 5
    assert rt.retry_policy.timeout_seconds == 60.0


def test_retry_states_tracked():
    rt = WorkflowRuntime()
    assert rt._retry_states == {}
    assert isinstance(rt._retry_states, dict)


def test_retry_policy_in_status_report():
    rt = WorkflowRuntime()
    rt.load_workflow([{"id": "T1", "deps": []}])
    rt.run()
    status = rt.status()
    assert "retry_states" in status
    assert isinstance(status["retry_states"], dict)
