from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.trade_logger import read_jsonl_rows


FIELDNAMES = [
    "trade_id",
    "candidate_id",
    "symbol",
    "side",
    "quantity",
    "entry_type",
    "entry_order_id",
    "entry_status",
    "entry_price",
    "entry_time",
    "sl_order_id",
    "tp_order_id",
    "sl_price",
    "tp_price",
    "protective_order_success",
    "exit_type",
    "exit_order_id",
    "exit_price",
    "exit_time",
    "outcome",
    "pnl_estimate_usdt",
    "pnl_pct_estimate",
    "risk_per_unit",
    "reward_per_unit",
    "risk_reward_ratio",
    "initial_risk_usdt",
    "realized_r_multiple",
    "planned_tp_r_multiple",
    "stop_distance_pct",
    "take_profit_distance_pct",
    "exit_efficiency_pct",
    "orphan_ever_detected",
    "orphan_after_close",
    "orphan_cleanup_done",
    "lifecycle_status",
    "execution_verdict",
    "source_reports",
]


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


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_float_nan(value: Any) -> float:
    if value is None:
        return float("nan")
    text = str(value).strip()
    if not text:
        return float("nan")
    try:
        return float(text)
    except (TypeError, ValueError):
        return float("nan")


def _valid_positive(value: float) -> bool:
    return math.isfinite(value) and value > 0


def _nan_if_invalid(value: float) -> float:
    if math.isfinite(value):
        return value
    return float("nan")


def _enrich_risk_metrics(row: dict[str, Any]) -> dict[str, Any]:
    entry_price = _to_float_nan(row.get("entry_price"))
    sl_price = _to_float_nan(row.get("sl_price"))
    tp_price = _to_float_nan(row.get("tp_price"))
    exit_price = _to_float_nan(row.get("exit_price"))
    quantity = abs(_to_float_nan(row.get("quantity")))
    pnl_estimate = _to_float_nan(row.get("pnl_estimate_usdt"))
    outcome = str(row.get("outcome", "")).strip().upper()

    risk_per_unit = float("nan")
    if _valid_positive(entry_price) and _valid_positive(sl_price):
        risk_per_unit = abs(entry_price - sl_price)

    reward_per_unit = float("nan")
    if _valid_positive(entry_price) and _valid_positive(tp_price):
        reward_per_unit = abs(tp_price - entry_price)

    risk_reward_ratio = float("nan")
    if _valid_positive(risk_per_unit):
        risk_reward_ratio = reward_per_unit / risk_per_unit

    initial_risk_usdt = float("nan")
    if _valid_positive(risk_per_unit) and _valid_positive(quantity):
        initial_risk_usdt = risk_per_unit * quantity

    realized_r_multiple = float("nan")
    if math.isfinite(pnl_estimate) and _valid_positive(initial_risk_usdt):
        realized_r_multiple = pnl_estimate / initial_risk_usdt

    planned_tp_r_multiple = float("nan")
    if _valid_positive(risk_per_unit):
        planned_tp_r_multiple = reward_per_unit / risk_per_unit

    stop_distance_pct = float("nan")
    if _valid_positive(entry_price) and _valid_positive(sl_price):
        stop_distance_pct = abs(entry_price - sl_price) / entry_price * 100.0

    take_profit_distance_pct = float("nan")
    if _valid_positive(entry_price) and _valid_positive(tp_price):
        take_profit_distance_pct = abs(tp_price - entry_price) / entry_price * 100.0

    exit_efficiency_pct = float("nan")
    if _valid_positive(exit_price) and _valid_positive(entry_price):
        if outcome == "TAKE_PROFIT_TRIGGERED" and _valid_positive(tp_price):
            target_move = abs(tp_price - entry_price)
            if target_move > 0:
                exit_efficiency_pct = abs(exit_price - entry_price) / target_move * 100.0
        elif outcome == "STOP_LOSS_TRIGGERED" and _valid_positive(sl_price):
            risk_move = abs(entry_price - sl_price)
            if risk_move > 0:
                exit_efficiency_pct = -abs(exit_price - entry_price) / risk_move * 100.0

    row["risk_per_unit"] = _nan_if_invalid(risk_per_unit)
    row["reward_per_unit"] = _nan_if_invalid(reward_per_unit)
    row["risk_reward_ratio"] = _nan_if_invalid(risk_reward_ratio)
    row["initial_risk_usdt"] = _nan_if_invalid(initial_risk_usdt)
    row["realized_r_multiple"] = _nan_if_invalid(realized_r_multiple)
    row["planned_tp_r_multiple"] = _nan_if_invalid(planned_tp_r_multiple)
    row["stop_distance_pct"] = _nan_if_invalid(stop_distance_pct)
    row["take_profit_distance_pct"] = _nan_if_invalid(take_profit_distance_pct)
    row["exit_efficiency_pct"] = _nan_if_invalid(exit_efficiency_pct)
    return row


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_trigger_review_md(path: Path) -> dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    values: dict[str, str] = {}
    for line in lines:
        text = line.strip()
        if not text.startswith("- "):
            continue
        body = text[2:]
        if ":" not in body:
            continue
        key, raw = body.split(":", 1)
        values[key.strip()] = raw.strip()
    if "outcome" not in values:
        return {}
    return {
        "candidate_id": values.get("candidate_id", ""),
        "symbol": values.get("symbol", ""),
        "exchange_order_id": values.get("exchange_order_id", ""),
        "entry_price": _to_float(values.get("entry_price", 0.0), 0.0),
        "exit_price": _to_float(values.get("exit_price", 0.0), 0.0),
        "entry_time": values.get("entry_time", ""),
        "exit_time": values.get("exit_time", ""),
        "position_qty": _to_float(values.get("position_qty", 0.0), 0.0),
        "outcome": values.get("outcome", ""),
        "orphan_after_close": str(values.get("orphan_after_close", "")).strip().lower() == "true",
        "pnl_estimate_usdt": _to_float(values.get("pnl_estimate_usdt", 0.0), 0.0),
        "pnl_pct_estimate": _to_float(values.get("pnl_pct_estimate", 0.0), 0.0),
    }


def _load_trigger_reviews(logs_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in logs_dir.glob("protection_trigger_review_*.json"):
        payload = _load_json(path)
        if payload:
            payload["__source_path"] = str(path)
            rows.append(payload)
    for path in logs_dir.glob("protection_trigger_review_*.md"):
        payload = _parse_trigger_review_md(path)
        if payload:
            payload["__source_path"] = str(path)
            rows.append(payload)
    return rows


def _orphan_event_map(logs_dir: Path) -> dict[str, dict[str, bool]]:
    result: dict[str, dict[str, bool]] = {}
    for path in (logs_dir / "risk_events_scoped_v4.jsonl", logs_dir / "risk_events.jsonl"):
        if not path.exists():
            continue
        for row in [item for item in read_jsonl_rows(str(path)) if isinstance(item, dict)]:
            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            bucket = result.setdefault(symbol, {"orphan_ever_detected": False, "orphan_cleanup_done": False})
            event_type = str(row.get("event_type", "")).strip().upper()
            if event_type in {"ORPHAN_PROTECTION_DETECTED", "CANDIDATE_SKIPPED_BY_PREFLIGHT"} and "ORPHAN" in json.dumps(row, ensure_ascii=False).upper():
                bucket["orphan_ever_detected"] = True
            if event_type in {"FLATTEN_CANCEL_ATTEMPTED", "FLATTEN_DRY_RUN_ONLY"}:
                bucket["orphan_cleanup_done"] = True
    return result


def _build_trade_rows(logs_dir: Path) -> list[dict[str, Any]]:
    trigger_rows = _load_trigger_reviews(logs_dir)
    orphan_map = _orphan_event_map(logs_dir)

    trades: list[dict[str, Any]] = []
    for summary_path in (logs_dir / "approved_candidate_runs").glob("*/summary.json"):
        summary = _load_json(summary_path)
        if not summary:
            continue
        snapshot = _load_json(summary_path.parent / "candidate_snapshot.json")
        candidates = [row for row in list(snapshot.get("candidates", [])) if isinstance(row, dict)]
        if not candidates:
            continue
        for cand in candidates:
            status = str(cand.get("status", "")).strip().upper()
            if status != "SUBMITTED":
                continue
            candidate_id = str(cand.get("candidate_id", "")).strip()
            symbol = str(cand.get("symbol", "")).strip().upper()
            exchange_order_id = str(cand.get("exchange_order_id", ""))
            trigger = {}
            for row in trigger_rows:
                row_cid = str(row.get("candidate_id", "")).strip()
                row_symbol = str(row.get("symbol", "")).strip().upper()
                row_oid = str(row.get("exchange_order_id", ""))
                if row_cid and row_cid == candidate_id:
                    trigger = row
                    break
                if row_oid and exchange_order_id and row_oid == exchange_order_id:
                    trigger = row
                    break
                if row_symbol and row_symbol == symbol:
                    trigger = row
            entry_price = _to_float(trigger.get("entry_price", 0.0), 0.0)
            if entry_price <= 0 and isinstance(cand.get("entry_payload", {}), dict):
                entry_price = _to_float(cand.get("entry_payload", {}).get("price", 0.0), 0.0)
            exit_price = _to_float(trigger.get("exit_price", 0.0), 0.0)
            qty = abs(_to_float(cand.get("quantity", 0.0), 0.0))
            pnl_estimate = _to_float(trigger.get("pnl_estimate_usdt", 0.0), 0.0)
            pnl_pct = _to_float(trigger.get("pnl_pct_estimate", 0.0), 0.0)
            if abs(pnl_estimate) <= 0 and entry_price > 0 and exit_price > 0 and qty > 0:
                side = str(cand.get("side", "")).strip().upper()
                if side in {"SELL", "SHORT"}:
                    pnl_estimate = (entry_price - exit_price) * qty
                else:
                    pnl_estimate = (exit_price - entry_price) * qty
            if abs(pnl_pct) <= 0 and entry_price > 0 and exit_price > 0:
                side = str(cand.get("side", "")).strip().upper()
                if side in {"SELL", "SHORT"}:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100.0
                else:
                    pnl_pct = (exit_price - entry_price) / entry_price * 100.0

            outcome = str(trigger.get("outcome", "UNKNOWN")).strip().upper() or "UNKNOWN"
            if outcome == "STILL_OPEN":
                continue
            if outcome == "UNKNOWN" and not str(trigger.get("exit_time", "")).strip() and exit_price <= 0:
                continue
            orphan_after_close = bool(trigger.get("orphan_after_close", False))
            orphan_signals = orphan_map.get(symbol, {})
            orphan_ever = bool(orphan_signals.get("orphan_ever_detected", False) or orphan_after_close)
            orphan_cleanup_done = bool(orphan_signals.get("orphan_cleanup_done", False) or (orphan_ever and not orphan_after_close))

            lifecycle_status = "CLOSED"
            execution_verdict = "PASS"
            if outcome in {"UNKNOWN"}:
                execution_verdict = "PARTIAL"
            if orphan_after_close:
                execution_verdict = "PARTIAL"

            row = {
                "trade_id": f"trade_{candidate_id or exchange_order_id or symbol}",
                "candidate_id": candidate_id,
                "symbol": symbol,
                "side": str(cand.get("side", "")).strip().upper(),
                "quantity": qty,
                "entry_type": str(cand.get("order_type", "MARKET")).strip().upper(),
                "entry_order_id": exchange_order_id,
                "entry_status": "SUBMITTED",
                "entry_price": round(entry_price, 8),
                "entry_time": str(trigger.get("entry_time", "") or cand.get("submitted_at_utc", "") or summary.get("started_at_utc", "")),
                "sl_order_id": str(cand.get("stop_loss_algo_id", "")),
                "tp_order_id": str(cand.get("take_profit_algo_id", "")),
                "sl_price": _to_float(cand.get("stop_loss_plan", {}).get("price", 0.0), 0.0) if isinstance(cand.get("stop_loss_plan", {}), dict) else 0.0,
                "tp_price": _to_float(cand.get("take_profit_plan", {}).get("price", 0.0), 0.0) if isinstance(cand.get("take_profit_plan", {}), dict) else 0.0,
                "protective_order_success": bool(cand.get("protective_orders_submitted", False)),
                "exit_type": outcome,
                "exit_order_id": str(trigger.get("exit_order_id", "")),
                "exit_price": round(exit_price, 8),
                "exit_time": str(trigger.get("exit_time", "")),
                "outcome": outcome,
                "pnl_estimate_usdt": round(pnl_estimate, 8),
                "pnl_pct_estimate": round(pnl_pct, 8),
                "orphan_ever_detected": orphan_ever,
                "orphan_after_close": orphan_after_close,
                "orphan_cleanup_done": orphan_cleanup_done,
                "lifecycle_status": lifecycle_status,
                "execution_verdict": execution_verdict,
                "source_reports": json.dumps(
                    [str(summary_path), str(summary_path.parent / "candidate_snapshot.json"), str(trigger.get("__source_path", ""))],
                    ensure_ascii=False,
                ),
            }
            row = _enrich_risk_metrics(row)
            trades.append(row)
    # candidate_id de-dup: keep latest entry_time
    dedup: dict[str, dict[str, Any]] = {}
    for row in trades:
        cid = str(row.get("candidate_id", "")).strip()
        key = cid or str(row.get("trade_id", ""))
        if key not in dedup:
            dedup[key] = row
            continue
        old_dt = _parse_dt(dedup[key].get("entry_time", ""))
        new_dt = _parse_dt(row.get("entry_time", ""))
        if old_dt is None or (new_dt is not None and new_dt > old_dt):
            dedup[key] = row
    return list(dedup.values())


def generate_trade_lifecycle_csv(
    *,
    reports_dir: str = "reports",
    logs_dir: str = "logs",
) -> dict[str, Any]:
    reports_root = Path(reports_dir)
    logs_root = Path(logs_dir)
    out_dir = reports_root / "trade_lifecycle"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "trade_lifecycle.csv"
    json_path = out_dir / "trade_lifecycle.json"
    md_path = out_dir / "summary.md"

    rows = _build_trade_rows(logs_root)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in FIELDNAMES})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reports_dir": str(reports_root),
        "logs_dir": str(logs_root),
        "total_rows": len(rows),
        "closed_rows": sum(1 for row in rows if str(row.get("lifecycle_status", "")).upper() == "CLOSED"),
        "open_rows": sum(1 for row in rows if str(row.get("lifecycle_status", "")).upper() == "OPEN"),
        "pass_rows": sum(1 for row in rows if str(row.get("execution_verdict", "")).upper() == "PASS"),
        "partial_rows": sum(1 for row in rows if str(row.get("execution_verdict", "")).upper() == "PARTIAL"),
        "fail_rows": sum(1 for row in rows if str(row.get("execution_verdict", "")).upper() == "FAIL"),
        "unique_candidate_id_count": len({str(row.get("candidate_id", "")).strip() for row in rows if str(row.get("candidate_id", "")).strip()}),
        "rows": rows,
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "summary_md_path": str(md_path),
    }
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_lines = [
        "# Trade Lifecycle Summary",
        "",
        f"- total_rows: {summary['total_rows']}",
        f"- closed_rows: {summary['closed_rows']}",
        f"- pass_rows: {summary['pass_rows']}",
        "",
        f"- csv: {csv_path}",
        f"- json: {json_path}",
    ]
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate trade lifecycle CSV/JSON/MD from local artifacts")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_trade_lifecycle_csv(
        reports_dir=str(args.reports_dir or "reports"),
        logs_dir=str(args.logs_dir or "logs"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"total_rows={result.get('total_rows', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")
    print(f"json_path={result.get('json_path', '')}")


if __name__ == "__main__":
    main()
