"""Unit tests for core.workflow_outputs."""

import time

import pytest

from core.workflow_outputs import MissingOutputError, OutputType, WorkflowOutputBus


@pytest.fixture
def bus():
    return WorkflowOutputBus()


class TestPublishConsumeRoundTrip:
    def test_basic_roundtrip(self, bus):
        bus.publish_output("wf1", "t1", {"val": 42})
        result = bus.consume_output("wf1", "t1")
        assert result["data"] == {"val": 42}
        assert result["task_id"] == "t1"
        assert result["output_type"] == OutputType.JSON
        assert isinstance(result["timestamp"], float)

    def test_overwrite_same_task(self, bus):
        bus.publish_output("wf1", "t1", {"round": 1})
        bus.publish_output("wf1", "t1", {"round": 2})
        result = bus.consume_output("wf1", "t1")
        assert result["data"] == {"round": 2}


class TestMissingOutputError:
    def test_consume_nonexistent_raises(self, bus):
        with pytest.raises(MissingOutputError):
            bus.consume_output("wf1", "t1")

    def test_consume_empty_bus(self, bus):
        with pytest.raises(MissingOutputError):
            bus.consume_output("nope", "nope")


class TestHasOutput:
    def test_false_when_empty(self, bus):
        assert bus.has_output("wf1", "t1") is False

    def test_true_after_publish(self, bus):
        bus.publish_output("wf1", "t1", {"x": 1})
        assert bus.has_output("wf1", "t1") is True

    def test_wrong_workflow(self, bus):
        bus.publish_output("wf1", "t1", {"x": 1})
        assert bus.has_output("wf2", "t1") is False

    def test_wrong_task(self, bus):
        bus.publish_output("wf1", "t1", {"x": 1})
        assert bus.has_output("wf1", "t2") is False


class TestListOutputs:
    def test_empty_workflow(self, bus):
        assert bus.list_outputs("nope") == {}

    def test_lists_all_tasks(self, bus):
        bus.publish_output("wf1", "t1", {"a": 1})
        bus.publish_output("wf1", "t2", {"b": 2})
        outputs = bus.list_outputs("wf1")
        assert set(outputs.keys()) == {"t1", "t2"}
        assert outputs["t1"]["data"] == {"a": 1}
        assert outputs["t2"]["data"] == {"b": 2}


class TestWorkflowIsolation:
    def test_different_workflows_independent(self, bus):
        bus.publish_output("wf1", "t1", {"wf": 1})
        bus.publish_output("wf2", "t1", {"wf": 2})
        assert bus.consume_output("wf1", "t1")["data"] == {"wf": 1}
        assert bus.consume_output("wf2", "t1")["data"] == {"wf": 2}

    def test_list_isolation(self, bus):
        bus.publish_output("wf1", "t1", {"a": 1})
        bus.publish_output("wf2", "t2", {"b": 2})
        assert list(bus.list_outputs("wf1").keys()) == ["t1"]
        assert list(bus.list_outputs("wf2").keys()) == ["t2"]


class TestClearWorkflow:
    def test_clear_removes_only_target(self, bus):
        bus.publish_output("wf1", "t1", {"a": 1})
        bus.publish_output("wf2", "t1", {"b": 2})
        bus.clear_workflow("wf1")
        assert bus.has_output("wf1", "t1") is False
        assert bus.has_output("wf2", "t1") is True

    def test_clear_nonexistent_is_noop(self, bus):
        bus.clear_workflow("nope")  # should not raise


class TestSummary:
    def test_empty_bus(self, bus):
        s = bus.summary()
        assert s["total_workflows"] == 0
        assert s["total_outputs"] == 0
        assert s["per_workflow"] == {}

    def test_multi_workflow_summary(self, bus):
        bus.publish_output("wf1", "t1", {"a": 1})
        bus.publish_output("wf1", "t2", {"b": 2})
        bus.publish_output("wf2", "t1", {"c": 3})
        s = bus.summary()
        assert s["total_workflows"] == 2
        assert s["total_outputs"] == 3
        assert s["per_workflow"] == {"wf1": 2, "wf2": 1}

    def test_summary_after_clear(self, bus):
        bus.publish_output("wf1", "t1", {"a": 1})
        bus.clear_workflow("wf1")
        s = bus.summary()
        assert s["total_workflows"] == 0
        assert s["total_outputs"] == 0


class TestTypedOutput:
    def test_default_is_json(self, bus):
        bus.publish_output("wf1", "t1", {"x": 1})
        assert bus.consume_output("wf1", "t1")["output_type"] == OutputType.JSON

    def test_explicit_type(self, bus):
        bus.publish_output("wf1", "t1", {"raw": b"data"}, output_type=OutputType.BINARY)
        assert bus.consume_output("wf1", "t1")["output_type"] == OutputType.BINARY

    def test_all_enum_values(self):
        for ot in OutputType:
            assert isinstance(ot.value, str)


class TestTimestamp:
    def test_timestamp_is_set(self, bus):
        before = time.time()
        bus.publish_output("wf1", "t1", {"x": 1})
        after = time.time()
        ts = bus.consume_output("wf1", "t1")["timestamp"]
        assert before <= ts <= after

    def test_overwrite_updates_timestamp(self, bus):
        bus.publish_output("wf1", "t1", {"round": 1})
        t1 = bus.consume_output("wf1", "t1")["timestamp"]
        bus.publish_output("wf1", "t1", {"round": 2})
        t2 = bus.consume_output("wf1", "t1")["timestamp"]
        assert t2 >= t1
