import pytest
from core.workflow_budget import WorkflowBudget, BudgetStatus, BudgetExceeded


def test_budget_creation_defaults():
    b = WorkflowBudget()
    assert b.max_tokens == 1_000_000
    assert b.max_cost_usd == 100.0
    assert b.check() == BudgetStatus.OK


def test_record_cost():
    b = WorkflowBudget()
    entry = b.record("T1", "mock", 100, 50, 0.01)
    assert entry.input_tokens == 100
    assert entry.output_tokens == 50
    assert entry.cost_usd == 0.01
    assert entry.task_id == "T1"
    assert entry.adapter_id == "mock"
    assert entry.timestamp


def test_budget_exceeded_raises():
    b = WorkflowBudget(max_cost_usd=0.05)
    b.record("T1", "mock", 0, 0, 0.03)
    with pytest.raises(BudgetExceeded):
        b.record("T2", "mock", 0, 0, 0.03)


def test_warning_threshold():
    b = WorkflowBudget(max_cost_usd=1.0, warning_threshold=0.8)
    b.record("T1", "mock", 0, 0, 0.5)
    assert b.check() == BudgetStatus.OK
    b.record("T2", "mock", 0, 0, 0.35)
    assert b.check() == BudgetStatus.WARNING


def test_per_task_budget():
    b = WorkflowBudget()
    b.record("T1", "mock", 100, 50, 0.01)
    b.record("T1", "mock", 200, 100, 0.02)
    b.record("T2", "mock", 50, 25, 0.005)
    result = b.per_task_budget("T1")
    assert result["tokens"] == 450
    assert result["entries"] == 2
    assert result["cost_usd"] == pytest.approx(0.03)


def test_per_adapter_budget():
    b = WorkflowBudget()
    b.record("T1", "adapter_a", 100, 50, 0.01)
    b.record("T2", "adapter_a", 200, 100, 0.02)
    b.record("T1", "adapter_b", 50, 25, 0.005)
    result = b.per_adapter_budget("adapter_a")
    assert result["tokens"] == 450
    assert result["entries"] == 2
    assert result["cost_usd"] == pytest.approx(0.03)


def test_remaining_tokens():
    b = WorkflowBudget(max_tokens=1000)
    b.record("T1", "mock", 300, 100, 0.01)
    r = b.remaining()
    assert r["tokens"] == 600


def test_remaining_cost():
    b = WorkflowBudget(max_cost_usd=10.0)
    b.record("T1", "mock", 10, 10, 3.5)
    r = b.remaining()
    assert r["cost_usd"] == pytest.approx(6.5)


def test_summary_stats():
    b = WorkflowBudget()
    b.record("T1", "mock", 100, 50, 0.01)
    s = b.summary()
    assert s["total_entries"] == 1
    assert s["total_tokens"] == 150
    assert s["total_cost_usd"] == 0.01
    assert s["status"] == "ok"
    assert s["exceeded"] is False


def test_reset_clears_all():
    b = WorkflowBudget()
    b.record("T1", "mock", 100, 50, 0.01)
    b.reset()
    assert b.summary()["total_entries"] == 0
    assert b.summary()["total_tokens"] == 0
    assert b.summary()["total_cost_usd"] == 0.0
    assert b.check() == BudgetStatus.OK


def test_multiple_entries():
    b = WorkflowBudget()
    for i in range(5):
        b.record(f"T{i}", "mock", 10, 5, 0.001)
    s = b.summary()
    assert s["total_entries"] == 5
    assert s["total_tokens"] == 75
    assert s["total_cost_usd"] == pytest.approx(0.005)


def test_zero_budget():
    b = WorkflowBudget(max_tokens=0, max_cost_usd=0.0)
    assert b.check() == BudgetStatus.OK
    with pytest.raises(BudgetExceeded):
        b.record("T1", "mock", 0, 1, 0.0)
