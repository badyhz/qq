from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.binance_testnet_client import BinanceFuturesTestnetClient
from core.trade_logger import read_jsonl_rows
from scripts.protection_monitor_report_common import (
    classify_protection_trigger_outcome,
    summarize_protection_trigger_outcomes,
    render_protection_monitor_markdown,
)
from scripts.submit_replayed_testnet_payload import (
    DEFAULT_TESTNET_BASE_URL,
    _build_protection_state,
    _normalize_algo_order_type,
    _normalize_algo_rows,
    _normalize_algo_status,
    _resolve_testnet_base_url,
    _to_float,
)


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


def _to_ts_ms(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _extract_algo_trigger(rows: list[dict[str, Any]], order_type: str) -> float:
    for row in rows:
        if _normalize_algo_order_type(row) != order_type:
            continue
        for key in ("triggerPrice", "stopPrice", "activatePrice"):
            price = _to_float(row.get(key, 0.0), 0.0)
            if price > 0:
                return price
    return 0.0


def _extract_symbol_state_from_snapshot(snapshot_payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    for row in [item for item in list(snapshot_payload.get("per_symbol_state", [])) if isinstance(item, dict)]:
        if str(row.get("symbol", "")).strip().upper() == symbol:
            result = dict(row)
            result["ts_utc"] = str(snapshot_payload.get("ts_utc", ""))
            return result
    return {}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _latest_matching_run(
    *,
    approved_runs_root: Path,
    symbol: str,
    candidate_id: str,
    since_dt: datetime,
) -> tuple[dict[str, Any], Path | None]:
    latest_payload: dict[str, Any] = {}
    latest_dir: Path | None = None
    latest_dt = datetime.min.replace(tzinfo=timezone.utc)
    for path in approved_runs_root.glob("*/summary.json"):
        payload = _load_json(path)
        ts = _parse_dt(payload.get("completed_at_utc", "") or payload.get("started_at_utc", ""))
        if ts is None or ts < since_dt:
            continue
        per_candidate = [row for row in list(payload.get("per_candidate", [])) if isinstance(row, dict)]
        matches_symbol = any(str(row.get("symbol", "")).strip().upper() == symbol for row in per_candidate)
        matches_candidate = bool(candidate_id) and any(str(row.get("candidate_id", "")).strip() == candidate_id for row in per_candidate)
        if not matches_symbol and not matches_candidate:
            continue
        if ts > latest_dt:
            latest_dt = ts
            latest_payload = payload
            latest_dir = path.parent
    return latest_payload, latest_dir


def _scan_manual_flatten_evidence(symbol: str, since_dt: datetime) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for path in (Path("logs/risk_events_scoped_v4.jsonl"), Path("logs/risk_events.jsonl")):
        if not path.exists():
            continue
        for row in [item for item in read_jsonl_rows(str(path)) if isinstance(item, dict)]:
            if str(row.get("symbol", "")).strip().upper() != symbol:
                continue
            if str(row.get("event_type", "")).strip().upper() != "FLATTEN_CLOSE_ATTEMPTED":
                continue
            ts = _parse_dt(row.get("ts_utc", ""))
            if ts is None or ts < since_dt:
                continue
            evidence.append(
                {
                    "type": "manual_flatten_event",
                    "ts_utc": row.get("ts_utc", ""),
                    "event_id": row.get("event_id", ""),
                    "source": str(path),
                }
            )
    return evidence


def _fetch_current_state(
    *,
    env: str,
    symbol: str,
    base_url: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str]:
    resolved_base_url = _resolve_testnet_base_url(base_url) if base_url else DEFAULT_TESTNET_BASE_URL
    api_key = str(os.getenv("BINANCE_TESTNET_API_KEY", "")).strip()
    api_secret = str(os.getenv("BINANCE_TESTNET_API_SECRET", "")).strip()
    if env != "testnet":
        return {}, {}, {}, [], [], "env_not_testnet"
    if not api_key or not api_secret:
        return {}, {}, {}, [], [], "missing_testnet_api_key"

    client = BinanceFuturesTestnetClient(api_key=api_key, api_secret=api_secret, base_url=resolved_base_url)
    pos = client.get_position_risk(symbol=symbol)
    algo = client.get_open_algo_orders(symbol=symbol, algo_type="CONDITIONAL")
    if (not bool(pos.get("ok", False))) or (not bool(algo.get("ok", False))):
        return pos, algo, {}, [], [], "state_query_failed"

    protection = _build_protection_state(symbol=symbol, position_response=pos, open_algo_response=algo)
    open_rows = [row for row in _normalize_algo_rows(algo.get("response", {})) if _normalize_algo_status(row) == "NEW"]
    all_orders_resp = client.get_all_orders(symbol=symbol, limit=200)
    all_orders = [row for row in list(all_orders_resp.get("response", [])) if isinstance(row, dict)] if bool(all_orders_resp.get("ok", False)) else []
    return pos, algo, protection, open_rows, all_orders, ""


def _load_state_json_override(path: str, symbol: str) -> dict[str, Any]:
    if not path:
        return {}
    payload = _load_json(Path(path))
    if not payload:
        return {}
    if "per_symbol_state" in payload:
        return _extract_symbol_state_from_snapshot(payload, symbol)
    return payload


def _find_snapshot_states(symbol: str, since_dt: datetime) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path("logs/testnet_state_snapshots")
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    if not root.exists():
        return before, after
    rows: list[dict[str, Any]] = []
    for path in root.glob("*/state.json"):
        payload = _load_json(path)
        ts = _parse_dt(payload.get("ts_utc", ""))
        if ts is None or ts < since_dt:
            continue
        row = _extract_symbol_state_from_snapshot(payload, symbol)
        if row:
            row["snapshot_path"] = str(path)
            rows.append(row)
    rows.sort(key=lambda item: _parse_dt(item.get("ts_utc", "")) or datetime.min.replace(tzinfo=timezone.utc))
    for row in rows:
        amt = abs(_to_float(row.get("positionAmt", 0.0), 0.0))
        status = str(row.get("protection_status", "")).strip().upper()
        if amt > 0 and status == "FULLY_PROTECTED":
            before = row
        if amt <= 0 and status in {"FLAT_CLEAN", "ORPHAN_PROTECTION"}:
            after = row
    return before, after


def _infer_outcome(
    *,
    current_state: dict[str, Any],
    open_algo_rows: list[dict[str, Any]],
    all_orders: list[dict[str, Any]],
    manual_flatten_evidence: list[dict[str, Any]],
    before_state: dict[str, Any],
    tp_trigger: float,
    sl_trigger: float,
) -> tuple[str, list[str], float, str]:
    evidence: list[str] = []
    exit_price = 0.0
    exit_time = ""
    position_amt = _to_float(current_state.get("positionAmt", current_state.get("position_amt", 0.0)), 0.0)
    protection_status = str(current_state.get("protection_status", "")).strip().upper()
    open_count = int(current_state.get("openAlgoOrdersCount", len(open_algo_rows)) or 0)

    if abs(position_amt) > 0 and protection_status == "FULLY_PROTECTED":
        evidence.append("position_open_and_fully_protected")
        return "STILL_OPEN", evidence, 0.0, ""

    reduce_filled = []
    for row in all_orders:
        status = str(row.get("status", "")).strip().upper()
        if status not in {"FILLED", "PARTIALLY_FILLED"}:
            continue
        reduce_only = str(row.get("reduceOnly", "")).strip().lower() in {"true", "1"}
        if not reduce_only:
            continue
        reduce_filled.append(row)

    reduce_filled.sort(key=lambda row: _to_ts_ms(row.get("updateTime", row.get("time", 0))), reverse=True)
    if reduce_filled:
        top = reduce_filled[0]
        order_type = str(top.get("origType", top.get("type", ""))).strip().upper()
        exit_price = _to_float(top.get("avgPrice", top.get("price", 0.0)), 0.0)
        ts_ms = _to_ts_ms(top.get("updateTime", top.get("time", 0)))
        if ts_ms > 0:
            exit_time = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
        evidence.append(f"filled_reduce_order_type={order_type}")
        if order_type == "TAKE_PROFIT_MARKET":
            return "TAKE_PROFIT_TRIGGERED", evidence, exit_price, exit_time
        if order_type == "STOP_MARKET":
            return "STOP_LOSS_TRIGGERED", evidence, exit_price, exit_time

    if manual_flatten_evidence:
        evidence.append("flatten_close_attempted_event_detected")
        return "MANUAL_FLATTENED", evidence, exit_price, exit_time

    if abs(position_amt) <= 0 and open_count > 0:
        evidence.append("position_flat_but_open_algo_orders_present")
        return "UNKNOWN", evidence, exit_price, exit_time

    before_amt = _to_float(before_state.get("positionAmt", before_state.get("position_amt", 0.0)), 0.0)
    if abs(position_amt) <= 0 and abs(before_amt) > 0:
        mark = _to_float(before_state.get("markPrice", 0.0), 0.0)
        if mark > 0 and tp_trigger > 0 and sl_trigger > 0:
            if abs(mark - tp_trigger) < abs(mark - sl_trigger):
                evidence.append("inferred_by_mark_near_tp")
                return "TAKE_PROFIT_TRIGGERED", evidence, exit_price, exit_time
            evidence.append("inferred_by_mark_near_sl")
            return "STOP_LOSS_TRIGGERED", evidence, exit_price, exit_time
        evidence.append("was_fully_protected_then_flat_without_direct_trigger_evidence")
        return "EXTERNAL_CLOSED", evidence, exit_price, exit_time

    return "UNKNOWN", evidence, exit_price, exit_time


def _write_md(path: Path, report: dict[str, Any]) -> None:
    helper_summary = summarize_protection_trigger_outcomes([report])
    rendered = render_protection_monitor_markdown(helper_summary, title="Protection Trigger Outcome Review")
    lines = rendered.splitlines()
    lines.extend(
        [
            "",
            "## Core Fields",
            f"- candidate_id: {report.get('candidate_id', '')}",
            f"- exchange_order_id: {report.get('exchange_order_id', '')}",
            f"- entry_price: {report.get('entry_price', 0)}",
            f"- exit_price: {report.get('exit_price', 0)}",
            f"- entry_time: {report.get('entry_time', '')}",
            f"- exit_time: {report.get('exit_time', '')}",
            f"- position_qty: {report.get('position_qty', 0)}",
            f"- stop_loss_trigger_price: {report.get('stop_loss_trigger_price', 0)}",
            f"- take_profit_trigger_price: {report.get('take_profit_trigger_price', 0)}",
            f"- final_position_status: {report.get('final_position_status', '')}",
            "",
            "## Evidence",
        ]
    )
    for item in list(report.get("evidence", [])):
        lines.append(f"- {item}")
    lines.extend(["", "## Recommended Actions"])
    for item in list(report.get("recommended_actions", [])):
        lines.append(f"- {item}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def review_protection_trigger_outcome(
    *,
    env: str = "testnet",
    symbol: str = "OPUSDT",
    candidate_id: str = "",
    approved_run_dir: str = "logs/approved_candidate_runs",
    state_before_json: str = "",
    state_after_json: str = "",
    lookback_hours: int = 24,
    output_md: str = "logs/protection_trigger_review_OPUSDT.md",
    base_url: str = "",
) -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    target_symbol = str(symbol or "").strip().upper()
    now = datetime.now(timezone.utc)
    since_dt = now - timedelta(hours=max(1, int(lookback_hours)))

    current_pos, current_algo, protection, open_algo_rows, all_orders, state_error = _fetch_current_state(
        env=resolved_env,
        symbol=target_symbol,
        base_url=base_url,
    )

    before_override = _load_state_json_override(state_before_json, target_symbol)
    after_override = _load_state_json_override(state_after_json, target_symbol)
    snap_before, snap_after = _find_snapshot_states(target_symbol, since_dt)
    before_state = before_override or snap_before

    if after_override:
        final_state = after_override
    elif protection:
        final_state = {
            "symbol": target_symbol,
            "positionAmt": _to_float(protection.get("position_amt", 0.0), 0.0),
            "entryPrice": _to_float(protection.get("entry_price", 0.0), 0.0),
            "markPrice": _to_float(protection.get("mark_price", 0.0), 0.0),
            "openAlgoOrdersCount": len(open_algo_rows),
            "protection_status": str(protection.get("protection_status", "UNKNOWN")),
            "action_required": str(protection.get("action_required", "")),
        }
    else:
        final_state = snap_after or {}

    run_summary, run_dir = _latest_matching_run(
        approved_runs_root=Path(approved_run_dir),
        symbol=target_symbol,
        candidate_id=str(candidate_id or "").strip(),
        since_dt=since_dt,
    )
    batch_row: dict[str, Any] = {}
    if run_dir is not None:
        submit_file = run_dir / "batch" / f"{target_symbol}_submit.jsonl"
        if submit_file.exists():
            rows = [row for row in read_jsonl_rows(str(submit_file)) if isinstance(row, dict)]
            if rows:
                batch_row = rows[-1]

    manual_flatten_evidence = _scan_manual_flatten_evidence(target_symbol, since_dt)
    sl_trigger = _to_float(batch_row.get("stop_loss_plan", {}).get("price", 0.0), 0.0) if isinstance(batch_row.get("stop_loss_plan", {}), dict) else 0.0
    tp_trigger = _to_float(batch_row.get("take_profit_plan", {}).get("price", 0.0), 0.0) if isinstance(batch_row.get("take_profit_plan", {}), dict) else 0.0
    if sl_trigger <= 0:
        sl_trigger = _extract_algo_trigger(open_algo_rows, "STOP_MARKET")
    if tp_trigger <= 0:
        tp_trigger = _extract_algo_trigger(open_algo_rows, "TAKE_PROFIT_MARKET")

    outcome, evidence_list, exit_price, exit_time = _infer_outcome(
        current_state=final_state,
        open_algo_rows=open_algo_rows,
        all_orders=all_orders,
        manual_flatten_evidence=manual_flatten_evidence,
        before_state=before_state,
        tp_trigger=tp_trigger,
        sl_trigger=sl_trigger,
    )
    orphan_after_close = bool(
        _to_float(final_state.get("positionAmt", 0.0), 0.0) == 0
        and int(final_state.get("openAlgoOrdersCount", 0) or 0) > 0
    )
    final_position_status = str(final_state.get("protection_status", "UNKNOWN")).strip().upper()
    entry_price = _to_float(batch_row.get("entry_payload", {}).get("price", 0.0), 0.0) if isinstance(batch_row.get("entry_payload", {}), dict) else 0.0
    if entry_price <= 0:
        entry_price = _to_float(before_state.get("entryPrice", before_state.get("entry_price", 0.0)), 0.0)
    position_qty = abs(_to_float(before_state.get("positionAmt", before_state.get("position_amt", batch_row.get("quantity", 0.0))), 0.0))
    if position_qty <= 0:
        position_qty = abs(_to_float(batch_row.get("quantity", 0.0), 0.0))
    pnl_estimate = 0.0
    pnl_pct = 0.0
    if exit_price > 0 and entry_price > 0 and position_qty > 0:
        pnl_estimate = (exit_price - entry_price) * position_qty
        pnl_pct = (exit_price - entry_price) / entry_price * 100.0

    evidence = []
    evidence.extend(evidence_list)
    if run_summary:
        evidence.append(f"matched_run_id={run_summary.get('run_id', '')}")
    if batch_row:
        evidence.append("batch_submit_row_found")
    if manual_flatten_evidence:
        evidence.append("manual_flatten_events_found")
    if state_error:
        evidence.append(f"state_error={state_error}")

    verdict = "PASS"
    verdict_reason = "protected_state_or_clean_close_detected"
    if final_position_status in {"NAKED_POSITION", "PARTIAL_PROTECTED"}:
        verdict = "FAIL"
        verdict_reason = "position_not_fully_protected"
    elif outcome in {"UNKNOWN"} or orphan_after_close:
        verdict = "PARTIAL"
        verdict_reason = "close_outcome_uncertain_or_orphan_detected"
    elif state_error:
        verdict = "PARTIAL"
        verdict_reason = state_error

    recommended_actions: list[str] = []
    if verdict == "PASS" and outcome == "STILL_OPEN":
        recommended_actions.append("keep_monitoring_position_protection_distance")
    if orphan_after_close:
        recommended_actions.append(
            f"PYTHONPATH=. ./.venv/bin/python scripts/safe_flatten_testnet_symbol.py --env testnet --symbol {target_symbol} --cancel-protective-orders --dry-run --json"
        )
    if verdict == "PARTIAL" and outcome == "UNKNOWN":
        recommended_actions.append("review_order_history_and_algo_history_manually")
    if verdict == "FAIL":
        recommended_actions.append("stop_new_actions_and_repair_protection_or_flatten")

    monitor_state = classify_protection_trigger_outcome(
        {
            "outcome": outcome,
            "verdict": verdict,
            "orphan_after_close": orphan_after_close,
        }
    )
    helper_summary = summarize_protection_trigger_outcomes(
        [
            {
                "symbol": target_symbol,
                "outcome": outcome,
                "verdict": verdict,
                "orphan_after_close": orphan_after_close,
            }
        ]
    )

    report = {
        "ok": verdict != "FAIL",
        "ts_utc": now.isoformat(),
        "env": resolved_env,
        "symbol": target_symbol,
        "candidate_id": str(candidate_id or "") or str(batch_row.get("candidate_id", "")),
        "exchange_order_id": str(batch_row.get("exchange_order_id", "")),
        "entry_price": entry_price,
        "exit_price": exit_price,
        "entry_time": str(run_summary.get("started_at_utc", "")),
        "exit_time": exit_time,
        "position_qty": position_qty,
        "stop_loss_trigger_price": sl_trigger,
        "take_profit_trigger_price": tp_trigger,
        "final_position_status": final_position_status,
        "outcome": outcome,
        "monitor_state": monitor_state,
        "aggregate_status": str(helper_summary.get("aggregate_status", "")),
        "orphan_after_close": orphan_after_close,
        "pnl_estimate_usdt": round(pnl_estimate, 8),
        "pnl_pct_estimate": round(pnl_pct, 8),
        "evidence": evidence,
        "recommended_actions": recommended_actions,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "before_state": before_state,
        "after_state": final_state,
        "approved_run_id": str(run_summary.get("run_id", "")),
        "approved_run_dir": str(run_dir) if run_dir is not None else "",
        "output_md": output_md,
    }
    _write_md(Path(output_md), report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review protection trigger outcome for one testnet symbol (read-only)")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--symbol", default="OPUSDT")
    parser.add_argument("--candidate-id", default="")
    parser.add_argument("--approved-run-dir", default="logs/approved_candidate_runs")
    parser.add_argument("--state-before-json", default="")
    parser.add_argument("--state-after-json", default="")
    parser.add_argument("--lookback-hours", type=int, default=24)
    parser.add_argument("--output-md", default="logs/protection_trigger_review_OPUSDT.md")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    report = review_protection_trigger_outcome(
        env=str(args.env or "testnet"),
        symbol=str(args.symbol or "OPUSDT"),
        candidate_id=str(args.candidate_id or ""),
        approved_run_dir=str(args.approved_run_dir or "logs/approved_candidate_runs"),
        state_before_json=str(args.state_before_json or ""),
        state_after_json=str(args.state_after_json or ""),
        lookback_hours=int(args.lookback_hours or 24),
        output_md=str(args.output_md or "logs/protection_trigger_review_OPUSDT.md"),
        base_url=str(args.base_url or ""),
    )
    if bool(args.json):
        print(json.dumps(report, ensure_ascii=False))
        return
    print(f"outcome={report.get('outcome', '')}")
    print(f"verdict={report.get('verdict', '')}")
    print(f"output_md={report.get('output_md', '')}")


if __name__ == "__main__":
    main()
