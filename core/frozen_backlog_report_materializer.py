"""T1525 - Frozen Backlog Report Materializer."""
from __future__ import annotations

from core.frozen_backlog_inventory import FrozenBacklogInventory
from core.frozen_backlog_report_record import FrozenBacklogReportRecord
from core.frozen_backlog_report_summary import FrozenBacklogReportSummary


def materialize_report_records(
    inventory: FrozenBacklogInventory,
) -> tuple[FrozenBacklogReportRecord, ...]:
    """Convert inventory records to report records.

    Pure deterministic. No I/O. No timestamps. No network.
    """
    records: list[FrozenBacklogReportRecord] = []
    for idx, rec in enumerate(inventory.records):
        records.append(
            FrozenBacklogReportRecord(
                record_id=f"report-{idx:04d}",
                file_path=rec.file_path,
                risk_class=rec.risk_class,
                category=rec.category,
                allowed_actions=rec.allowed_actions,
                forbidden_actions=rec.forbidden_actions,
                required_evidence=rec.required_evidence,
                readiness_score=rec.promotion_readiness_default,
                unlock_recommendation=rec.unlock_recommendation,
                release_hold=rec.release_hold,
            )
        )
    return tuple(records)


def materialize_report_summary(
    inventory: FrozenBacklogInventory,
) -> FrozenBacklogReportSummary:
    """Create summary from inventory.

    Pure deterministic. No I/O. No timestamps. No network.
    """
    return FrozenBacklogReportSummary(
        summary_id=f"summary-{inventory.inventory_id}",
        total_files=inventory.total_count,
        high_risk_count=inventory.high_risk_count,
        medium_risk_count=inventory.medium_risk_count,
        release_hold="HOLD",
        no_live=True,
        no_submit=True,
        no_exchange=True,
        no_runtime_integration=True,
        no_planner_integration=True,
    )


def materialize_full_report(
    inventory: FrozenBacklogInventory,
) -> tuple[FrozenBacklogReportSummary, tuple[FrozenBacklogReportRecord, ...]]:
    """Return both summary and records.

    Pure deterministic. No I/O. No timestamps. No network.
    """
    summary = materialize_report_summary(inventory)
    records = materialize_report_records(inventory)
    return (summary, records)
