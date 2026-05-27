"""T1527 - Tests for FrozenBacklogReportMaterializer."""
from __future__ import annotations

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY, FrozenBacklogInventory
from core.frozen_backlog_inventory_record import FrozenBacklogInventoryRecord
from core.frozen_backlog_report_materializer import (
    materialize_full_report,
    materialize_report_records,
    materialize_report_summary,
)
from core.frozen_backlog_report_record import FrozenBacklogReportRecord
from core.frozen_backlog_report_summary import FrozenBacklogReportSummary


def _make_single_record_inventory() -> FrozenBacklogInventory:
    """Helper: build a minimal 1-record inventory for testing."""
    rec = FrozenBacklogInventoryRecord(
        file_path="scripts/example.py",
        risk_class="MEDIUM",
        category="OPERATIONAL_SHADOW",
        allowed_actions=("review", "read"),
        forbidden_actions=("execute", "submit"),
        required_evidence=("dry_run_log",),
        promotion_readiness_default=0.2,
        unlock_recommendation="HOLD",
        release_hold="HOLD",
    )
    return FrozenBacklogInventory(
        inventory_id="test-inv",
        records=(rec,),
        total_count=1,
        high_risk_count=0,
        medium_risk_count=1,
    )


class TestMaterializeReportRecords:
    """Tests for materialize_report_records."""

    def test_returns_tuple(self) -> None:
        result = materialize_report_records(FROZEN_BACKLOG_INVENTORY)
        assert isinstance(result, tuple)

    def test_count_matches_inventory(self) -> None:
        result = materialize_report_records(FROZEN_BACKLOG_INVENTORY)
        assert len(result) == FROZEN_BACKLOG_INVENTORY.total_count

    def test_each_is_frozen_backlog_report_record(self) -> None:
        result = materialize_report_records(FROZEN_BACKLOG_INVENTORY)
        for rec in result:
            assert isinstance(rec, FrozenBacklogReportRecord)

    def test_record_ids_are_sequential(self) -> None:
        inv = _make_single_record_inventory()
        result = materialize_report_records(inv)
        assert result[0].record_id == "report-0000"

    def test_hold_preserved_in_records(self) -> None:
        result = materialize_report_records(FROZEN_BACKLOG_INVENTORY)
        for rec in result:
            assert rec.release_hold == "HOLD"

    def test_readiness_score_matches_promotion_default(self) -> None:
        inv = _make_single_record_inventory()
        result = materialize_report_records(inv)
        assert result[0].readiness_score == 0.2

    def test_file_path_preserved(self) -> None:
        inv = _make_single_record_inventory()
        result = materialize_report_records(inv)
        assert result[0].file_path == "scripts/example.py"


class TestMaterializeReportSummary:
    """Tests for materialize_report_summary."""

    def test_returns_frozen_backlog_report_summary(self) -> None:
        result = materialize_report_summary(FROZEN_BACKLOG_INVENTORY)
        assert isinstance(result, FrozenBacklogReportSummary)

    def test_total_files_matches(self) -> None:
        result = materialize_report_summary(FROZEN_BACKLOG_INVENTORY)
        assert result.total_files == 22

    def test_high_risk_count_matches(self) -> None:
        result = materialize_report_summary(FROZEN_BACKLOG_INVENTORY)
        assert result.high_risk_count == 9

    def test_medium_risk_count_matches(self) -> None:
        result = materialize_report_summary(FROZEN_BACKLOG_INVENTORY)
        assert result.medium_risk_count == 13

    def test_release_hold_is_hold(self) -> None:
        result = materialize_report_summary(FROZEN_BACKLOG_INVENTORY)
        assert result.release_hold == "HOLD"

    def test_no_live_is_true(self) -> None:
        result = materialize_report_summary(FROZEN_BACKLOG_INVENTORY)
        assert result.no_live is True

    def test_no_submit_is_true(self) -> None:
        result = materialize_report_summary(FROZEN_BACKLOG_INVENTORY)
        assert result.no_submit is True

    def test_no_exchange_is_true(self) -> None:
        result = materialize_report_summary(FROZEN_BACKLOG_INVENTORY)
        assert result.no_exchange is True

    def test_no_runtime_integration_is_true(self) -> None:
        result = materialize_report_summary(FROZEN_BACKLOG_INVENTORY)
        assert result.no_runtime_integration is True

    def test_no_planner_integration_is_true(self) -> None:
        result = materialize_report_summary(FROZEN_BACKLOG_INVENTORY)
        assert result.no_planner_integration is True


class TestMaterializeFullReport:
    """Tests for materialize_full_report."""

    def test_returns_tuple_of_two(self) -> None:
        result = materialize_full_report(FROZEN_BACKLOG_INVENTORY)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_summary(self) -> None:
        summary, _ = materialize_full_report(FROZEN_BACKLOG_INVENTORY)
        assert isinstance(summary, FrozenBacklogReportSummary)

    def test_second_element_is_records_tuple(self) -> None:
        _, records = materialize_full_report(FROZEN_BACKLOG_INVENTORY)
        assert isinstance(records, tuple)
        assert len(records) == 22

    def test_deterministic_output(self) -> None:
        r1 = materialize_full_report(FROZEN_BACKLOG_INVENTORY)
        r2 = materialize_full_report(FROZEN_BACKLOG_INVENTORY)
        assert r1[0].to_dict() == r2[0].to_dict()
        assert len(r1[1]) == len(r2[1])
        for a, b in zip(r1[1], r2[1]):
            assert a.to_dict() == b.to_dict()
