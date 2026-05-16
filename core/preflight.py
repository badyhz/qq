from __future__ import annotations

from typing import Any

READINESS_READY = "READY"
READINESS_NOT_READY = "NOT_READY"
READINESS_READY_WITH_WARNINGS = "READY_WITH_WARNINGS"


def build_issue(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message}


def finalize_report(*, mode: str, checked_items: dict[str, Any], blocking_issues: list[dict], warnings: list[str]) -> dict[str, Any]:
    return {
        "ok": len(blocking_issues) == 0,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "mode": mode,
        "checked_items": checked_items,
    }


def summarize_readiness(
    *,
    mode: str,
    preflight_report: dict[str, Any],
    connectivity_result: dict[str, Any],
    external_state_result: dict[str, Any],
    runtime_status: dict[str, Any],
) -> dict[str, Any]:
    blocking_issues: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not bool(preflight_report.get("ok", False)):
        blocking_issues.extend(list(preflight_report.get("blocking_issues", [])))
    warnings.extend(list(preflight_report.get("warnings", [])))

    connectivity_ok = bool(connectivity_result.get("success", False))
    if not connectivity_ok and mode == "live":
        blocking_issues.append(
            build_issue("connectivity_failed", str(connectivity_result.get("error", "connectivity_failed")))
        )
    elif not connectivity_ok:
        warnings.append(f"connectivity_unavailable:{connectivity_result.get('error', 'unknown')}")
    warnings.extend(list(connectivity_result.get("warnings", [])))

    external_ok = bool(external_state_result.get("success", False))
    if not external_ok and mode == "live":
        blocking_issues.append(
            build_issue("external_state_sync_failed", str(external_state_result.get("reason", "external_sync_failed")))
        )
    elif not external_ok:
        warnings.append(f"external_state_sync_skipped:{external_state_result.get('reason', 'unknown')}")
    warnings.extend(list(external_state_result.get("warnings", [])))

    runtime_overall = str(runtime_status.get("overall_status", "OK")).upper()
    if runtime_overall == "ERROR":
        blocking_issues.append(build_issue("runtime_status_error", "Runtime status is ERROR."))
    elif runtime_overall == "WARN":
        warnings.append("runtime_status_warn")

    deduped_warnings = list(dict.fromkeys([str(item) for item in warnings if str(item)]))
    status = READINESS_READY
    if blocking_issues:
        status = READINESS_NOT_READY
    elif deduped_warnings:
        status = READINESS_READY_WITH_WARNINGS

    return {
        "status": status,
        "mode": mode,
        "blocking_issues": blocking_issues,
        "warnings": deduped_warnings,
    }
