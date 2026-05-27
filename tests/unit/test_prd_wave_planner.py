"""Tests for PRD wave planner — T875."""

from typing import List, Optional

import pytest

from core.prd_milestone_planner import PrdMilestone
from core.prd_wave_planner import (
    PrdWave,
    plan_waves_for_milestone,
    summarize_waves,
    wave_to_dict,
    wave_to_markdown,
    waves_to_dict,
    waves_to_markdown,
)


# --- Fixtures ---


def _make_milestone(
    task_count: int,
    risk: str = "LOW",
    deps: Optional[List[str]] = None,
    ms_id: str = "MS-T001-T025",
) -> PrdMilestone:
    task_ids = [f"T{i:03d}" for i in range(1, task_count + 1)]
    return PrdMilestone(
        milestone_id=ms_id,
        title=f"Test milestone ({task_count} tasks)",
        task_ids=task_ids,
        risk_level=risk,
        status="NOT_STARTED",
        dependencies=deps or [],
        recommended_execution_mode="SMALL_BATCH",
        notes=[],
    )


# --- Tests ---


class TestWaveSplit:
    def test_25_tasks_split_into_3_waves(self):
        ms = _make_milestone(25)
        waves = plan_waves_for_milestone(ms, max_tasks_per_wave=10)
        assert len(waves) == 3
        # Wave sizes: 10, 10, 5
        assert len(waves[0].task_ids) == 10
        assert len(waves[1].task_ids) == 10
        assert len(waves[2].task_ids) == 5
        # All tasks accounted for
        all_tasks = []
        for w in waves:
            all_tasks.extend(w.task_ids)
        assert all_tasks == [f"T{i:03d}" for i in range(1, 26)]

    def test_10_tasks_single_wave(self):
        ms = _make_milestone(10)
        waves = plan_waves_for_milestone(ms)
        assert len(waves) == 1

    def test_empty_milestone(self):
        ms = _make_milestone(0)
        waves = plan_waves_for_milestone(ms)
        assert waves == []

    def test_wave_ids_contain_milestone_and_index(self):
        ms = _make_milestone(25, ms_id="MS-T001-T025")
        waves = plan_waves_for_milestone(ms, max_tasks_per_wave=10)
        assert waves[0].wave_id == "MS-T001-T025-W0"
        assert waves[1].wave_id == "MS-T001-T025-W1"
        assert waves[2].wave_id == "MS-T001-T025-W2"


class TestRiskParallelism:
    def test_low_risk_8_agents(self):
        ms = _make_milestone(5, risk="LOW")
        waves = plan_waves_for_milestone(ms)
        assert waves[0].max_parallel_agents == 8

    def test_medium_risk_8_agents(self):
        ms = _make_milestone(5, risk="MEDIUM")
        waves = plan_waves_for_milestone(ms)
        assert waves[0].max_parallel_agents == 8

    def test_high_risk_3_agents(self):
        ms = _make_milestone(5, risk="HIGH")
        waves = plan_waves_for_milestone(ms)
        assert waves[0].max_parallel_agents == 3

    def test_frozen_risk_0_agents(self):
        ms = _make_milestone(5, risk="FROZEN")
        waves = plan_waves_for_milestone(ms)
        assert waves[0].max_parallel_agents == 0


class TestRoute:
    def test_low_route_mimo25(self):
        ms = _make_milestone(5, risk="LOW")
        waves = plan_waves_for_milestone(ms)
        assert waves[0].recommended_route == "mimo2.5"

    def test_medium_route_mimo25(self):
        ms = _make_milestone(5, risk="MEDIUM")
        waves = plan_waves_for_milestone(ms)
        assert waves[0].recommended_route == "mimo2.5"

    def test_high_route_mimo25pro(self):
        ms = _make_milestone(5, risk="HIGH")
        waves = plan_waves_for_milestone(ms)
        assert waves[0].recommended_route == "mimo2.5pro"

    def test_frozen_route_human_only(self):
        ms = _make_milestone(5, risk="FROZEN")
        waves = plan_waves_for_milestone(ms)
        assert waves[0].recommended_route == "HUMAN_ONLY"

    def test_ext_deps_route_mimo25pro(self):
        ms = _make_milestone(5, risk="LOW", deps=["T999"])
        waves = plan_waves_for_milestone(ms)
        assert waves[0].recommended_route == "mimo2.5pro"


class TestDeterminism:
    def test_same_input_same_output(self):
        ms = _make_milestone(25, risk="MEDIUM", deps=["T999"])
        w1 = plan_waves_for_milestone(ms)
        w2 = plan_waves_for_milestone(ms)
        assert waves_to_dict(w1) == waves_to_dict(w2)

    def test_dict_roundtrip(self):
        ms = _make_milestone(15, risk="HIGH", ms_id="MS-T001-T015")
        waves = plan_waves_for_milestone(ms)
        dicts = waves_to_dict(waves)
        assert len(dicts) == 2
        assert dicts[0]["wave_id"] == "MS-T001-T015-W0"
        assert dicts[0]["risk_level"] == "HIGH"
        assert dicts[0]["recommended_route"] == "mimo2.5pro"


class TestSerializers:
    def test_wave_to_dict_keys(self):
        ms = _make_milestone(5)
        wave = plan_waves_for_milestone(ms)[0]
        d = wave_to_dict(wave)
        expected_keys = {
            "wave_id",
            "milestone_id",
            "task_ids",
            "max_parallel_agents",
            "dependency_notes",
            "risk_level",
            "recommended_route",
            "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_wave_to_markdown_contains_wave_id(self):
        ms = _make_milestone(5, ms_id="MS-T001-T005")
        wave = plan_waves_for_milestone(ms)[0]
        md = wave_to_markdown(wave)
        assert "MS-T001-T005-W0" in md
        assert "mimo2.5" in md

    def test_waves_to_markdown_header(self):
        ms = _make_milestone(25)
        waves = plan_waves_for_milestone(ms)
        md = waves_to_markdown(waves)
        assert "# Execution Waves (3 total)" in md


class TestSummary:
    def test_summarize_counts(self):
        ms = _make_milestone(25, risk="MEDIUM")
        waves = plan_waves_for_milestone(ms)
        s = summarize_waves(waves)
        assert s["total_waves"] == 3
        assert s["total_tasks"] == 25
        assert s["risk_counts"] == {"MEDIUM": 3}
        assert s["route_counts"] == {"mimo2.5": 3}

    def test_summarize_mixed_not_applicable(self):
        """Single milestone has uniform risk, so summary is always uniform."""
        ms = _make_milestone(10, risk="FROZEN")
        waves = plan_waves_for_milestone(ms)
        s = summarize_waves(waves)
        assert s["route_counts"] == {"HUMAN_ONLY": 1}
