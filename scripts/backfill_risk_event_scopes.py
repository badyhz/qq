from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.trade_logger import read_jsonl_rows


TEST_SCOPES = {"TEST_FIXTURE", "LOCAL_DRY_RUN", "LIVE_BLOCK_TEST"}
MOCK_POSITION_AMTS = {50.0, 100.0, -100.0}
MOCK_ALGO_IDS = {"stop_ok", "tp_ok", "sl_ok", "mock_algo", "mock_tp", "mock_sl"}
MOCK_ERROR_MESSAGES = {"x", "network down"}


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _infer_scope(row: dict[str, Any]) -> str:
    event_type = str(row.get("event_type", "")).strip().upper()
    component = str(row.get("component", "")).strip().lower()
    env = str(row.get("env", "")).strip().lower()
    context = dict(row.get("context", {})) if isinstance(row.get("context", {}), dict) else {}
    source_log = str(row.get("source_log", "")).strip().lower()
    message = str(row.get("message", "")).strip().lower()
    run_id = str(row.get("run_id", "")).strip()
    candidate_id = str(row.get("candidate_id", "")).strip()
    shift_id = str(row.get("shift_id", "")).strip()
    approved_run_id = str(row.get("approved_run_id", "")).strip()
    batch_id = str(row.get("batch_id", "")).strip()
    has_real_ref = bool(run_id or candidate_id or shift_id or approved_run_id or batch_id)
    existing = str(row.get("event_scope", "")).strip().upper()

    def _to_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    pos_amt = _to_float(context.get("position_amt", context.get("positionAmt", None)))
    error_message = str(context.get("error_message", context.get("error", ""))).strip().lower()
    latest_context = dict(context.get("latest", {})) if isinstance(context.get("latest", {}), dict) else {}
    latest_error_message = str(
        latest_context.get("error_message", latest_context.get("error", ""))
    ).strip().lower()
    latest_error_code = str(latest_context.get("error_code", "")).strip()
    state_context = dict(context.get("state", {})) if isinstance(context.get("state", {}), dict) else {}
    preflight_status = str(context.get("preflight_status", "")).strip().lower()
    state_error_code = str(state_context.get("error_code", "")).strip().lower()
    stop_algo_id = str(context.get("stop_loss_algo_id", "")).strip().lower()
    tp_algo_id = str(context.get("take_profit_algo_id", "")).strip().lower()
    looks_mock = False
    if pos_amt in MOCK_POSITION_AMTS:
        looks_mock = True
    if error_message in MOCK_ERROR_MESSAGES:
        looks_mock = True
    if stop_algo_id in MOCK_ALGO_IDS or tp_algo_id in MOCK_ALGO_IDS:
        looks_mock = True
    if str(context.get("submit_status", "")).strip().lower() == "submit_failed" and error_message == "x":
        looks_mock = True

    if event_type == "BATCH_SYMBOL_FAILED" and "batch skipped symbol due to risky preflight state" in message:
        if preflight_status == "preflight_unavailable" and state_error_code == "missing_testnet_api_key":
            return "LOCAL_DRY_RUN"

    if existing:
        return existing

    if "unit_test" in component or "pytest" in component:
        return "TEST_FIXTURE"
    if event_type == "CANDIDATE_SUBMITTED" and env == "testnet":
        return "TESTNET_REAL"
    if event_type == "LIVE_SUBMIT_BLOCKED":
        if str(context.get("production_like", "")).strip().lower() in {"1", "true", "yes"}:
            return "PRODUCTION_LIKE"
        return "LIVE_BLOCK_TEST"
    if event_type in {"NOTIFICATION_DRY_RUN", "FLATTEN_DRY_RUN_ONLY"}:
        return "LOCAL_DRY_RUN"
    if event_type == "NOTIFICATION_SEND_FAILED" and ("network down" in error_message or "network down" in message):
        return "TEST_FIXTURE"
    if event_type == "NOTIFICATION_SEND_FAILED" and str(context.get("channel", "")).strip().lower() == "wecom" and not has_real_ref:
        return "LOCAL_DRY_RUN"
    if _to_bool(context.get("dry_run", False), False):
        return "LOCAL_DRY_RUN"
    if event_type in {"MISSING_API_KEY", "API_AUTH_FAILED"}:
        if not has_real_ref:
            return "LOCAL_DRY_RUN"
        if looks_mock:
            return "TEST_FIXTURE"
    if event_type == "NAKED_POSITION_DETECTED":
        if looks_mock and (not has_real_ref):
            return "TEST_FIXTURE"
    if event_type in {"PROTECTIVE_ORDER_FAILED", "PROTECTIVE_ORDER_PARTIAL", "ORDER_WOULD_IMMEDIATELY_TRIGGER"}:
        if looks_mock or (not has_real_ref):
            return "TEST_FIXTURE"
    if event_type == "BATCH_SYMBOL_FAILED":
        if latest_error_message == "x":
            return "TEST_FIXTURE"
        if latest_error_code == "-1" and latest_error_message == "x":
            return "TEST_FIXTURE"
        if any(token in message for token in ["allowlist", "preflight_unavailable"]):
            if not has_real_ref:
                return "LOCAL_DRY_RUN"
        if "some candidates were skipped during candidate building" in message:
            return "LOCAL_DRY_RUN"
        if "error_message" in context and str(context.get("error_message", "")).strip().lower() == "x":
            return "TEST_FIXTURE"
    if source_log.endswith("logs/risk_events.jsonl") and looks_mock and (not has_real_ref):
        return "TEST_FIXTURE"
    if has_real_ref and env == "testnet":
        if event_type in {"CANDIDATE_SUBMITTED", "CANDIDATE_SUBMIT_FAILED", "CANDIDATE_SKIPPED_BY_PREFLIGHT"}:
            return "TESTNET_REAL"
        return "PRODUCTION_LIKE"
    if event_type in {"CANDIDATE_SUBMITTED", "CANDIDATE_SUBMIT_FAILED", "CANDIDATE_SKIPPED_BY_PREFLIGHT"}:
        return "LOCAL_DRY_RUN"
    if env == "testnet" and not has_real_ref:
        return "TEST_FIXTURE"
    if env == "testnet":
        return "PRODUCTION_LIKE"
    return "UNKNOWN"


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    scope = _infer_scope(payload)
    payload["event_scope"] = scope
    message = str(payload.get("message", "")).strip().lower()
    event_type = str(payload.get("event_type", "")).strip().upper()
    context = dict(payload.get("context", {})) if isinstance(payload.get("context", {}), dict) else {}
    state = dict(context.get("state", {})) if isinstance(context.get("state", {}), dict) else {}
    is_missing_key_preflight_skip = (
        event_type == "BATCH_SYMBOL_FAILED"
        and "batch skipped symbol due to risky preflight state" in message
        and str(context.get("preflight_status", "")).strip().lower() == "preflight_unavailable"
        and str(state.get("error_code", "")).strip().lower() == "missing_testnet_api_key"
    )
    expected_block_default = scope == "LIVE_BLOCK_TEST"
    if event_type == "BATCH_SYMBOL_FAILED" and "symbol rejected by allowlist" in message:
        expected_block_default = True
    if is_missing_key_preflight_skip:
        expected_block_default = True
    payload["is_test_event"] = bool(payload.get("is_test_event", scope in TEST_SCOPES))
    if is_missing_key_preflight_skip:
        payload["is_test_event"] = True
    payload["is_expected_block"] = bool(
        payload.get("is_expected_block", expected_block_default)
    )
    if event_type == "BATCH_SYMBOL_FAILED" and "symbol rejected by allowlist" in message:
        payload["is_expected_block"] = True
    if is_missing_key_preflight_skip:
        payload["is_expected_block"] = True
    for key in ("run_id", "candidate_id", "shift_id", "approved_run_id"):
        payload[key] = str(payload.get(key, "") or "")
    return payload


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


def _detect_dense_fixture_windows(rows: list[dict[str, Any]]) -> set[str]:
    counts: dict[str, int] = {}
    for row in rows:
        run_id = str(row.get("run_id", "")).strip()
        candidate_id = str(row.get("candidate_id", "")).strip()
        shift_id = str(row.get("shift_id", "")).strip()
        approved_run_id = str(row.get("approved_run_id", "")).strip()
        if run_id or candidate_id or shift_id or approved_run_id:
            continue
        dt = _parse_dt(row.get("ts_utc", ""))
        if dt is None:
            continue
        minute_key = dt.strftime("%Y-%m-%dT%H:%M")
        counts[minute_key] = int(counts.get(minute_key, 0)) + 1
    return {k for k, v in counts.items() if v >= 8}


def _write_jsonl(path: str, rows: list[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def backfill_risk_event_scopes(
    *,
    input_jsonl: str = "logs/risk_events.jsonl",
    output_jsonl: str = "logs/risk_events_scoped.jsonl",
    dry_run: bool = True,
    in_place: bool = False,
    strict_production_only: bool = False,
) -> dict[str, Any]:
    rows = read_jsonl_rows(input_jsonl)
    scoped = [_normalize_row(row) for row in rows]
    dense_minutes = _detect_dense_fixture_windows(scoped)
    for row in scoped:
        dt = _parse_dt(row.get("ts_utc", ""))
        if dt is None:
            continue
        minute_key = dt.strftime("%Y-%m-%dT%H:%M")
        if minute_key not in dense_minutes:
            continue
        if str(row.get("event_scope", "")).upper() in {"UNKNOWN", "PRODUCTION_LIKE"} and not any(
            str(row.get(key, "")).strip() for key in ("run_id", "candidate_id", "shift_id", "approved_run_id", "batch_id")
        ):
            row["event_scope"] = "TEST_FIXTURE"
            row["is_test_event"] = True
            row["is_expected_block"] = bool(str(row.get("event_type", "")).strip().upper() == "LIVE_SUBMIT_BLOCKED")
    target = input_jsonl if in_place else output_jsonl

    count_by_scope: dict[str, int] = {}
    unknown_by_type: dict[str, int] = {}
    for row in scoped:
        scope = str(row.get("event_scope", "UNKNOWN")).upper()
        count_by_scope[scope] = int(count_by_scope.get(scope, 0)) + 1
        if scope == "UNKNOWN":
            event_type = str(row.get("event_type", "UNKNOWN")).upper()
            unknown_by_type[event_type] = int(unknown_by_type.get(event_type, 0)) + 1

    if not dry_run:
        _write_jsonl(target, scoped)

    strict_rows = 0
    if strict_production_only:
        for row in scoped:
            scope = str(row.get("event_scope", "UNKNOWN")).upper()
            if scope in {"TESTNET_REAL", "PRODUCTION_LIKE"} and (not bool(row.get("is_test_event", False))):
                strict_rows += 1

    return {
        "ok": True,
        "input_jsonl": input_jsonl,
        "output_jsonl": target,
        "dry_run": bool(dry_run),
        "in_place": bool(in_place),
        "total_rows": len(rows),
        "scoped_rows": len(scoped),
        "count_by_scope": count_by_scope,
        "unknown_events_count": int(count_by_scope.get("UNKNOWN", 0)),
        "top_unknown_event_types": sorted(
            [{"event_type": k, "count": v} for k, v in unknown_by_type.items()],
            key=lambda item: int(item.get("count", 0)),
            reverse=True,
        )[:10],
        "strict_production_only": bool(strict_production_only),
        "strict_production_rows": strict_rows,
        "would_write": target if dry_run else "",
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill risk event scope fields into a new JSONL")
    parser.add_argument("--input-jsonl", default="logs/risk_events.jsonl")
    parser.add_argument("--output-jsonl", default="logs/risk_events_scoped.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--strict-production-only", action="store_true")
    parser.add_argument("--json-summary", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = backfill_risk_event_scopes(
        input_jsonl=str(args.input_jsonl or "logs/risk_events.jsonl"),
        output_jsonl=str(args.output_jsonl or "logs/risk_events_scoped.jsonl"),
        dry_run=True if bool(args.dry_run) else False,
        in_place=bool(args.in_place),
        strict_production_only=bool(args.strict_production_only),
    )
    if bool(args.json_summary):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"input_jsonl={result.get('input_jsonl', '')}")
    print(f"output_jsonl={result.get('output_jsonl', '')}")
    print(f"dry_run={result.get('dry_run', True)}")
    print(f"total_rows={result.get('total_rows', 0)}")


if __name__ == "__main__":
    main()
