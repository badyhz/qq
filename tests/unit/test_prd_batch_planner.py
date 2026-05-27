"""Tests for PRD batch planner — T876."""

from core.prd_batch_planner import (
    PrdBatch,
    batch_to_dict,
    batch_to_markdown,
    batches_to_dict,
    batches_to_markdown,
    plan_batches_for_wave,
    summarize_batches,
)
from core.prd_wave_planner import PrdWave


# --- Helpers ---


def _make_wave(task_count: int, risk: str = "LOW") -> PrdWave:
    task_ids = [f"T{i}" for i in range(1, task_count + 1)]
    return PrdWave(
        wave_id="M0-W0",
        milestone_id="M0",
        task_ids=task_ids,
        max_parallel_agents=8,
        dependency_notes=[],
        risk_level=risk,
        recommended_route="mimo2.5",
        notes=[],
    )


# --- Tests ---


class TestPlanBatches:
    def test_12_tasks_split_5_5_2(self):
        wave = _make_wave(12)
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)

        assert len(batches) == 3
        assert len(batches[0].task_ids) == 5
        assert len(batches[1].task_ids) == 5
        assert len(batches[2].task_ids) == 2

    def test_batch_ids_sequential(self):
        wave = _make_wave(12)
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)

        assert batches[0].batch_id == "M0-W0-B0"
        assert batches[1].batch_id == "M0-W0-B1"
        assert batches[2].batch_id == "M0-W0-B2"

    def test_execution_order_sequential(self):
        wave = _make_wave(12)
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)

        for i, b in enumerate(batches):
            assert b.execution_order == i

    def test_hard_stop_is_last_task(self):
        wave = _make_wave(12)
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)

        assert batches[0].hard_stop_task_id == "T5"
        assert batches[1].hard_stop_task_id == "T10"
        assert batches[2].hard_stop_task_id == "T12"

    def test_high_risk_max_2_agents(self):
        wave = _make_wave(6, risk="HIGH")
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)

        for b in batches:
            assert b.risk_level == "HIGH"
            assert b.recommended_agent_count == 2

    def test_frozen_risk_zero_agents(self):
        wave = _make_wave(4, risk="FROZEN")
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)

        assert len(batches) == 1
        assert batches[0].recommended_agent_count == 0

    def test_frozen_notes_require_human_approval(self):
        wave = _make_wave(4, risk="FROZEN")
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)

        assert any("Human approval" in n for n in batches[0].notes)

    def test_low_risk_uses_wave_parallel(self):
        wave = _make_wave(3, risk="LOW")
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)

        assert batches[0].recommended_agent_count == 8

    def test_medium_risk_uses_wave_parallel(self):
        wave = _make_wave(3, risk="MEDIUM")
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)

        assert batches[0].recommended_agent_count == 8

    def test_empty_wave_returns_empty(self):
        wave = _make_wave(0)
        batches = plan_batches_for_wave(wave)

        assert batches == []

    def test_wave_id_propagated(self):
        wave = _make_wave(3)
        batches = plan_batches_for_wave(wave)

        for b in batches:
            assert b.wave_id == "M0-W0"

    def test_tasks_preserved_in_order(self):
        wave = _make_wave(7)
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=3)

        flat = []
        for b in batches:
            flat.extend(b.task_ids)
        assert flat == [f"T{i}" for i in range(1, 8)]


class TestSerialization:
    def test_batch_to_dict_keys(self):
        wave = _make_wave(3)
        batches = plan_batches_for_wave(wave)
        d = batch_to_dict(batches[0])

        expected_keys = {
            "batch_id",
            "wave_id",
            "task_ids",
            "execution_order",
            "risk_level",
            "recommended_agent_count",
            "hard_stop_task_id",
            "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_batches_to_dict_length(self):
        wave = _make_wave(12)
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)
        dicts = batches_to_dict(batches)

        assert len(dicts) == 3


class TestMarkdown:
    def test_batch_markdown_contains_id(self):
        wave = _make_wave(3)
        batches = plan_batches_for_wave(wave)
        md = batch_to_markdown(batches[0])

        assert "M0-W0-B0" in md

    def test_batches_markdown_header(self):
        wave = _make_wave(12)
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)
        md = batches_to_markdown(batches)

        assert "# Execution Batches (3 total)" in md

    def test_deterministic_markdown(self):
        wave = _make_wave(12)
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)
        md1 = batches_to_markdown(batches)
        md2 = batches_to_markdown(batches)

        assert md1 == md2

    def test_markdown_lists_all_tasks(self):
        wave = _make_wave(6)
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=3)
        md = batches_to_markdown(batches)

        for i in range(1, 7):
            assert f"T{i}" in md


class TestSummary:
    def test_summary_counts(self):
        wave = _make_wave(12)
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)
        s = summarize_batches(batches)

        assert s["total_batches"] == 3
        assert s["total_tasks"] == 12
        assert s["risk_counts"]["LOW"] == 3

    def test_summary_high_risk_agents(self):
        wave = _make_wave(6, risk="HIGH")
        batches = plan_batches_for_wave(wave, max_tasks_per_batch=5)
        s = summarize_batches(batches)

        assert s["total_recommended_agents"] == 4  # 2 + 2

    def test_summary_frozen_agents(self):
        wave = _make_wave(4, risk="FROZEN")
        batches = plan_batches_for_wave(wave)
        s = summarize_batches(batches)

        assert s["total_recommended_agents"] == 0
