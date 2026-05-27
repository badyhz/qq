"""Runtime async integration tests for WorkflowRuntime + AsyncAgentAdapter."""
import asyncio
from unittest.mock import MagicMock

from core.workflow_runtime import WorkflowRuntime
from core.async_agent_adapter import AsyncMockAdapter, AsyncAgentAdapter, AsyncAdapterStatus
from core.workflow_observability import EventType


def test_runtime_has_set_adapter():
    rt = WorkflowRuntime()
    assert hasattr(rt, "set_adapter")
    assert callable(rt.set_adapter)


def test_runtime_default_no_adapter():
    rt = WorkflowRuntime()
    assert rt._adapter is None


def test_runtime_accepts_async_mock_adapter():
    rt = WorkflowRuntime()
    adapter = AsyncMockAdapter()
    rt.set_adapter(adapter)
    assert rt._adapter is adapter
    assert isinstance(rt._adapter, AsyncAgentAdapter)


def test_run_async_completes_all_tasks():
    async def _test():
        rt = WorkflowRuntime(max_workers=3)
        load = rt.load_workflow([
            {"id": "T1", "deps": []},
            {"id": "T2", "deps": []},
        ])
        assert load["valid"]
        result = await rt.run_async(AsyncMockAdapter())
        assert result["is_complete"]
        assert result["completed"] == 2
    asyncio.run(_test())


def test_run_async_with_custom_adapter():
    async def _test():
        rt = WorkflowRuntime(max_workers=2)
        rt.load_workflow([
            {"id": "A1", "deps": []},
            {"id": "A2", "deps": ["A1"]},
        ])
        adapter = AsyncMockAdapter(adapter_id="custom_v2", auto_complete=True)
        result = await rt.run_async(adapter)
        assert result["is_complete"]
        assert adapter.adapter_id() == "custom_v2"
        status = await adapter.status()
        assert status["submitted"] >= 2
    asyncio.run(_test())


def test_run_async_emits_workflow_events():
    async def _test():
        rt = WorkflowRuntime(max_workers=2)
        rt.load_workflow([
            {"id": "E1", "deps": []},
            {"id": "E2", "deps": []},
        ])
        await rt.run_async(AsyncMockAdapter())
        summary = rt.observability.summary()
        counts = summary["counts"]
        assert counts.get("workflow_started", 0) >= 1
        assert counts.get("workflow_completed", 0) >= 1
        assert counts.get("task_started", 0) >= 2
        assert counts.get("task_completed", 0) >= 2
    asyncio.run(_test())


def test_run_async_records_execution_log():
    async def _test():
        rt = WorkflowRuntime(max_workers=2)
        rt.load_workflow([
            {"id": "L1", "deps": []},
            {"id": "L2", "deps": []},
        ])
        result = await rt.run_async(AsyncMockAdapter())
        # run_async does not extend execution_log directly;
        # verify completion via observability and summary
        assert result["completed"] == 2
        completed_events = rt.observability.query(
            event_type=EventType.TASK_COMPLETED
        )
        assert len(completed_events) == 2
        completed_ids = {e.task_id for e in completed_events}
        assert completed_ids == {"L1", "L2"}
    asyncio.run(_test())
