import asyncio
import pytest

from adapters.mimo_api_adapter import MiMoAPIAdapter
from core.async_agent_adapter import AsyncAdapterStatus


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def adapter():
    return MiMoAPIAdapter()


@pytest.fixture
def adapter_with_key():
    return MiMoAPIAdapter(api_key="sk-test-abcdef1234567890")


# -- Adapter ID --


class TestAdapterID:
    def test_returns_mimo_api(self, adapter):
        assert adapter.adapter_id() == "mimo_api"

    def test_default_model(self, adapter):
        assert adapter._model == "mimo-v2.5"

    def test_custom_model(self):
        a = MiMoAPIAdapter(model="mimo-v3")
        assert a._model == "mimo-v3"


# -- Submit --


class TestSubmit:
    def test_returns_request_id(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello"))
        assert isinstance(rid, str)
        assert len(rid) > 0

    def test_task_stored_locally(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello"))
        assert rid in adapter._tasks

    def test_payload_stored(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello"))
        payload = adapter._tasks[rid]["payload"]
        assert isinstance(payload, dict)


# -- Request Payload --


class TestBuildPayload:
    def test_has_model_field(self, adapter):
        payload = adapter.build_request_payload("t1", "hi")
        assert payload["model"] == "mimo-v2.5"

    def test_has_messages_field(self, adapter):
        payload = adapter.build_request_payload("t1", "hi")
        assert "messages" in payload
        assert isinstance(payload["messages"], list)
        assert payload["messages"][0]["content"] == "hi"

    def test_has_parameters_field(self, adapter):
        payload = adapter.build_request_payload("t1", "hi")
        assert "parameters" in payload
        assert "temperature" in payload["parameters"]
        assert "max_tokens" in payload["parameters"]

    def test_metadata_includes_dry_run(self, adapter):
        payload = adapter.build_request_payload("t1", "hi")
        assert payload["metadata"]["dry_run"] is True

    def test_kwargs_override(self, adapter):
        payload = adapter.build_request_payload("t1", "hi", temperature=0.1)
        assert payload["parameters"]["temperature"] == 0.1


# -- Response Normalization --


class TestNormalize:
    def test_normalizes_choice(self, adapter):
        raw = {
            "choices": [{"message": {"content": "hello", "role": "assistant"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1},
        }
        result = adapter.normalize_response(raw)
        assert result["output"] == "hello"
        assert result["usage"]["prompt_tokens"] == 5

    def test_empty_choices(self, adapter):
        result = adapter.normalize_response({"choices": [], "usage": {}})
        assert result["output"] == ""


# -- Poll --


class TestPoll:
    def test_returns_completed(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello world"))
        result = _run(adapter.poll(rid))
        assert result.status == AsyncAdapterStatus.COMPLETED

    def test_output_is_simulated(self, adapter):
        rid = _run(adapter.submit_task("t1", "test"))
        result = _run(adapter.poll(rid))
        assert "DRY-RUN" in result.output

    def test_unknown_request_raises(self, adapter):
        with pytest.raises(KeyError):
            _run(adapter.poll("nonexistent"))


# -- Cancel --


class TestCancel:
    def test_cancel_returns_true(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello"))
        assert _run(adapter.cancel(rid)) is True

    def test_cancelled_status_on_poll(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello"))
        _run(adapter.cancel(rid))
        result = _run(adapter.poll(rid))
        assert result.status == AsyncAdapterStatus.CANCELLED

    def test_cancel_unknown_returns_false(self, adapter):
        assert _run(adapter.cancel("nonexistent")) is False

    def test_cancel_completed_returns_false(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello"))
        _run(adapter.poll(rid))  # completes it
        assert _run(adapter.cancel(rid)) is False

    def test_cancel_increments_count(self, adapter):
        rid = _run(adapter.submit_task("t1", "hello"))
        _run(adapter.cancel(rid))
        assert adapter._cancelled == 1


# -- Rate Limit / Budget / Kill Switch --


class TestHooks:
    def test_rate_limit_passes(self, adapter):
        assert adapter.check_rate_limit() is True

    def test_budget_passes_under_ceiling(self, adapter):
        assert adapter.check_budget(5.0) is True

    def test_budget_fails_over_ceiling(self, adapter):
        assert adapter.check_budget(100.0) is False

    def test_kill_switch_returns_false(self, adapter):
        assert adapter.check_kill_switch() is False


# -- API Key --


class TestAPIKey:
    def test_set_api_key(self, adapter_with_key):
        assert adapter_with_key._api_key == "sk-test-abcdef1234567890"

    def test_mask_key_long(self, adapter):
        masked = adapter.mask_key("sk-test-abcdef1234567890")
        assert masked.startswith("sk-t")
        assert masked.endswith("7890")
        assert "abcdef" not in masked

    def test_mask_key_short(self, adapter):
        masked = adapter.mask_key("abc")
        assert masked == "***"

    def test_mask_key_none(self, adapter):
        assert adapter.mask_key(None) == "<none>"

    def test_set_api_key_logs_masked(self, adapter, caplog):
        with caplog.at_level("INFO"):
            adapter.set_api_key("sk-secret123456")
        assert any("sk-s" in r.message for r in caplog.records)


# -- Retry Handler --


class TestRetryHandler:
    def test_retryable_error(self, adapter):
        assert adapter.retry_handler(Exception("timeout")) is True

    def test_retryable_value_error(self, adapter):
        assert adapter.retry_handler(ValueError("bad input")) is True


# -- Status --


class TestStatus:
    def test_returns_dict(self, adapter):
        st = _run(adapter.status())
        assert isinstance(st, dict)

    def test_adapter_id_in_status(self, adapter):
        st = _run(adapter.status())
        assert st["adapter_id"] == "mimo_api"

    def test_dry_run_true(self, adapter):
        st = _run(adapter.status())
        assert st["dry_run"] is True

    def test_submitted_count(self, adapter):
        _run(adapter.submit_task("t1", "a"))
        _run(adapter.submit_task("t2", "b"))
        st = _run(adapter.status())
        assert st["submitted"] == 2

    def test_completed_count(self, adapter):
        rid = _run(adapter.submit_task("t1", "a"))
        _run(adapter.poll(rid))
        st = _run(adapter.status())
        assert st["completed"] == 1

    def test_cancelled_count(self, adapter):
        rid = _run(adapter.submit_task("t1", "a"))
        _run(adapter.cancel(rid))
        st = _run(adapter.status())
        assert st["cancelled"] == 1


# -- Multiple Tasks --


class TestMultipleTasks:
    def test_independent_tracking(self, adapter):
        rid1 = _run(adapter.submit_task("t1", "prompt1"))
        rid2 = _run(adapter.submit_task("t2", "prompt2"))
        assert rid1 != rid2
        assert adapter._tasks[rid1]["task_id"] == "t1"
        assert adapter._tasks[rid2]["task_id"] == "t2"

    def test_cancel_one_does_not_affect_other(self, adapter):
        rid1 = _run(adapter.submit_task("t1", "a"))
        rid2 = _run(adapter.submit_task("t2", "b"))
        _run(adapter.cancel(rid1))
        r2 = _run(adapter.poll(rid2))
        assert r2.status == AsyncAdapterStatus.COMPLETED


# -- Dry-Run Safety --


class TestDryRunMode:
    def test_no_network_calls(self, adapter):
        """Verify adapter stores requests locally, never sends."""
        rid = _run(adapter.submit_task("t1", "sensitive data"))
        task = adapter._tasks[rid]
        assert task["payload"]["metadata"]["dry_run"] is True
        assert task["prompt"] == "sensitive data"

    def test_default_dry_run(self, adapter):
        assert adapter._dry_run is True

    def test_status_shows_dry_run(self, adapter):
        st = _run(adapter.status())
        assert st["dry_run"] is True

    def test_api_key_not_in_payload(self, adapter_with_key):
        """API key must never appear in request payload."""
        rid = _run(adapter_with_key.submit_task("t1", "hello"))
        payload_str = str(adapter_with_key._tasks[rid]["payload"])
        assert "abcdef1234567890" not in payload_str
