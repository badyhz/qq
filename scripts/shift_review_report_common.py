from __future__ import annotations

from typing import Any


def compute_shift_review_verdict(
    *,
    snapshot_level: str,
    daily_level: str,
    artifact_ok: bool,
    required_missing_count: int,
    optional_missing_count: int,
    latest_is_noop: bool,
    open_queue_count: int,
    fail_count: int,
    run_failed_count: int,
    run_done_count: int,
    major_count: int,
    minor_count: int,
    low_count: int,
) -> tuple[str, str]:
    snapshot = str(snapshot_level or "UNKNOWN").strip().upper()
    daily = str(daily_level or "").strip().upper()

    if snapshot == "CRITICAL":
        return "FAIL", "state_snapshot_critical"
    if major_count > 0 or minor_count > 0:
        return "FAIL", "non_expected_risk_events_present"
    if fail_count > 0 or run_failed_count > 0:
        return "FAIL", "submit_failure_detected"
    if run_done_count > 0 and required_missing_count > 0:
        return "FAIL", "submitted_run_missing_required_artifacts"
    if (not artifact_ok) and required_missing_count > 0:
        return "FAIL", "artifact_critical_missing"

    if (
        snapshot == "CLEAN"
        and daily == "PASS"
        and artifact_ok
        and required_missing_count <= 0
        and major_count <= 0
        and minor_count <= 0
        and low_count <= 0
    ):
        if open_queue_count > 0:
            return "PARTIAL", "candidate_queue_pending_or_approved"
        return "PASS", "clean_shift_pass"

    if daily == "PARTIAL":
        return "PARTIAL", "daily_summary_partial"
    if open_queue_count > 0:
        return "PARTIAL", "candidate_queue_pending_or_approved"
    if optional_missing_count > 0 and (not latest_is_noop):
        return "PARTIAL", "optional_artifacts_missing"

    if snapshot == "CLEAN" and daily == "PASS" and artifact_ok and required_missing_count <= 0:
        return "PASS", "clean_state_and_artifacts_ok"
    return "PARTIAL", "mixed_signals_require_operator_review"


def map_shift_next_actions(*, verdict: str, snapshot_level: str, open_queue_count: int) -> list[str]:
    state = str(snapshot_level or "UNKNOWN").strip().upper()
    if verdict == "FAIL":
        if state == "CRITICAL":
            return ["cleanup_orphan", "run_next_clean_shift"]
        return ["review_candidates", "run_next_clean_shift"]
    if verdict == "PARTIAL":
        if open_queue_count > 0:
            return ["review_candidates", "approve_one_candidate", "run_next_clean_shift"]
        return ["run_next_clean_shift"]
    return ["no_action"]


def build_shift_report_payload(
    *,
    overview: dict[str, Any],
    state_snapshot: dict[str, Any],
    queue_review: dict[str, Any],
    quality_review: dict[str, Any],
    run_review: dict[str, Any],
    state_review: dict[str, Any],
    event_review: dict[str, Any],
    file_review: dict[str, Any],
    daily_level: str,
    daily_reason: str,
    verdict: str,
    verdict_reason: str,
    next_actions: list[str],
    output_md: str,
    output_json: str,
) -> dict[str, Any]:
    return {
        "ok": True,
        "shift_overview": dict(overview),
        "state_snapshot": dict(state_snapshot),
        "candidate_review": dict(queue_review),
        "candidate_quality_summary": dict(quality_review),
        "execution_review": dict(run_review),
        "protection_review": dict(state_review),
        "risk_review": dict(event_review),
        "artifact_review": dict(file_review),
        "daily_summary_verdict": str(daily_level or ""),
        "daily_summary_reason": str(daily_reason or ""),
        "verdict": str(verdict or ""),
        "verdict_reason": str(verdict_reason or ""),
        "next_actions": list(next_actions or []),
        "output_md": str(output_md or ""),
        "output_json": str(output_json or ""),
    }


def render_shift_report_markdown(
    *,
    title: str,
    sections: list[tuple[str, list[str]]],
    verdict: str,
    verdict_reason: str,
    next_actions: list[str],
) -> str:
    lines = [f"# {title}", ""]
    for section_name, section_lines in list(sections or []):
        lines.append(f"## {section_name}")
        for item in list(section_lines or []):
            lines.append(f"- {item}")
        lines.append("")
    lines.extend([
        "## Verdict",
        f"- verdict: {verdict}",
        f"- reason: {verdict_reason}",
        "",
        "## Next Actions",
    ])
    for action in list(next_actions or []):
        lines.append(f"- {action}")
    return "\n".join(lines) + "\n"
