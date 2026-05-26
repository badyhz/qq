"""Unit tests for core.runtime_budget_attribution."""

import pytest

from core.runtime_budget_attribution import (
    AdapterCost,
    RuntimeBudgetAttribution,
    TaskCost,
    WorkflowCost,
)


class TestRecordAndGetTaskCost:
    def test_record_and_retrieve(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "adapter_a", 100, 50, 0.02)
        tc = rba.get_task_cost("wf1", "t1")
        assert tc is not None
        assert tc.task_id == "t1"
        assert tc.adapter_id == "adapter_a"
        assert tc.input_tokens == 100
        assert tc.output_tokens == 50
        assert tc.cost_usd == 0.02
        assert isinstance(tc.timestamp, float)

    def test_unknown_task_returns_none(self):
        rba = RuntimeBudgetAttribution()
        assert rba.get_task_cost("wf1", "nonexistent") is None

    def test_unknown_workflow_returns_none(self):
        rba = RuntimeBudgetAttribution()
        assert rba.get_task_cost("nonexistent", "t1") is None


class TestAdapterCostAggregation:
    def test_single_task(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "adapter_a", 100, 50, 0.02)
        ac = rba.get_adapter_costs("wf1", "adapter_a")
        assert ac.total_tasks == 1
        assert ac.total_input_tokens == 100
        assert ac.total_output_tokens == 50
        assert ac.total_cost_usd == 0.02

    def test_multiple_tasks_same_adapter(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "adapter_a", 100, 50, 0.02)
        rba.record_task_cost("wf1", "t2", "adapter_a", 200, 80, 0.05)
        ac = rba.get_adapter_costs("wf1", "adapter_a")
        assert ac.total_tasks == 2
        assert ac.total_input_tokens == 300
        assert ac.total_output_tokens == 130
        assert ac.total_cost_usd == 0.07

    def test_no_tasks_returns_zero(self):
        rba = RuntimeBudgetAttribution()
        ac = rba.get_adapter_costs("wf1", "adapter_a")
        assert ac.total_tasks == 0
        assert ac.total_cost_usd == 0.0


class TestWorkflowCostAggregation:
    def test_single_adapter(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "adapter_a", 100, 50, 0.02)
        rba.record_task_cost("wf1", "t2", "adapter_a", 200, 80, 0.05)
        wc = rba.get_workflow_cost("wf1")
        assert wc.workflow_id == "wf1"
        assert wc.total_tasks == 2
        assert wc.total_cost_usd == 0.07
        assert wc.total_input_tokens == 300
        assert wc.total_output_tokens == 130

    def test_multiple_adapters(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "adapter_a", 100, 50, 0.02)
        rba.record_task_cost("wf1", "t2", "adapter_b", 300, 100, 0.10)
        wc = rba.get_workflow_cost("wf1")
        assert wc.total_tasks == 2
        assert wc.total_cost_usd == pytest.approx(0.12)
        assert wc.total_input_tokens == 400
        assert wc.total_output_tokens == 150
        assert "adapter_a" in wc.adapter_breakdown
        assert "adapter_b" in wc.adapter_breakdown
        assert wc.adapter_breakdown["adapter_a"].total_cost_usd == 0.02
        assert wc.adapter_breakdown["adapter_b"].total_cost_usd == 0.10

    def test_empty_workflow(self):
        rba = RuntimeBudgetAttribution()
        wc = rba.get_workflow_cost("nonexistent")
        assert wc.total_tasks == 0
        assert wc.total_cost_usd == 0.0
        assert wc.adapter_breakdown == {}


class TestGetAllAdapterCosts:
    def test_breakdown(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "adapter_a", 100, 50, 0.02)
        rba.record_task_cost("wf1", "t2", "adapter_b", 200, 80, 0.05)
        rba.record_task_cost("wf1", "t3", "adapter_a", 300, 100, 0.10)
        result = rba.get_all_adapter_costs("wf1")
        assert len(result) == 2
        assert result["adapter_a"].total_tasks == 2
        assert result["adapter_a"].total_cost_usd == pytest.approx(0.12)
        assert result["adapter_b"].total_tasks == 1
        assert result["adapter_b"].total_cost_usd == 0.05

    def test_empty(self):
        rba = RuntimeBudgetAttribution()
        assert rba.get_all_adapter_costs("wf1") == {}


class TestListWorkflows:
    def test_list_workflows(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "a", 10, 5, 0.01)
        rba.record_task_cost("wf2", "t2", "a", 10, 5, 0.01)
        rba.record_task_cost("wf3", "t3", "b", 10, 5, 0.01)
        wfs = rba.list_workflows()
        assert set(wfs) == {"wf1", "wf2", "wf3"}

    def test_empty(self):
        rba = RuntimeBudgetAttribution()
        assert rba.list_workflows() == []


class TestClearWorkflow:
    def test_clear_removes_only_that_workflow(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "a", 10, 5, 0.01)
        rba.record_task_cost("wf2", "t2", "a", 10, 5, 0.01)
        rba.clear_workflow("wf1")
        assert rba.get_task_cost("wf1", "t1") is None
        assert rba.get_task_cost("wf2", "t2") is not None

    def test_clear_nonexistent_noop(self):
        rba = RuntimeBudgetAttribution()
        rba.clear_workflow("nonexistent")  # should not raise


class TestWorkflowIsolation:
    def test_separate_workflows(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "a", 100, 50, 0.02)
        rba.record_task_cost("wf2", "t2", "a", 300, 100, 0.10)
        wc1 = rba.get_workflow_cost("wf1")
        wc2 = rba.get_workflow_cost("wf2")
        assert wc1.total_cost_usd == 0.02
        assert wc2.total_cost_usd == 0.10
        assert wc1.total_tasks == 1
        assert wc2.total_tasks == 1


class TestSummary:
    def test_summary(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "adapter_a", 100, 50, 0.02)
        rba.record_task_cost("wf1", "t2", "adapter_b", 200, 80, 0.05)
        rba.record_task_cost("wf2", "t3", "adapter_a", 300, 100, 0.10)
        s = rba.summary()
        assert s["total_workflows"] == 2
        assert s["total_tasks"] == 3
        assert s["total_cost_usd"] == 0.17
        assert s["total_input_tokens"] == 600
        assert s["total_output_tokens"] == 230
        assert s["unique_adapters"] == 2

    def test_summary_empty(self):
        rba = RuntimeBudgetAttribution()
        s = rba.summary()
        assert s["total_workflows"] == 0
        assert s["total_tasks"] == 0
        assert s["total_cost_usd"] == 0.0


class TestTokenAdditivity:
    def test_tokens_additive(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "a", 100, 50, 0.01)
        rba.record_task_cost("wf1", "t2", "a", 200, 75, 0.01)
        wc = rba.get_workflow_cost("wf1")
        assert wc.total_input_tokens == 300
        assert wc.total_output_tokens == 125

    def test_cost_additive(self):
        rba = RuntimeBudgetAttribution()
        rba.record_task_cost("wf1", "t1", "a", 10, 5, 0.01)
        rba.record_task_cost("wf1", "t2", "a", 10, 5, 0.03)
        rba.record_task_cost("wf1", "t3", "b", 10, 5, 0.07)
        wc = rba.get_workflow_cost("wf1")
        assert abs(wc.total_cost_usd - 0.11) < 1e-9
