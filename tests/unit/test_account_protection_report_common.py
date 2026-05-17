from __future__ import annotations

from scripts.account_protection_report_common import (
    classify_account_risk_guard,
    classify_protection_health,
    render_account_protection_markdown,
    summarize_account_risk_state,
    summarize_protection_health,
)


def test_account_risk_summary_and_classification_blocked() -> None:
    summary = summarize_account_risk_state(
        [
            {
                "allowed": False,
                "reason": "max_positions_exceeded",
                "current_open_positions": 4,
                "total_notional": 1200.5,
                "duplicate_candidate_id_count": 0,
                "pending_or_approved_count": 0,
            }
        ]
    )
    verdict = classify_account_risk_guard(summary)
    assert summary["blocked_count"] == 1
    assert verdict["guard_status"] == "BLOCKED"


def test_account_risk_partial_for_pending_candidates() -> None:
    summary = summarize_account_risk_state(
        [{"allowed": True, "pending_or_approved_count": 2, "duplicate_candidate_id_count": 0}]
    )
    verdict = classify_account_risk_guard(summary)
    assert verdict["guard_status"] == "PARTIAL"
    assert verdict["guard_reason"] == "pending_or_approved_candidates_present"


def test_protection_health_orphan_and_missing_protection() -> None:
    summary = summarize_protection_health(
        [
            {"protection_health": "ORPHAN_PROTECTION"},
            {"protection_health": "PARTIAL_PROTECTION"},
        ]
    )
    verdict = classify_protection_health(summary)
    assert summary["warning_count"] == 1
    assert summary["failed_count"] == 1
    assert verdict["aggregate_health"] == "FAIL"


def test_render_account_protection_markdown_sections() -> None:
    md = render_account_protection_markdown(
        {
            "account_risk": {
                "guard_status": "PASS",
                "guard_reason": "ok",
                "blocked_count": 0,
                "max_open_positions": 1,
                "total_notional": 10.0,
            },
            "protection_health": {
                "aggregate_health": "PARTIAL",
                "aggregate_reason": "orphan_or_unknown_detected",
                "critical_count": 0,
                "failed_count": 0,
                "warning_count": 1,
            },
        }
    )
    assert "# Account Protection Summary" in md
    assert "## Account Risk Guard" in md
    assert "## Protection Health" in md
