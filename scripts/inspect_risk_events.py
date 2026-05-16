from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.risk_event_logger import is_expected_safety_rejection


def _to_csv_set(value: str, *, upper: bool = True) -> set[str]:
    items = [item.strip() for item in str(value or "").split(",") if item.strip()]
    if upper:
        return {item.upper() for item in items}
    return set(items)


def _parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _load_jsonl_with_invalid(path: Path) -> tuple[list[dict[str, Any]], int]:
    if not path.exists():
        return [], 0
    rows: list[dict[str, Any]] = []
    invalid_rows = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            invalid_rows += 1
            continue
        if isinstance(payload, dict):
            rows.append(payload)
        else:
            invalid_rows += 1
    return rows, invalid_rows


def _is_suspected_test_noise(row: dict[str, Any]) -> bool:
    scope = str(row.get("event_scope", "UNKNOWN")).strip().upper()
    if bool(row.get("is_test_event", False)):
        return True
    if scope in {"TEST_FIXTURE", "LOCAL_DRY_RUN", "LIVE_BLOCK_TEST"}:
        return True
    message = str(row.get("message", "")).strip().lower()
    context = dict(row.get("context", {})) if isinstance(row.get("context", {}), dict) else {}
    latest = dict(context.get("latest", {})) if isinstance(context.get("latest", {}), dict) else {}
    error_message = str(context.get("error_message", context.get("error", latest.get("error_message", "")))).strip().lower()
    if error_message in {"x", "network down"}:
        return True
    if "unit_test" in str(row.get("component", "")).strip().lower() or "pytest" in str(row.get("component", "")).strip().lower():
        return True
    if str(latest.get("error_message", "")).strip().lower() == "x":
        return True
    if "mock" in message:
        return True
    return False


def _match_filters(
    row: dict[str, Any],
    *,
    event_scope: set[str],
    severity: set[str],
    event_type: set[str],
    symbol: str,
    component: str,
    since_dt: datetime | None,
    until_dt: datetime | None,
) -> bool:
    scope_value = str(row.get("event_scope", "UNKNOWN")).strip().upper() or "UNKNOWN"
    severity_value = str(row.get("severity", "UNKNOWN")).strip().upper() or "UNKNOWN"
    type_value = str(row.get("event_type", "UNKNOWN")).strip().upper() or "UNKNOWN"
    symbol_value = str(row.get("symbol", "")).strip().upper()
    component_value = str(row.get("component", "")).strip().lower()
    ts = _parse_dt(row.get("ts_utc", ""))

    if event_scope and scope_value not in event_scope:
        return False
    if severity and severity_value not in severity:
        return False
    if event_type and type_value not in event_type:
        return False
    if symbol and symbol_value != symbol:
        return False
    if component and component_value != component:
        return False
    if since_dt is not None and (ts is None or ts < since_dt):
        return False
    if until_dt is not None and (ts is None or ts > until_dt):
        return False
    return True


def inspect_risk_events(
    *,
    input_jsonl: str = "logs/risk_events_scoped_v3.jsonl",
    event_scope: str = "",
    severity: str = "",
    event_type: str = "",
    symbol: str = "",
    component: str = "",
    limit: int = 20,
    since_utc: str = "",
    until_utc: str = "",
) -> dict[str, Any]:
    path = Path(input_jsonl)
    if not path.exists():
        return {
            "ok": False,
            "input_jsonl": input_jsonl,
            "error": "file_not_found",
            "total_rows": 0,
            "filtered_rows": 0,
            "invalid_rows": 0,
            "latest_events": [],
            "recommendations": ["check_input_jsonl_path"],
        }

    rows, invalid_rows = _load_jsonl_with_invalid(path)
    scope_filter = _to_csv_set(event_scope, upper=True)
    severity_filter = _to_csv_set(severity, upper=True)
    type_filter = _to_csv_set(event_type, upper=True)
    symbol_filter = str(symbol or "").strip().upper()
    component_filter = str(component or "").strip().lower()
    since_dt = _parse_dt(since_utc)
    until_dt = _parse_dt(until_utc)
    resolved_limit = max(1, int(limit or 20))

    filtered: list[dict[str, Any]] = []
    count_by_scope: dict[str, int] = {}
    count_by_severity: dict[str, int] = {}
    count_by_event_type: dict[str, int] = {}
    count_by_component: dict[str, int] = {}
    unknown_by_type: dict[str, int] = {}
    unknown_by_component: dict[str, int] = {}
    suspected_test_noise_count = 0
    production_like_error_count = 0
    production_like_non_expected_error_count = 0
    expected_safety_rejection_count = 0
    latest_critical: dict[str, Any] = {}
    latest_error: dict[str, Any] = {}

    for row in rows:
        if not _match_filters(
            row,
            event_scope=scope_filter,
            severity=severity_filter,
            event_type=type_filter,
            symbol=symbol_filter,
            component=component_filter,
            since_dt=since_dt,
            until_dt=until_dt,
        ):
            continue
        filtered.append(row)

        scope_value = str(row.get("event_scope", "UNKNOWN")).strip().upper() or "UNKNOWN"
        severity_value = str(row.get("severity", "UNKNOWN")).strip().upper() or "UNKNOWN"
        type_value = str(row.get("event_type", "UNKNOWN")).strip().upper() or "UNKNOWN"
        component_value = str(row.get("component", "UNKNOWN")).strip() or "UNKNOWN"
        count_by_scope[scope_value] = int(count_by_scope.get(scope_value, 0)) + 1
        count_by_severity[severity_value] = int(count_by_severity.get(severity_value, 0)) + 1
        count_by_event_type[type_value] = int(count_by_event_type.get(type_value, 0)) + 1
        count_by_component[component_value] = int(count_by_component.get(component_value, 0)) + 1

        if scope_value == "UNKNOWN":
            unknown_by_type[type_value] = int(unknown_by_type.get(type_value, 0)) + 1
            unknown_by_component[component_value] = int(unknown_by_component.get(component_value, 0)) + 1
        if _is_suspected_test_noise(row):
            suspected_test_noise_count += 1
        is_expected = is_expected_safety_rejection(row)
        if scope_value == "PRODUCTION_LIKE" and severity_value == "ERROR":
            production_like_error_count += 1
            if not is_expected:
                production_like_non_expected_error_count += 1
        if is_expected:
            expected_safety_rejection_count += 1
        if severity_value == "CRITICAL":
            latest_critical = row
        if severity_value == "ERROR":
            latest_error = row

    latest_events = sorted(
        filtered,
        key=lambda row: _parse_dt(row.get("ts_utc", "")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )[:resolved_limit]
    unknown_events_count = int(count_by_scope.get("UNKNOWN", 0))

    recommendations: list[str] = []
    if not latest_critical:
        recommendations.append("no_critical_events")
    if production_like_non_expected_error_count > 0:
        recommendations.append("review_production_like_errors")
    if expected_safety_rejection_count > 0:
        recommendations.append("allowlist_rejections_are_expected")
    if suspected_test_noise_count > 0:
        recommendations.append("consider_using_production_only")
    if unknown_events_count > 0:
        recommendations.append("inspect_unknown_events")
        recommendations.append("run_backfill_scopes")

    return {
        "ok": True,
        "input_jsonl": input_jsonl,
        "total_rows": len(rows),
        "filtered_rows": len(filtered),
        "invalid_rows": invalid_rows,
        "count_by_scope": count_by_scope,
        "count_by_severity": count_by_severity,
        "count_by_event_type": count_by_event_type,
        "count_by_component": count_by_component,
        "top_unknown_event_types": sorted(
            [{"event_type": key, "count": value} for key, value in unknown_by_type.items()],
            key=lambda item: int(item.get("count", 0)),
            reverse=True,
        )[:10],
        "top_unknown_components": sorted(
            [{"component": key, "count": value} for key, value in unknown_by_component.items()],
            key=lambda item: int(item.get("count", 0)),
            reverse=True,
        )[:10],
        "unknown_events_count": unknown_events_count,
        "latest_critical": latest_critical,
        "latest_error": latest_error,
        "latest_events": latest_events,
        "suspected_test_noise_count": suspected_test_noise_count,
        "production_like_error_count": production_like_error_count,
        "production_like_non_expected_error_count": production_like_non_expected_error_count,
        "expected_safety_rejection_count": expected_safety_rejection_count,
        "recommendations": sorted(set(recommendations)),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only risk events inspector for audit and daily-verdict diagnostics")
    parser.add_argument("--input-jsonl", default="logs/risk_events_scoped_v3.jsonl")
    parser.add_argument("--event-scope", default="")
    parser.add_argument("--severity", default="")
    parser.add_argument("--event-type", default="")
    parser.add_argument("--symbol", default="")
    parser.add_argument("--component", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--since-utc", default="")
    parser.add_argument("--until-utc", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def _print_human(summary: dict[str, Any]) -> None:
    print(f"ok={summary.get('ok', False)}")
    print(f"input_jsonl={summary.get('input_jsonl', '')}")
    if not bool(summary.get("ok", False)):
        print(f"error={summary.get('error', '')}")
        return
    print(f"total_rows={summary.get('total_rows', 0)}")
    print(f"filtered_rows={summary.get('filtered_rows', 0)}")
    print(f"invalid_rows={summary.get('invalid_rows', 0)}")
    print(f"unknown_events_count={summary.get('unknown_events_count', 0)}")
    print(f"suspected_test_noise_count={summary.get('suspected_test_noise_count', 0)}")
    print(f"production_like_error_count={summary.get('production_like_error_count', 0)}")
    print(f"expected_safety_rejection_count={summary.get('expected_safety_rejection_count', 0)}")
    print(f"recommendations={json.dumps(summary.get('recommendations', []), ensure_ascii=False)}")


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = inspect_risk_events(
        input_jsonl=str(args.input_jsonl or "logs/risk_events_scoped_v3.jsonl"),
        event_scope=str(args.event_scope or ""),
        severity=str(args.severity or ""),
        event_type=str(args.event_type or ""),
        symbol=str(args.symbol or ""),
        component=str(args.component or ""),
        limit=int(args.limit or 20),
        since_utc=str(args.since_utc or ""),
        until_utc=str(args.until_utc or ""),
    )
    if bool(args.json):
        print(json.dumps(summary, ensure_ascii=False))
        return
    _print_human(summary)


if __name__ == "__main__":
    main()
