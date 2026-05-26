import pytest
from core.agent_adapter import (
    AdapterStatus,
    TaskResult,
    MockAdapter,
    ClaudeAdapter,
    MiMoAdapter,
    CodexAdapter,
)


def test_mock_adapter_creation():
    a = MockAdapter("test_mock")
    assert a.adapter_id() == "test_mock"
    assert a.status()["adapter_id"] == "test_mock"


def test_mock_submit_task():
    a = MockAdapter("test_mock")
    req_id = a.submit_task("t1", "hello")
    assert isinstance(req_id, str)
    assert len(req_id) > 0


def test_mock_poll_completed():
    a = MockAdapter("test_mock", auto_complete=True)
    req_id = a.submit_task("t1", "prompt")
    result = a.poll(req_id)
    assert result.status == AdapterStatus.COMPLETED
    assert result.task_id == "t1"
    assert result.output == "mock output"
    assert result.duration_ms >= 0


def test_mock_cancel():
    a = MockAdapter("test_mock")
    req_id = a.submit_task("t1", "prompt")
    assert a.cancel(req_id) is True
    assert a.status()["cancelled"] == 1


def test_mock_status():
    a = MockAdapter("test_mock")
    a.submit_task("t1", "prompt")
    s = a.status()
    assert s["adapter_id"] == "test_mock"
    assert s["submitted"] == 1


def test_claude_adapter_raises():
    a = ClaudeAdapter()
    with pytest.raises(NotImplementedError):
        a.adapter_id()


def test_mimo_adapter_raises():
    a = MiMoAdapter()
    with pytest.raises(NotImplementedError):
        a.adapter_id()


def test_codex_adapter_raises():
    a = CodexAdapter()
    with pytest.raises(NotImplementedError):
        a.adapter_id()


def test_task_result_fields():
    r = TaskResult(
        task_id="t1",
        adapter_id="mock",
        status=AdapterStatus.COMPLETED,
        output="out",
        duration_ms=12.5,
    )
    assert r.task_id == "t1"
    assert r.status == AdapterStatus.COMPLETED
    assert r.duration_ms == 12.5


def test_adapter_id_unique_per_instance():
    a1 = MockAdapter("a1")
    a2 = MockAdapter("a2")
    assert a1.adapter_id() != a2.adapter_id()
