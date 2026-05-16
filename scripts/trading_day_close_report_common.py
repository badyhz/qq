from __future__ import annotations

from typing import Any


def compute_day_close_verdict(
    *,
    critical_symbols_count: int,
    weak_symbols_count: int,
    queue_fail_count: int,
    run_fail_count: int,
    major_count: int,
    minor_count: int,
    low_count: int,
    required_missing_count: int,
    state_health: str,
    cleanup_needed_count: int,
    open_queue_count: int,
) -> tuple[str, str]:
    health = str(state_health or "").strip().upper()

    if critical_symbols_count > 0 or weak_symbols_count > 0:
        return "FAIL", "critical_position_protection_state_present"
    if queue_fail_count > 0 or run_fail_count > 0:
        return "FAIL", "submit_failed_detected"
    if major_count > 0 or minor_count > 0:
        return "FAIL", "non_expected_critical_or_error_present"
    if required_missing_count > 0:
        return "FAIL", "artifact_missing_files_present"
    if health == "FAIL":
        return "FAIL", "protection_health_failed"

    if cleanup_needed_count > 0:
        return "PARTIAL", "orphan_protection_requires_cleanup"
    if open_queue_count > 0:
        return "PARTIAL", "pending_or_approved_candidates_exist"
    if low_count > 0:
        return "PARTIAL", "non_expected_warning_present"
    if health == "PARTIAL":
        return "PARTIAL", "protection_health_partial"
    return "PASS", "clean_account_and_queue"


def map_day_close_next_actions(*, verdict: str, reason: str) -> list[str]:
    why = str(reason or "")
    if verdict == "PASS":
        return ["no_action"]
    if verdict == "FAIL":
        if "position_protection" in why:
            return ["stop_new_orders", "repair_protection_or_flatten", "rerun_state_snapshot"]
        if "submit_failed" in why:
            return ["inspect_submit_failures", "review_risk_events", "rerun_after_fix"]
        return ["inspect_failures", "repair_and_rerun"]
    if "orphan" in why:
        return ["run_safe_flatten_dry_run_for_orphans", "manual_confirm_if_needed", "rerun_diagnosis"]
    if "pending_or_approved" in why:
        return ["review_candidates", "approve_or_reject_pending"]
    return ["review_warnings_and_rerun"]


def build_day_close_report_payload(
    *,
    ok: bool,
    date: str,
    env: str,
    symbols: list[str],
    final_verdict: str,
    day_summary: dict[str, Any],
    state_summary: dict[str, Any],
    run_summary: dict[str, Any],
    queue_summary: dict[str, Any],
    health_summary: dict[str, Any],
    cleanup_summary: dict[str, Any],
    guard_summary: dict[str, Any],
    event_summary: dict[str, Any],
    file_summary: dict[str, Any],
    latest_snapshot: dict[str, Any],
    latest_shift_review: dict[str, Any],
    daily_level: str,
    daily_reason: str,
    verdict_reason: str,
    next_actions: list[str],
    output_md: str,
    output_json: str,
) -> dict[str, Any]:
    return {
        "ok": bool(ok),
        "date": str(date or ""),
        "env": str(env or ""),
        "symbols": list(symbols or []),
        "day_summary": dict(day_summary),
        "final_account_state": dict(state_summary),
        "execution_summary": dict(run_summary),
        "candidate_summary": dict(queue_summary),
        "protection_summary": dict(health_summary),
        "orphan_diagnosis": dict(cleanup_summary),
        "risk_guard_summary": dict(guard_summary),
        "risk_events_summary": dict(event_summary),
        "artifacts_summary": dict(file_summary),
        "latest_snapshot": dict(latest_snapshot),
        "latest_shift_review": dict(latest_shift_review),
        "daily_summary_verdict": str(daily_level or ""),
        "daily_summary_reason": str(daily_reason or ""),
        "final_verdict": str(final_verdict or ""),
        "verdict_reason": str(verdict_reason or ""),
        "next_actions": list(next_actions or []),
        "output_md": str(output_md or ""),
        "output_json": str(output_json or ""),
    }


def render_day_close_markdown(
    *,
    title: str,
    header_lines: list[str],
    sections: list[tuple[str, list[str]]],
    next_actions: list[str],
) -> str:
    lines = [f"# {title}", ""]
    for item in list(header_lines or []):
        lines.append(f"- {item}")
    lines.append("")
    for section_name, section_lines in list(sections or []):
        lines.append(f"## {section_name}")
        for item in list(section_lines or []):
            lines.append(f"- {item}")
        lines.append("")
    lines.append("## Next Actions")
    for action in list(next_actions or []):
        lines.append(f"- {action}")
    return "\n".join(lines) + "\n"
