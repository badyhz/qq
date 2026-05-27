"""Safety boundaries + dependency density scorer acceptance tests.

Pure pytest. No I/O. No network.
"""

import json
import os

import pytest

from core.prd_backlog_schema import PrdBacklogItem, build_backlog_item
from core.prd_backlog_frozen_milestone_guard import check_frozen_milestone
from core.prd_backlog_materializer import materialize_default_backlog
from core.prd_dependency_density_scorer import (
    score_dependency_density,
    score_density_for_milestone,
    density_score_to_dict,
    density_score_to_markdown,
)

# 14 non-seed PRD source modules (T858-T900)
CORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "core")
PRD_SOURCE_FILES = [
    "prd_task_model.py",
    "prd_task_queue_loader.py",
    "prd_task_queue_validator.py",
    "prd_agent_prompt_generator.py",
    "prd_acceptance_command_registry.py",
    "prd_safety_boundary_checker.py",
    "prd_execution_report_parser.py",
    "prd_queue_closeout_packet.py",
    "prd_control_plane_final_status_report.py",
    "prd_backlog_schema.py",
    "prd_milestone_planner.py",
    "prd_wave_planner.py",
    "prd_batch_planner.py",
    "prd_dependency_graph_validator.py",
    "prd_task_risk_classifier.py",
    "prd_agent_execution_window_recommender.py",
    "prd_backlog_seed_packet.py",
    "prd_planning_final_status_report.py",
    "prd_backlog_frozen_milestone_guard.py",
    "prd_backlog_materializer.py",
    "prd_backlog_markdown_renderer.py",
    "prd_backlog_json_serializer.py",
    "prd_dependency_density_scorer.py",
    "prd_backlog_risk_heatmap_packet.py",
    "prd_execution_prompt_pack_generator.py",
]


def _read_file(filename: str) -> str:
    path = os.path.join(CORE_DIR, filename)
    with open(path, "r") as f:
        return f.read()


def _make_item(task_id: str, deps=None, risk="LOW", milestone="M1", status="NOT_STARTED"):
    return build_backlog_item(
        task_id=task_id,
        title=f"Test {task_id}",
        milestone_id=milestone,
        wave_id=f"{milestone}-W0",
        batch_id=f"{milestone}-W0-B0",
        risk_level=risk,
        status=status,
        dependencies=deps or [],
        allowed_file_patterns=[],
        forbidden_file_patterns=[],
        acceptance_command_ids=[],
        notes=[],
    )


# ── TestNoLiveAuthorizationInModules ──


class TestNoLiveAuthorizationInModules:
    def test_no_module_authorizes_live(self):
        """No PRD source file may contain 'authorized for live trading'."""
        for fname in PRD_SOURCE_FILES:
            content = _read_file(fname)
            assert "authorized for live trading" not in content.lower(), (
                f"{fname} contains forbidden live-authorization string"
            )

    def test_no_module_authorizes_real_order(self):
        """No PRD source file may contain 'authorized for real order placement'."""
        for fname in PRD_SOURCE_FILES:
            content = _read_file(fname)
            assert "authorized for real order placement" not in content.lower(), (
                f"{fname} contains forbidden real-order-authorization string"
            )


# ── TestForbiddenPatterns ──


class TestForbiddenPatterns:
    def test_milestone_seeds_no_frozen_tasks(self):
        """M1-M7 seed task_items must not contain any FROZEN risk-level item."""
        from core.prd_backlog_milestone1_seed import build_milestone1_seed
        from core.prd_backlog_milestone2_seed import build_milestone2_seed
        from core.prd_backlog_milestone3_seed import build_milestone3_seed
        from core.prd_backlog_milestone4_seed import build_milestone4_seed
        from core.prd_backlog_milestone5_seed import build_milestone5_seed
        from core.prd_backlog_milestone6_seed import build_milestone6_seed
        from core.prd_backlog_milestone7_seed import build_milestone7_seed

        seeds = [
            build_milestone1_seed(),
            build_milestone2_seed(),
            build_milestone3_seed(),
            build_milestone4_seed(),
            build_milestone5_seed(),
            build_milestone6_seed(),
            build_milestone7_seed(),
        ]
        for seed in seeds:
            for item in seed.task_items:
                assert item.get("risk_level") != "FROZEN", (
                    f"{seed.milestone_id} contains FROZEN task {item.get('task_id')}"
                )

    def test_materialized_backlog_no_frozen(self):
        """Default materialized backlog must contain zero FROZEN items."""
        result = materialize_default_backlog()
        frozen = [i for i in result.backlog.items if i.risk_level == "FROZEN"]
        assert len(frozen) == 0, f"Found {len(frozen)} FROZEN items in materialized backlog"

    def test_frozen_guard_blocks_frozen_outside_m8(self):
        """FROZEN task in M1 must be BLOCKED by frozen milestone guard."""
        item = _make_item(task_id="T999", risk="FROZEN", milestone="M1")
        guard = check_frozen_milestone([item])
        assert guard.verdict == "BLOCKED"


# ── TestDependencyDensityScorer ──


class TestDependencyDensityScorer:
    def test_import(self):
        """All four public symbols are importable."""
        assert callable(score_dependency_density)
        assert callable(score_density_for_milestone)
        assert callable(density_score_to_dict)
        assert callable(density_score_to_markdown)

    def test_empty_items(self):
        """Empty list yields density_level='low'."""
        score = score_dependency_density([])
        assert score.density_level == "low"

    def test_all_have_deps(self):
        """5 items all with deps -> density_level='high'."""
        items = [_make_item(f"T{i}", deps=["T0"]) for i in range(5)]
        score = score_dependency_density(items)
        assert score.density_level == "high"

    def test_none_have_deps(self):
        """5 items with no deps -> density_level='low'."""
        items = [_make_item(f"T{i}") for i in range(5)]
        score = score_dependency_density(items)
        assert score.density_level == "low"

    def test_deterministic(self):
        """Same input produces identical output."""
        items = [_make_item(f"T{i}", deps=["T0"] if i else []) for i in range(5)]
        s1 = score_dependency_density(items)
        s2 = score_dependency_density(items)
        assert s1 == s2

    def test_dict_serializable(self):
        """density_score_to_dict output is JSON-serializable."""
        items = [_make_item("T1", deps=["T0"])]
        score = score_dependency_density(items)
        d = density_score_to_dict(score)
        json.dumps(d)  # must not raise


# ── TestTaskQueueDoc ──


class TestTaskQueueDoc:
    QUEUE_PATH = os.path.join(
        os.path.dirname(__file__), "..", "..", "docs", "dev_prd", "runtime_governance_task_queue.md"
    )

    def _read_queue(self) -> str:
        with open(self.QUEUE_PATH, "r") as f:
            return f.read()

    def test_queue_contains_t881_t900_completed(self):
        """Task queue doc references T881 and marks range as completed."""
        text = self._read_queue()
        assert "T881" in text
        assert "completed" in text.lower()

    def test_queue_contains_t901_human_review(self):
        """Task queue doc references T901 with HUMAN_REVIEW_REQUIRED."""
        text = self._read_queue()
        assert "T901" in text
        assert "HUMAN_REVIEW_REQUIRED" in text


# ── TestMaterializerSeedCount ──


class TestMaterializerSeedCount:
    def test_current_seed_is_71(self):
        """Current seed materializes exactly 71 tasks."""
        result = materialize_default_backlog()
        assert result.materialized_count == 71

    def test_seed_count_documented(self):
        """Current seed materializes 71 tasks from 7 milestones. Full 500+ expansion is future work."""
        result = materialize_default_backlog()
        assert result.milestone_count == 7
        assert result.materialized_count == 71
