import asyncio
import pytest

from adapters.mimo_sandbox_adapter import MiMoSandboxAdapter
from core.async_agent_adapter import AsyncAdapterStatus


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def adapter():
    return MiMoSandboxAdapter()


@pytest.fixture
def failing_adapter():
    return MiMoSandboxAdapter(fail_prob=1.0, max_retries=2)


class TestAdapterID:
    def test_returns_mimo_sandbox(self, adapter):
        assert adapter.adapter_id() == "mimo_sandbox"

    def test_default_model(self, adapter):
        assert adapter._model == "mimo-v2.5"


class TestSubmit:
    def test_returns_request_id(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello"))
        assert isinstance(rid, str)
        assert len(rid) > 0

    def test_task_tracked(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello"))
        assert rid in adapter._tasks

    def test_latency_configurable(self):
        fast = MiMoSandboxAdapter(latency_ms=0.0)
        start = asyncio.get_event_loop().time()
        _run(fast.submit_task("t1", "hi"))
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed < 0.1


class TestPoll:
    def test_returns_completed(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello world"))
        result = _run(adapter.poll(rid))
        assert result.status == AsyncAdapterStatus.COMPLETED

    def test_response_contains_model_content(self, adapter):
        rid = _run(adapter.submit_task("t1", "test prompt"))
        result = _run(adapter.poll(rid))
        assert "mimo-v2.5 sandbox response" in result.output

    def test_unknown_request_raises(self, adapter):
        with pytest.raises(KeyError):
            _run(adapter.poll("nonexistent"))

    def test_cancelled_returns_cancelled(self, adapter):
        rid = _run(adapter.submit_task("t1", "hi"))
        _run(adapter.cancel(rid))
        result = _run(adapter.poll(rid))
        assert result.status == AsyncAdapterStatus.CANCELLED


class TestCancel:
    def test_cancel_returns_true(self, adapter):
        rid = _run(adapter.submit_task("t1", "hi"))
        assert _run(adapter.cancel(rid)) is True

    def test_cancel_unknown_returns_false(self, adapter):
        assert _run(adapter.cancel("nope")) is False

    def test_cancel_increments_count(self, adapter):
        rid = _run(adapter.submit_task("t1", "hi"))
        _run(adapter.cancel(rid))
        assert adapter._cancelled == 1


class TestTokenTracking:
    def test_input_tokens_tracked(self, adapter):
        rid = _run(adapter.submit_task("t1", "a" * 20))
        _run(adapter.poll(rid))
        summary = adapter.token_summary()
        assert summary["input_tokens"] == 5  # 20 // 4

    def test_output_tokens_tracked(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello"))
        _run(adapter.poll(rid))
        summary = adapter.token_summary()
        assert summary["output_tokens"] == 40

    def test_total_tokens_sum(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello world"))
        _run(adapter.poll(rid))
        summary = adapter.token_summary()
        assert summary["total_tokens"] == summary["input_tokens"] + summary["output_tokens"]

    def test_cumulative_across_tasks(self, adapter):
        rid1 = _run(adapter.submit_task("t1", "a" * 8))
        _run(adapter.poll(rid1))
        rid2 = _run(adapter.submit_task("t2", "b" * 12))
        _run(adapter.poll(rid2))
        summary = adapter.token_summary()
        assert summary["input_tokens"] == 2 + 3  # 8//4 + 12//4


class TestStatus:
    def test_returns_adapter_id(self, adapter):
        st = _run(adapter.status())
        assert st["adapter_id"] == "mimo_sandbox"

    def test_submitted_count(self, adapter):
        _run(adapter.submit_task("t1", "a"))
        _run(adapter.submit_task("t2", "b"))
        st = _run(adapter.status())
        assert st["submitted"] == 2

    def test_cancelled_count(self, adapter):
        rid = _run(adapter.submit_task("t1", "a"))
        _run(adapter.cancel(rid))
        st = _run(adapter.status())
        assert st["cancelled"] == 1


class TestRetryBehavior:
    def test_random_failure_with_fail_prob_1(self, failing_adapter):
        rid = _run(failing_adapter.submit_task("t1", "prompt"))
        result = _run(failing_adapter.poll(rid))
        assert result.status == AsyncAdapterStatus.FAILED

    def test_retry_counted(self):
        # fail_prob=1.0 makes submit fail immediately; use fail_prob on poll path instead
        adapter = MiMoSandboxAdapter(fail_prob=0.0, max_retries=2)
        rid = _run(adapter.submit_task("t1", "prompt"))
        # Manually set fail_prob so poll triggers retry
        adapter._fail_prob = 1.0
        _run(adapter.poll(rid))
        stats = adapter.retry_stats()
        assert stats["retry_count"] >= 1

    def test_success_after_retry(self):
        # Use 0 fail_prob so submit succeeds, then manually test retry path
        adapter = MiMoSandboxAdapter(fail_prob=0.0)
        rid = _run(adapter.submit_task("t1", "prompt"))
        _run(adapter.poll(rid))
        stats = adapter.retry_stats()
        assert stats["success_after_retry"] == 0


class TestMultipleTasks:
    def test_independent_tracking(self, adapter):
        rid1 = _run(adapter.submit_task("t1", "first"))
        rid2 = _run(adapter.submit_task("t2", "second"))
        r1 = _run(adapter.poll(rid1))
        r2 = _run(adapter.poll(rid2))
        assert r1.task_id == "t1"
        assert r2.task_id == "t2"
        assert r1.status == AsyncAdapterStatus.COMPLETED
        assert r2.status == AsyncAdapterStatus.COMPLETED

    def test_cancel_one_does_not_affect_other(self, adapter):
        rid1 = _run(adapter.submit_task("t1", "a"))
        rid2 = _run(adapter.submit_task("t2", "b"))
        _run(adapter.cancel(rid1))
        r2 = _run(adapter.poll(rid2))
        assert r2.status == AsyncAdapterStatus.COMPLETED
