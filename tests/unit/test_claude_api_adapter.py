"""Unit tests for ClaudeAPIAdapter (skeleton / dry-run mode)."""

import json
import pytest

from adapters.claude_api_adapter import ClaudeAPIAdapter
from core.async_agent_adapter import AsyncAdapterStatus


@pytest.fixture
def adapter():
    return ClaudeAPIAdapter()


@pytest.fixture
def adapter_with_key():
    return ClaudeAPIAdapter(api_key="sk-ant-abcdefghijklmnopqrstuvwxyz12345678")


# ── Contract / identity ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_adapter_id(adapter):
    assert adapter.adapter_id() == "claude_api"


@pytest.mark.anyio
async def test_returns_request_id(adapter):
    rid = await adapter.submit_task("t1", "hello")
    assert isinstance(rid, str)
    assert len(rid) > 0


# ── Payload structure ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_request_payload_has_required_fields(adapter):
    rid = await adapter.submit_task("t1", "test prompt")
    req = adapter._requests[rid]
    payload = req["payload"]
    assert "model" in payload
    assert "messages" in payload
    assert "max_tokens" in payload
    assert isinstance(payload["messages"], list)
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "test prompt"


@pytest.mark.anyio
async def test_request_payload_model_matches_init(adapter):
    rid = await adapter.submit_task("t1", "hi")
    payload = adapter._requests[rid]["payload"]
    assert payload["model"] == "claude-sonnet-4-20250514"


@pytest.mark.anyio
async def test_request_payload_custom_max_tokens():
    a = ClaudeAPIAdapter()
    rid = await a.submit_task("t1", "hi", max_tokens=1024)
    payload = a._requests[rid]["payload"]
    assert payload["max_tokens"] == 1024


@pytest.mark.anyio
async def test_request_payload_includes_task_metadata(adapter):
    rid = await adapter.submit_task("t1", "hi")
    payload = adapter._requests[rid]["payload"]
    assert payload["metadata"]["task_id"] == "t1"


# ── Response parsing ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_poll_returns_completed(adapter):
    rid = await adapter.submit_task("t1", "hello")
    result = await adapter.poll(rid)
    assert result.status == AsyncAdapterStatus.COMPLETED


@pytest.mark.anyio
async def test_poll_output_is_json(adapter):
    rid = await adapter.submit_task("t1", "hello")
    result = await adapter.poll(rid)
    body = json.loads(result.output)
    assert "text" in body
    assert "model" in body
    assert "input_tokens" in body
    assert "output_tokens" in body
    assert "estimated_cost_usd" in body


@pytest.mark.anyio
async def test_parse_response_normalizes_format(adapter):
    raw = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "hello"}],
        "model": "claude-sonnet-4-20250514",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    parsed = adapter.parse_response(raw)
    assert parsed["id"] == "msg_test"
    assert parsed["text"] == "hello"
    assert parsed["input_tokens"] == 10
    assert parsed["output_tokens"] == 5
    assert parsed["stop_reason"] == "end_turn"
    assert isinstance(parsed["estimated_cost_usd"], float)


# ── Guard hooks ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_rate_limit_passes_in_skeleton(adapter):
    assert adapter.check_rate_limit() is True


@pytest.mark.anyio
async def test_budget_check_passes_in_skeleton(adapter):
    assert adapter.check_budget(0.01) is True


@pytest.mark.anyio
async def test_kill_switch_returns_false(adapter):
    assert adapter.check_kill_switch() is False


# ── API key management ───────────────────────────────────────────────


def test_set_api_key_stores_key(adapter):
    adapter.set_api_key("sk-test-12345")
    assert adapter._api_key == "sk-test-12345"


def test_mask_key_normal():
    masked = ClaudeAPIAdapter.mask_key("sk-ant-api03-abcdefghij")
    assert masked.startswith("sk-...")
    assert masked.endswith("hij")
    assert "abcdefgh" not in masked


def test_mask_key_short():
    assert ClaudeAPIAdapter.mask_key("ab") == "****"


def test_mask_key_none():
    assert ClaudeAPIAdapter.mask_key(None) == "****"


# ── Status ───────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_status_returns_correct_counts(adapter):
    await adapter.submit_task("t1", "a")
    await adapter.submit_task("t2", "b")
    st = await adapter.status()
    assert st["adapter_id"] == "claude_api"
    assert st["submitted"] == 2
    assert st["completed"] == 2
    assert st["model"] == "claude-sonnet-4-20250514"
    assert st["dry_run"] is True


@pytest.mark.anyio
async def test_status_includes_token_counts(adapter):
    await adapter.submit_task("t1", "1234")
    st = await adapter.status()
    assert st["total_input_tokens"] > 0


# ── Cancel ───────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_cancel_works(adapter):
    # Cancel a completed request (already done) — should return False
    rid = await adapter.submit_task("t1", "hello")
    # Request completes immediately in dry-run, so cancel on completed = False
    cancelled = await adapter.cancel(rid)
    assert cancelled is False


@pytest.mark.anyio
async def test_cancel_unknown_returns_false(adapter):
    cancelled = await adapter.cancel("nonexistent")
    assert cancelled is False


# ── Multiple tasks ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_multiple_tasks_tracked_independently(adapter):
    rid1 = await adapter.submit_task("t1", "aaa")
    rid2 = await adapter.submit_task("t2", "bbbbbbbb")
    r1 = await adapter.poll(rid1)
    r2 = await adapter.poll(rid2)
    assert r1.task_id == "t1"
    assert r2.task_id == "t2"
    assert r1.status == AsyncAdapterStatus.COMPLETED
    assert r2.status == AsyncAdapterStatus.COMPLETED


# ── Dry-run safety ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_dry_run_flag_always_true(adapter):
    st = await adapter.status()
    assert st["dry_run"] is True


@pytest.mark.anyio
async def test_no_real_http_adapter(adapter):
    """Adapter must not import or use requests/httpx/aiohttp."""
    import inspect
    source = inspect.getsource(ClaudeAPIAdapter)
    for forbidden in ["requests.get", "requests.post", "aiohttp", "httpx"]:
        assert forbidden not in source, f"Found forbidden import: {forbidden}"


# ── Cost estimation ──────────────────────────────────────────────────


@pytest.mark.anyio
async def test_budget_exceeded_after_accumulation():
    a = ClaudeAPIAdapter(budget_ceiling_usd=0.001)
    # Submit enough to accumulate cost
    for i in range(5):
        rid = await a.submit_task(f"t{i}", "x" * 4000)
    st = await a.status()
    assert st["total_cost_usd"] > 0.001
    assert a.check_budget(0.0) is False
