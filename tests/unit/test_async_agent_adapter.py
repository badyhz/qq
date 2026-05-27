import asyncio

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.async_agent_adapter import (
    AsyncAdapterStatus,
    AsyncMockAdapter,
    AsyncTaskResult,
    SyncToAsyncAdapter,
)
from core.agent_adapter import MockAdapter


def test_async_mock_creation():
    a = AsyncMockAdapter("test")
    assert a.adapter_id() == "test"


def test_async_submit_task():
    async def _test():
        a = AsyncMockAdapter()
        req_id = await a.submit_task("T1", "hello")
        assert req_id is not None
        result = await a.poll(req_id)
        assert result.status == AsyncAdapterStatus.COMPLETED
    asyncio.run(_test())


def test_async_poll_completed():
    async def _test():
        a = AsyncMockAdapter(auto_complete=True)
        req_id = await a.submit_task("T2", "prompt")
        result = await a.poll(req_id)
        assert result.status == AsyncAdapterStatus.COMPLETED
        assert result.task_id == "T2"
        assert result.output == "mock output"
        assert result.duration_ms >= 0
    asyncio.run(_test())


def test_async_cancel():
    async def _test():
        a = AsyncMockAdapter(auto_complete=False)
        req_id = await a.submit_task("T3", "prompt")
        cancelled = await a.cancel(req_id)
        assert cancelled is True
        result = await a.poll(req_id)
        assert result.status == AsyncAdapterStatus.CANCELLED
    asyncio.run(_test())


def test_async_status():
    async def _test():
        a = AsyncMockAdapter()
        await a.submit_task("T4", "prompt")
        s = await a.status()
        assert s["adapter_id"] == "async_mock"
        assert s["submitted"] == 1
    asyncio.run(_test())


def test_sync_to_async_adapter_wraps():
    async def _test():
        sync_adapter = MockAdapter("sync_mock")
        a = SyncToAsyncAdapter(sync_adapter)
        assert a.adapter_id() == "sync_mock"
        req_id = await a.submit_task("T5", "hello sync")
        assert req_id is not None
        result = await a.poll(req_id)
        assert result.status == AsyncAdapterStatus.COMPLETED
        assert result.adapter_id == "sync_mock"
    asyncio.run(_test())


def test_task_result_fields():
    async def _test():
        a = AsyncMockAdapter()
        req_id = await a.submit_task("T6", "prompt")
        result = await a.poll(req_id)
        assert hasattr(result, "task_id")
        assert hasattr(result, "adapter_id")
        assert hasattr(result, "status")
        assert hasattr(result, "output")
        assert hasattr(result, "duration_ms")
        assert isinstance(result, AsyncTaskResult)
    asyncio.run(_test())


def test_adapter_id_unique_per_instance():
    a1 = AsyncMockAdapter("a1")
    a2 = AsyncMockAdapter("a2")
    assert a1.adapter_id() != a2.adapter_id()


def test_async_mock_failure_mode():
    async def _test():
        a = AsyncMockAdapter(fail_prob=1.0)
        req_id = await a.submit_task("T7", "will fail")
        result = await a.poll(req_id)
        assert result.status == AsyncAdapterStatus.FAILED
    asyncio.run(_test())


def test_async_lifecycle_full():
    """Full lifecycle: submit -> poll -> cancel -> status check."""
    async def _test():
        a = AsyncMockAdapter(auto_complete=False)
        s = await a.status()
        assert s["submitted"] == 0

        req1 = await a.submit_task("L1", "prompt1")
        req2 = await a.submit_task("L2", "prompt2")
        s = await a.status()
        assert s["submitted"] == 2

        # Poll both (should be RUNNING since auto_complete=False)
        r1 = await a.poll(req1)
        r2 = await a.poll(req2)
        assert r1.status == AsyncAdapterStatus.RUNNING
        assert r2.status == AsyncAdapterStatus.RUNNING

        # Cancel one
        await a.cancel(req1)
        r1 = await a.poll(req1)
        assert r1.status == AsyncAdapterStatus.CANCELLED

        # Other still running
        r2 = await a.poll(req2)
        assert r2.status == AsyncAdapterStatus.RUNNING

        s = await a.status()
        assert s["submitted"] == 2
        assert s["cancelled"] == 1
    asyncio.run(_test())
