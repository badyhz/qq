from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.binance_testnet_client import BinanceFuturesTestnetClient
from core.risk_event_logger import log_risk_event
from scripts.account_protection_report_common import classify_protection_health, summarize_protection_health
from scripts.submit_replayed_testnet_payload import (
    DEFAULT_TESTNET_BASE_URL,
    _build_protection_state,
    _normalize_algo_order_type,
    _normalize_algo_rows,
    _normalize_algo_status,
    _resolve_testnet_base_url,
    _to_float,
)


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in str(value or "").split(",") if item.strip()]


def _extract_algo_qty(row: dict[str, Any]) -> float:
    for key in ("quantity", "qty", "origQty", "executedQty"):
        qty = _to_float(row.get(key, 0.0), 0.0)
        if qty > 0:
            return qty
    return 0.0


def _extract_trigger_price(row: dict[str, Any]) -> float:
    for key in ("triggerPrice", "stopPrice", "activatePrice"):
        price = _to_float(row.get(key, 0.0), 0.0)
        if price > 0:
            return price
    return 0.0


def _algo_side(row: dict[str, Any]) -> str:
    for key in ("side", "orderSide", "positionSide"):
        value = str(row.get(key, "")).strip().upper()
        if value:
            return value
    return ""


def _is_reduce_only(row: dict[str, Any]) -> bool:
    for key in ("reduceOnly", "closePosition"):
        value = row.get(key)
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"true", "1", "yes"}:
            return True
    return False


def _is_trigger_direction_valid(position_amt: float, mark_price: float, sl_price: float, tp_price: float) -> bool:
    if abs(position_amt) <= 0 or mark_price <= 0:
        return True
    if position_amt > 0:
        if sl_price > 0 and not (sl_price < mark_price):
            return False
        if tp_price > 0 and not (tp_price > mark_price):
            return False
    else:
        if sl_price > 0 and not (sl_price > mark_price):
            return False
        if tp_price > 0 and not (tp_price < mark_price):
            return False
    return True


def _check_symbol_health(
    *,
    symbol: str,
    position_response: dict[str, Any],
    open_algo_response: dict[str, Any],
) -> dict[str, Any]:
    protection_state = _build_protection_state(
        symbol=symbol,
        position_response=position_response,
        open_algo_response=open_algo_response,
    )
    algo_rows = _normalize_algo_rows(open_algo_response.get("response", {}))
    open_rows = [row for row in algo_rows if _normalize_algo_status(row) == "NEW"]
    sl_rows = [row for row in open_rows if _normalize_algo_order_type(row) == "STOP_MARKET"]
    tp_rows = [row for row in open_rows if _normalize_algo_order_type(row) == "TAKE_PROFIT_MARKET"]

    position_amt = _to_float(protection_state.get("position_amt", 0.0), 0.0)
    abs_position = abs(position_amt)
    entry_price = _to_float(protection_state.get("entry_price", 0.0), 0.0)
    mark_price = _to_float(protection_state.get("mark_price", 0.0), 0.0)
    has_position = abs_position > 0

    unrealized_profit = 0.0
    position_rows = position_response.get("response", [])
    if isinstance(position_rows, list):
        for row in position_rows:
            if str(row.get("symbol", "")).strip().upper() != symbol:
                continue
            unrealized_profit = _to_float(row.get("unRealizedProfit", row.get("unrealizedProfit", 0.0)), 0.0)
            break

    sl_qty = sum(_extract_algo_qty(row) for row in sl_rows)
    tp_qty = sum(_extract_algo_qty(row) for row in tp_rows)
    sl_trigger = _extract_trigger_price(sl_rows[0]) if sl_rows else 0.0
    tp_trigger = _extract_trigger_price(tp_rows[0]) if tp_rows else 0.0
    sl_reduce_only = all(_is_reduce_only(row) for row in sl_rows) if sl_rows else False
    tp_reduce_only = all(_is_reduce_only(row) for row in tp_rows) if tp_rows else False
    expected_side = "SELL" if position_amt > 0 else "BUY"
    sl_side_ok = all(_algo_side(row) == expected_side for row in sl_rows) if sl_rows else False
    tp_side_ok = all(_algo_side(row) == expected_side for row in tp_rows) if tp_rows else False
    trigger_ok = _is_trigger_direction_valid(position_amt, mark_price, sl_trigger, tp_trigger)

    health = "UNKNOWN"
    health_reason = "unknown"
    severity = "INFO"
    if not has_position and not open_rows:
        health = "NO_POSITION"
        health_reason = "flat_clean"
    elif not has_position and open_rows:
        health = "ORPHAN_PROTECTION"
        health_reason = "no_position_with_open_algo_orders"
        severity = "WARNING"
    else:
        has_sl = len(sl_rows) > 0
        has_tp = len(tp_rows) > 0
        if not has_sl and has_tp:
            health = "MISSING_STOP_LOSS"
            health_reason = "missing_stop_loss_order"
            severity = "ERROR"
        elif has_sl and not has_tp:
            health = "MISSING_TAKE_PROFIT"
            health_reason = "missing_take_profit_order"
            severity = "ERROR"
        elif not has_sl and not has_tp:
            health = "PARTIAL_PROTECTION"
            health_reason = "no_protective_orders"
            severity = "CRITICAL"
        elif (not sl_reduce_only) or (not tp_reduce_only) or (not sl_side_ok) or (not tp_side_ok):
            health = "PARTIAL_PROTECTION"
            health_reason = "reduce_only_or_side_mismatch"
            severity = "ERROR"
        elif sl_qty + 1e-9 < abs_position or tp_qty + 1e-9 < abs_position:
            health = "PARTIAL_PROTECTION"
            health_reason = "protective_quantity_insufficient"
            severity = "ERROR"
        elif not trigger_ok:
            health = "INVALID_TRIGGER_DIRECTION"
            health_reason = "trigger_price_direction_invalid"
            severity = "CRITICAL"
        else:
            health = "HEALTHY"
            health_reason = "full_protection_verified"
            severity = "INFO"

    return {
        "symbol": symbol,
        "positionAmt": position_amt,
        "entryPrice": entry_price,
        "markPrice": mark_price,
        "unrealizedProfit": unrealized_profit,
        "openAlgoOrdersCount": len(open_rows),
        "open_stop_market_count": len(sl_rows),
        "open_take_profit_market_count": len(tp_rows),
        "stop_loss_trigger_price": sl_trigger,
        "take_profit_trigger_price": tp_trigger,
        "stop_loss_reduce_only_ok": bool(sl_reduce_only) if sl_rows else False,
        "take_profit_reduce_only_ok": bool(tp_reduce_only) if tp_rows else False,
        "stop_loss_side_ok": bool(sl_side_ok) if sl_rows else False,
        "take_profit_side_ok": bool(tp_side_ok) if tp_rows else False,
        "stop_loss_qty": sl_qty,
        "take_profit_qty": tp_qty,
        "protection_status": str(protection_state.get("protection_status", "UNKNOWN")),
        "action_required": str(protection_state.get("action_required", "")),
        "protection_health": health,
        "health_reason": health_reason,
        "severity": severity,
    }


def _aggregate_health(rows: list[dict[str, Any]]) -> tuple[str, str]:
    summary = summarize_protection_health(rows)
    result = classify_protection_health(summary)
    return str(result.get("aggregate_health", "PASS")), str(result.get("aggregate_reason", "all_positions_healthy_or_flat"))


def _write_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Protection Health Report",
        "",
        f"- ts_utc: {summary.get('ts_utc', '')}",
        f"- env: {summary.get('env', '')}",
        f"- symbols: {','.join(list(summary.get('symbols', [])))}",
        f"- aggregate_health: {summary.get('aggregate_health', '')}",
        f"- aggregate_reason: {summary.get('aggregate_reason', '')}",
        "",
        "| symbol | positionAmt | markPrice | openAlgoOrders | protection_status | protection_health | reason |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for row in list(summary.get("per_symbol", [])):
        lines.append(
            f"| {row.get('symbol', '')} | {row.get('positionAmt', 0)} | {row.get('markPrice', 0)} | {row.get('openAlgoOrdersCount', 0)} | "
            f"{row.get('protection_status', '')} | {row.get('protection_health', '')} | {row.get('health_reason', '')} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_protection_health(
    *,
    env: str = "testnet",
    symbols: str = "FETUSDT,OPUSDT",
    output_md: str = "logs/protection_health_report.md",
    base_url: str = "",
    log_risk_events: bool = False,
    risk_events_jsonl: str = "logs/risk_events.jsonl",
) -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    symbol_list = _parse_symbols(symbols)
    resolved_base_url = _resolve_testnet_base_url(base_url) if base_url else DEFAULT_TESTNET_BASE_URL
    ts_utc = datetime.now(timezone.utc).isoformat()

    if resolved_env != "testnet":
        summary = {
            "ok": False,
            "ts_utc": ts_utc,
            "env": resolved_env,
            "symbols": symbol_list,
            "aggregate_health": "FAIL",
            "aggregate_reason": "env_not_testnet",
            "per_symbol": [],
            "error_code": "env_not_testnet",
        }
        _write_md(Path(output_md), summary)
        return summary

    api_key = str(os.getenv("BINANCE_TESTNET_API_KEY", "")).strip()
    api_secret = str(os.getenv("BINANCE_TESTNET_API_SECRET", "")).strip()
    if not api_key or not api_secret:
        per_symbol = [
            {
                "symbol": symbol,
                "positionAmt": 0.0,
                "entryPrice": 0.0,
                "markPrice": 0.0,
                "unrealizedProfit": 0.0,
                "openAlgoOrdersCount": 0,
                "open_stop_market_count": 0,
                "open_take_profit_market_count": 0,
                "stop_loss_trigger_price": 0.0,
                "take_profit_trigger_price": 0.0,
                "protection_status": "UNKNOWN",
                "action_required": "missing_testnet_api_key",
                "protection_health": "UNKNOWN",
                "health_reason": "missing_testnet_api_key",
                "severity": "WARNING",
            }
            for symbol in symbol_list
        ]
        summary = {
            "ok": False,
            "ts_utc": ts_utc,
            "env": resolved_env,
            "symbols": symbol_list,
            "aggregate_health": "PARTIAL",
            "aggregate_reason": "missing_testnet_api_key",
            "per_symbol": per_symbol,
            "error_code": "missing_testnet_api_key",
        }
        _write_md(Path(output_md), summary)
        return summary

    client = BinanceFuturesTestnetClient(api_key=api_key, api_secret=api_secret, base_url=resolved_base_url)
    per_symbol: list[dict[str, Any]] = []
    for symbol in symbol_list:
        pos_resp = client.get_position_risk(symbol=symbol)
        algo_resp = client.get_open_algo_orders(symbol=symbol, algo_type="CONDITIONAL")
        if (not bool(pos_resp.get("ok", False))) or (not bool(algo_resp.get("ok", False))):
            per_symbol.append(
                {
                    "symbol": symbol,
                    "positionAmt": 0.0,
                    "entryPrice": 0.0,
                    "markPrice": 0.0,
                    "unrealizedProfit": 0.0,
                    "openAlgoOrdersCount": 0,
                    "open_stop_market_count": 0,
                    "open_take_profit_market_count": 0,
                    "stop_loss_trigger_price": 0.0,
                    "take_profit_trigger_price": 0.0,
                    "protection_status": "UNKNOWN",
                    "action_required": "state_query_failed",
                    "protection_health": "UNKNOWN",
                    "health_reason": str(pos_resp.get("error_message", "") or algo_resp.get("error_message", "") or "state_query_failed"),
                    "severity": "WARNING",
                }
            )
            continue
        per_symbol.append(_check_symbol_health(symbol=symbol, position_response=pos_resp, open_algo_response=algo_resp))

    aggregate_health, aggregate_reason = _aggregate_health(per_symbol)
    summary = {
        "ok": aggregate_health != "FAIL",
        "ts_utc": ts_utc,
        "env": resolved_env,
        "base_url": resolved_base_url,
        "symbols": symbol_list,
        "aggregate_health": aggregate_health,
        "aggregate_reason": aggregate_reason,
        "per_symbol": per_symbol,
        "output_md": output_md,
    }
    _write_md(Path(output_md), summary)

    if log_risk_events:
        event_type = "PROTECTION_HEALTH_CHECKED"
        severity = "INFO"
        if aggregate_health == "PARTIAL":
            event_type = "PROTECTION_HEALTH_WARNING"
            severity = "WARNING"
        elif aggregate_health == "FAIL":
            event_type = "PROTECTION_HEALTH_FAILED"
            severity = "CRITICAL"
        log_risk_event(
            env=resolved_env,
            symbol="",
            component="check_protection_health",
            event_type=event_type,
            severity=severity,
            message="protection health check completed",
            context={"aggregate_health": aggregate_health, "aggregate_reason": aggregate_reason},
            action_required="review_protection_health_report",
            event_scope="PRODUCTION_LIKE",
            is_test_event=False,
            output_path=risk_events_jsonl,
        )
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only protection health checker for testnet symbols")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--symbols", default="FETUSDT,OPUSDT")
    parser.add_argument("--output-md", default="logs/protection_health_report.md")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--log-risk-events", default="false")
    parser.add_argument("--risk-events-jsonl", default="logs/risk_events.jsonl")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = check_protection_health(
        env=str(args.env or "testnet"),
        symbols=str(args.symbols or "FETUSDT,OPUSDT"),
        output_md=str(args.output_md or "logs/protection_health_report.md"),
        base_url=str(args.base_url or ""),
        log_risk_events=_to_bool(args.log_risk_events, default=False),
        risk_events_jsonl=str(args.risk_events_jsonl or "logs/risk_events.jsonl"),
    )
    if bool(args.json):
        print(json.dumps(summary, ensure_ascii=False))
        return
    print(f"aggregate_health={summary.get('aggregate_health', '')}")
    print(f"aggregate_reason={summary.get('aggregate_reason', '')}")
    print(f"output_md={summary.get('output_md', '')}")


if __name__ == "__main__":
    main()
