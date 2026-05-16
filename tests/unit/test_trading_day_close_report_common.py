from __future__ import annotations

from scripts.trading_day_close_report_common import (
    build_day_close_report_payload,
    compute_day_close_verdict,
    map_day_close_next_actions,
    render_day_close_markdown,
)


def test_compute_day_close_verdict_paths() -> None:
    verdict, reason = compute_day_close_verdict(
        critical_symbols_count=1,
        weak_symbols_count=0,
        queue_fail_count=0,
        run_fail_count=0,
        major_count=0,
        minor_count=0,
        low_count=0,
        required_missing_count=0,
        state_health="PASS",
        cleanup_needed_count=0,
        open_queue_count=0,
    )
    assert verdict == "FAIL"
    assert reason == "critical_position_protection_state_present"

    verdict2, reason2 = compute_day_close_verdict(
        critical_symbols_count=0,
        weak_symbols_count=0,
        queue_fail_count=0,
        run_fail_count=0,
        major_count=0,
        minor_count=0,
        low_count=1,
        required_missing_count=0,
        state_health="PASS",
        cleanup_needed_count=0,
        open_queue_count=0,
    )
    assert verdict2 == "PARTIAL"
    assert reason2 == "non_expected_warning_present"

    verdict3, reason3 = compute_day_close_verdict(
        critical_symbols_count=0,
        weak_symbols_count=0,
        queue_fail_count=0,
        run_fail_count=0,
        major_count=0,
        minor_count=0,
        low_count=0,
        required_missing_count=0,
        state_health="PASS",
        cleanup_needed_count=0,
        open_queue_count=0,
    )
    assert verdict3 == "PASS"
    assert reason3 == "clean_account_and_queue"


def test_map_day_close_next_actions() -> None:
    assert map_day_close_next_actions(verdict="PASS", reason="clean_account_and_queue") == ["no_action"]
    assert map_day_close_next_actions(verdict="FAIL", reason="submit_failed_detected") == [
        "inspect_submit_failures",
        "review_risk_events",
        "rerun_after_fix",
    ]
    assert map_day_close_next_actions(verdict="PARTIAL", reason="orphan_protection_requires_cleanup") == [
        "run_safe_flatten_dry_run_for_orphans",
        "manual_confirm_if_needed",
        "rerun_diagnosis",
    ]


def test_build_payload_and_render_markdown() -> None:
    payload = build_day_close_report_payload(
        ok=True,
        date="2026-05-17",
        env="testnet",
        symbols=["BTCUSDT"],
        final_verdict="PARTIAL",
        day_summary={"final_verdict": "PARTIAL"},
        state_summary={"UNKNOWN": []},
        run_summary={"approved_runs_count": 1},
        queue_summary={"pending": 1},
        health_summary={"aggregate_health": "PASS"},
        cleanup_summary={"orphan_symbols": []},
        guard_summary={"allowed": True},
        event_summary={"non_expected_warning_count": 1},
        file_summary={"ok": True},
        latest_snapshot={"snapshot_id": "x1"},
        latest_shift_review={"verdict": "PASS"},
        daily_level="PARTIAL",
        daily_reason="warn",
        verdict_reason="non_expected_warning_present",
        next_actions=["review_warnings_and_rerun"],
        output_md="logs/close.md",
        output_json="logs/close.json",
    )
    assert payload["ok"] is True
    assert payload["final_verdict"] == "PARTIAL"
    assert payload["next_actions"] == ["review_warnings_and_rerun"]

    md = render_day_close_markdown(
        title="Trading Day Close Report",
        header_lines=["date: 2026-05-17", "env: testnet"],
        sections=[("Summary", ["final_verdict: PARTIAL"])],
        next_actions=["review_warnings_and_rerun"],
    )
    assert "# Trading Day Close Report" in md
    assert "## Summary" in md
    assert "## Next Actions" in md
    assert "- review_warnings_and_rerun" in md
