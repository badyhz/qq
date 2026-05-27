"""Tests for research workbench splits — T4531-T4560."""
from __future__ import annotations

import pytest

from core.research_workbench_splits import (
    ResearchSplitPlan,
    generate_research_splits,
    split_plan_to_dict,
)


class TestResearchSplits:
    def test_generates_splits(self):
        plan = generate_research_splits(total_bars=500, n_folds=3)
        assert plan.folds == 3
        assert len(plan.splits) > 0
        assert plan.split_mode == "rolling"

    def test_deterministic_ids(self):
        p1 = generate_research_splits(total_bars=500, n_folds=3, dataset_id="btc_5m")
        p2 = generate_research_splits(total_bars=500, n_folds=3, dataset_id="btc_5m")
        for a, b in zip(p1.splits, p2.splits):
            assert a.split_id == b.split_id

    def test_different_dataset_different_ids(self):
        p1 = generate_research_splits(total_bars=500, n_folds=3, dataset_id="btc")
        p2 = generate_research_splits(total_bars=500, n_folds=3, dataset_id="eth")
        ids1 = {s.split_id for s in p1.splits}
        ids2 = {s.split_id for s in p2.splits}
        assert ids1 != ids2

    def test_small_data_warning(self):
        plan = generate_research_splits(total_bars=10, n_folds=3, min_bars_per_fold=50)
        assert plan.small_data_warning is True

    def test_no_small_data_warning(self):
        plan = generate_research_splits(total_bars=500, n_folds=3, min_bars_per_fold=50)
        assert plan.small_data_warning is False

    def test_split_types_present(self):
        plan = generate_research_splits(total_bars=600, n_folds=3)
        types = {s.split_type for s in plan.splits}
        assert "TRAIN" in types
        assert "VALIDATION" in types
        assert "TEST" in types

    def test_bar_counts_positive(self):
        plan = generate_research_splits(total_bars=600, n_folds=3)
        for s in plan.splits:
            assert s.bar_count >= 0

    def test_frozen(self):
        plan = generate_research_splits(total_bars=500, n_folds=3)
        with pytest.raises(AttributeError):
            plan.folds = 5


class TestSplitPlanSerialization:
    def test_to_dict(self):
        plan = generate_research_splits(total_bars=500, n_folds=3, dataset_id="test")
        d = split_plan_to_dict(plan)
        assert d["split_mode"] == "rolling"
        assert d["folds"] == 3
        assert len(d["splits"]) > 0
        assert "split_id" in d["splits"][0]

    def test_deterministic_serialization(self):
        plan = generate_research_splits(total_bars=500, n_folds=3, dataset_id="test")
        import json
        j1 = json.dumps(split_plan_to_dict(plan), sort_keys=True)
        j2 = json.dumps(split_plan_to_dict(plan), sort_keys=True)
        assert j1 == j2
