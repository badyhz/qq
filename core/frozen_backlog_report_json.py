"""T1529 - Frozen Backlog Report JSON Renderer.

Pure functions. No I/O. No timestamps. No network.
Deterministic JSON with stable key ordering.
"""
from __future__ import annotations

import json

from core.frozen_backlog_report_record import FrozenBacklogReportRecord
from core.frozen_backlog_report_summary import FrozenBacklogReportSummary


def render_record_dict(record: FrozenBacklogReportRecord) -> dict[str, object]:
    """Convert a single FrozenBacklogReportRecord to a plain dict."""
    return {
        "record_id": record.record_id,
        "file_path": record.file_path,
        "risk_class": record.risk_class,
        "category": record.category,
        "allowed_actions": list(record.allowed_actions),
        "forbidden_actions": list(record.forbidden_actions),
        "required_evidence": list(record.required_evidence),
        "readiness_score": record.readiness_score,
        "unlock_recommendation": record.unlock_recommendation,
        "release_hold": record.release_hold,
    }


def render_summary_dict(summary: FrozenBacklogReportSummary) -> dict[str, object]:
    """Convert FrozenBacklogReportSummary to a plain dict."""
    return {
        "summary_id": summary.summary_id,
        "total_files": summary.total_files,
        "high_risk_count": summary.high_risk_count,
        "medium_risk_count": summary.medium_risk_count,
        "release_hold": summary.release_hold,
        "no_live": summary.no_live,
        "no_submit": summary.no_submit,
        "no_exchange": summary.no_exchange,
        "no_runtime_integration": summary.no_runtime_integration,
        "no_planner_integration": summary.no_planner_integration,
    }


def render_report_json(
    summary: FrozenBacklogReportSummary,
    records: tuple[FrozenBacklogReportRecord, ...],
) -> str:
    """Generate deterministic JSON string with summary and records."""
    payload = {
        "summary": render_summary_dict(summary),
        "records": [render_record_dict(r) for r in records],
    }
    return json.dumps(payload, sort_keys=True)
