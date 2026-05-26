"""Unit tests for ClaudeSandboxAdapter."""

import json
import pytest

from adapters.claude_sandbox_adapter import ClaudeSandboxAdapter
from core.async_agent_adapter import AsyncAdapterStatus


@pytest.fixture
def adapter():
    return ClaudeSandboxAdapter()


@pytest.fixture
def failing_adapter():
    return ClaudeSandboxAdapter(fail_prob=1.0)


@pytest.mark.anyio
async def test_adapter_id(adapter):
    assert adapter.adapter_id() == "claude_sandbox"


@pytest.mark.anyio
async def test_submit_returns_request_id(adapter):
    rid = await adapter.submit_task("t1", "hello")
    assert isinstance(rid, str)
    assert len(rid) > 0


@pytest.mark.anyio
async def test_poll_returns_completed(adapter):
    rid = await adapter.submit_task("t1", "hello")
    result = await adapter.poll(rid)
    assert result.status == AsyncAdapterStatus.COMPLETED


@pytest.mark.anyio
async def test_response_contains_simulated_content(adapter):
    rid = await adapter.submit_task("t1", "test prompt")
    result = await adapter.poll(rid)
    body = json.loads(result.output)
    assert body["content"] == "sandbox response"
    assert body["model"] == "claude-sonnet-4-20250514"


@pytest.mark.anyio
async def test_token_tracking(adapter):
    rid = await adapter.submit_task("t1", "12345678")
    result = await adapter.poll(rid)
    body = json.loads(result.output)
    assert body["tokens"]["input"] == 2  # 8 chars // 4
    assert body["tokens"]["output"] == 50
    summary = adapter.token_summary()
    assert summary["total_input_tokens"] == 2
    assert summary["total_output_tokens"] == 50


@pytest.mark.anyio
async def test_cancel(adapter):
    rid = await adapter.submit_task("t1", "hello")
    cancelled = await adapter.cancel(rid)
    assert cancelled is True
    result = await adapter.poll(rid)
    assert result.status == AsyncAdapterStatus.CANCELLED


@pytest.mark.anyio
async def test_status_returns_counts(adapter):
    rid1 = await adapter.submit_task("t1", "a")
    rid2 = await adapter.submit_task("t2", "b")
    await adapter.poll(rid1)
    await adapter.poll(rid2)
    st = await adapter.status()
    assert st["adapter_id"] == "claude_sandbox"
    assert st["submitted"] == 2
    assert st["completed"] == 2
    assert st["failed"] == 0
    assert st["cancelled"] == 0


@pytest.mark.anyio
async def test_random_failure_with_fail_prob_1(failing_adapter):
    rid = await failing_adapter.submit_task("t1", "hello")
    result = await failing_adapter.poll(rid)
    assert result.status == AsyncAdapterStatus.FAILED
    st = await failing_adapter.status()
    assert st["failed"] == 1


@pytest.mark.anyio
async def test_latency_is_configurable():
    import time
    fast = ClaudeSandboxAdapter(latency_ms=1.0)
    start = time.monotonic()
    await fast.submit_task("t1", "hi")
    elapsed = (time.monotonic() - start) * 1000
    assert elapsed < 50  # should be ~1ms, well under 50


@pytest.mark.anyio
async def test_multiple_tasks_tracked_independently(adapter):
    rid1 = await adapter.submit_task("t1", "aaa")
    rid2 = await adapter.submit_task("t2", "bbbbbbbb")
    r1 = await adapter.poll(rid1)
    r2 = await adapter.poll(rid2)
    b1 = json.loads(r1.output)
    b2 = json.loads(r2.output)
    assert r1.task_id == "t1"
    assert r2.task_id == "t2"
    assert b1["tokens"]["input"] == 0  # 3 // 4
    assert b2["tokens"]["input"] == 2  # 8 // 4
    assert adapter.token_summary()["total_input_tokens"] == 2


@pytest.mark.anyio
async def test_poll_unknown_request_raises(adapter):
    with pytest.raises(KeyError):
        await adapter.poll("nonexistent")
