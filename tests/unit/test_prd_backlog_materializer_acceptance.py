"""Acceptance tests for prd_backlog_materializer and frozen_milestone_guard.

Pure pytest. No I/O. No network.
"""

import pytest

from core.prd_backlog_schema import PrdBacklogItem


# --- Import smoke ---


class TestMaterializerImports:
    def test_materializer_imports(self):
        from core.prd_backlog_materializer import (
            materialize_default_backlog,
            materialize_backlog_from_seeds,
            materialization_result_to_dict,
            materialization_result_to_markdown,
            PrdMaterializationResult,
        )
        assert callable(materialize_default_backlog)
        assert callable(materialize_backlog_from_seeds)
        assert callable(materialization_result_to_dict)
        assert callable(materialization_result_to_markdown)
        assert PrdMaterializationResult is not None

    def test_frozen_guard_imports(self):
        from core.prd_backlog_frozen_milestone_guard import (
            check_frozen_milestone,
            frozen_guard_to_dict,
            frozen_guard_to_markdown,
            PrdFrozenMilestoneGuard,
        )
        assert callable(check_frozen_milestone)
        assert callable(frozen_guard_to_dict)
        assert callable(frozen_guard_to_markdown)
        assert PrdFrozenMilestoneGuard is not None


# --- Default materialization ---


class TestMaterializerDefault:
    @pytest.fixture(scope="class")
    def result(self):
        from core.prd_backlog_materializer import materialize_default_backlog
        return materialize_default_backlog()

    def test_default_materialization(self, result):
        assert result.materialized_count > 0
        assert result.milestone_count == 7
        assert result.frozen_guard.verdict == "PASS"

    def test_materialized_backlog_has_items(self, result):
        assert isinstance(result.backlog.items, list)
        assert len(result.backlog.items) > 0

    def test_all_items_have_required_fields(self, result):
        required = [
            "task_id",
            "title",
            "milestone_id",
            "wave_id",
            "batch_id",
            "risk_level",
            "status",
            "dependencies",
            "allowed_file_patterns",
            "forbidden_file_patterns",
            "acceptance_command_ids",
            "notes",
        ]
        for item in result.backlog.items:
            for field in required:
                assert hasattr(item, field), f"{item.task_id} missing {field}"

    def test_materialization_count_explained(self, result):
        """Current seed count is 71 tasks across 7 milestones.

        This is 71, not 500 -- the target_count param sets total_expected_tasks
        on the backlog but does not inflate the actual materialized items.
        The materialized_count reflects the real seed count.
        """
        assert result.materialized_count == 71


# --- Determinism ---


class TestMaterializerDeterminism:
    def test_default_materialization_is_deterministic(self):
        from core.prd_backlog_materializer import materialize_default_backlog

        a = materialize_default_backlog()
        b = materialize_default_backlog()
        assert a.materialized_count == b.materialized_count
        assert len(a.backlog.items) == len(b.backlog.items)


# --- Serializers ---


class TestMaterializerSerializers:
    def test_result_to_dict(self):
        from core.prd_backlog_materializer import (
            materialize_default_backlog,
            materialization_result_to_dict,
        )
        d = materialization_result_to_dict(materialize_default_backlog())
        assert "backlog" in d
        assert "materialized_count" in d
        assert "milestone_count" in d
        assert "frozen_guard" in d
        assert "notes" in d

    def test_result_to_markdown(self):
        from core.prd_backlog_materializer import (
            materialize_default_backlog,
            materialization_result_to_markdown,
        )
        md = materialization_result_to_markdown(materialize_default_backlog())
        assert "Materialization" in md


# --- Frozen guard ---


class TestFrozenMilestoneGuard:
    def test_guard_with_empty_items(self):
        from core.prd_backlog_frozen_milestone_guard import check_frozen_milestone
        guard = check_frozen_milestone([])
        assert guard.verdict == "PASS"

    def test_guard_blocks_frozen_outside_m8(self):
        from core.prd_backlog_frozen_milestone_guard import check_frozen_milestone
        item = PrdBacklogItem(
            task_id="T-TEST-1",
            title="Frozen task in wrong milestone",
            milestone_id="M1",
            wave_id="M1-W0",
            batch_id="M1-W0-B0",
            risk_level="FROZEN",
            status="NOT_STARTED",
            dependencies=(),
            allowed_file_patterns=(),
            forbidden_file_patterns=(),
            acceptance_command_ids=(),
            notes=(),
        )
        guard = check_frozen_milestone([item])
        assert guard.verdict == "BLOCKED"

    def test_guard_passes_frozen_in_m8(self):
        from core.prd_backlog_frozen_milestone_guard import check_frozen_milestone
        item = PrdBacklogItem(
            task_id="T-TEST-2",
            title="Frozen task in M8",
            milestone_id="M8",
            wave_id="M8-W0",
            batch_id="M8-W0-B0",
            risk_level="FROZEN",
            status="NOT_STARTED",
            dependencies=(),
            allowed_file_patterns=(),
            forbidden_file_patterns=(),
            acceptance_command_ids=(),
            notes=(),
        )
        guard = check_frozen_milestone([item])
        assert guard.verdict == "PASS"


# --- No live authorization ---


class TestNoLiveAuthorization:
    def test_no_materialized_task_authorizes_live(self):
        from core.prd_backlog_materializer import materialize_default_backlog
        result = materialize_default_backlog()
        forbidden = ["authorized for live trading", "authorized for real order placement"]
        for item in result.backlog.items:
            text = (item.title + " " + " ".join(item.notes)).lower()
            for phrase in forbidden:
                assert phrase not in text, f"{item.task_id} contains forbidden phrase: {phrase}"

    def test_no_frozen_items_in_default_materialization(self):
        from core.prd_backlog_materializer import materialize_default_backlog
        result = materialize_default_backlog()
        frozen = [i for i in result.backlog.items if i.risk_level == "FROZEN"]
        assert frozen == [], f"Frozen items found: {[i.task_id for i in frozen]}"
