from __future__ import annotations

from scripts.shift_review_report_common import (
    build_shift_report_payload,
    compute_shift_review_verdict,
    map_shift_next_actions,
    render_shift_report_markdown,
)


def test_compute_shift_review_verdict_fail_and_pass_paths() -> None:
    verdict, reason = compute_shift_review_verdict(
        snapshot_level="CRITICAL",
        daily_level="PASS",
        artifact_ok=True,
        required_missing_count=0,
        optional_missing_count=0,
        latest_is_noop=False,
        open_queue_count=0,
        fail_count=0,
        run_failed_count=0,
        run_done_count=0,
        major_count=0,
        minor_count=0,
        low_count=0,
    )
    assert verdict == "FAIL"
    assert reason == "state_snapshot_critical"

    verdict2, reason2 = compute_shift_review_verdict(
        snapshot_level="CLEAN",
        daily_level="PASS",
        artifact_ok=True,
        required_missing_count=0,
        optional_missing_count=0,
        latest_is_noop=False,
        open_queue_count=0,
        fail_count=0,
        run_failed_count=0,
        run_done_count=0,
        major_count=0,
        minor_count=0,
        low_count=0,
    )
    assert verdict2 == "PASS"
    assert reason2 == "clean_shift_pass"


def test_map_shift_next_actions() -> None:
    assert map_shift_next_actions(verdict="FAIL", snapshot_level="CRITICAL", open_queue_count=0) == [
        "cleanup_orphan",
        "run_next_clean_shift",
    ]
    assert map_shift_next_actions(verdict="PARTIAL", snapshot_level="CLEAN", open_queue_count=2) == [
        "review_candidates",
        "approve_one_candidate",
        "run_next_clean_shift",
    ]
    assert map_shift_next_actions(verdict="PASS", snapshot_level="CLEAN", open_queue_count=0) == ["no_action"]


def test_build_payload_and_render_markdown() -> None:
    payload = build_shift_report_payload(
        overview={"date": "2026-05-17", "env": "testnet", "symbols": ["BTCUSDT"]},
        state_snapshot={"snapshot_id": "s1"},
        queue_review={"pending": 1},
        quality_review={"high_count": 2},
        run_review={"latest_run_id": "r1"},
        state_review={"FLAT_CLEAN": 1},
        event_review={"non_expected_critical_count": 0},
        file_review={"ok": True},
        daily_level="PASS",
        daily_reason="ok",
        verdict="PARTIAL",
        verdict_reason="candidate_queue_pending_or_approved",
        next_actions=["review_candidates"],
        output_md="logs/a.md",
        output_json="logs/a.json",
    )
    assert payload["shift_overview"]["env"] == "testnet"
    assert payload["verdict"] == "PARTIAL"
    assert payload["next_actions"] == ["review_candidates"]

    md = render_shift_report_markdown(
        title="Shift Review Report",
        sections=[("Summary", ["date: 2026-05-17", "env: testnet"])],
        verdict="PARTIAL",
        verdict_reason="candidate_queue_pending_or_approved",
        next_actions=["review_candidates"],
    )
    assert "# Shift Review Report" in md
    assert "## Summary" in md
    assert "## Verdict" in md
    assert "## Next Actions" in md
    assert "- review_candidates" in md
