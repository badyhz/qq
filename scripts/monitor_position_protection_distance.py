from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.binance_testnet_client import BinanceFuturesTestnetClient
from scripts.protection_monitor_report_common import (
    classify_protection_distance_state,
    summarize_protection_distance,
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


def _parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in str(value or "").split(",") if item.strip()]


def _safe_pct(numerator: float, denominator: float) -> float:
    if abs(denominator) <= 0:
        return 0.0
    return numerator / denominator * 100.0


def _extract_trigger(rows: list[dict[str, Any]], order_type: str) -> float:
    for row in rows:
        if _normalize_algo_order_type(row) != order_type:
            continue
        for key in ("triggerPrice", "stopPrice", "activatePrice"):
            price = _to_float(row.get(key, 0.0), 0.0)
            if price > 0:
                return price
    return 0.0


def _extract_qty(rows: list[dict[str, Any]], order_type: str) -> float:
    qty = 0.0
    for row in rows:
        if _normalize_algo_order_type(row) != order_type:
            continue
        for key in ("quantity", "qty", "origQty", "executedQty"):
            q = _to_float(row.get(key, 0.0), 0.0)
            if q > 0:
                qty += q
                break
    return qty


def _is_reduce_only_ok(rows: list[dict[str, Any]], order_type: str) -> bool:
    target = [row for row in rows if _normalize_algo_order_type(row) == order_type]
    if not target:
        return False
    for row in target:
        text = str(row.get("reduceOnly", row.get("closePosition", ""))).strip().lower()
        if text not in {"true", "1", "yes"}:
            return False
    return True


def _write_md(path: Path, report: dict[str, Any]) -> None:
    rendered = render_protection_monitor_markdown(
        {
            "aggregate_status": report.get("aggregate_status", ""),
            "counts": report.get("counts", {}),
            "per_symbol": report.get("per_symbol", []),
        },
        title="Position Protection Distance Monitor",
    )
    rendered_lines = rendered.splitlines()
    lines = [
        "# Position Protection Distance Monitor",
        "",
        f"- ts_utc: {report.get('ts_utc', '')}",
        f"- env: {report.get('env', '')}",
        f"- symbols: {','.join(list(report.get('symbols', [])))}",
        f"- aggregate_status: {report.get('aggregate_status', '')}",
        "",
    ]
    if len(rendered_lines) > 4:
        lines.extend(rendered_lines[4:])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def monitor_position_protection_distance(
    *,
    env: str = "testnet",
    symbols: str = "FETUSDT,OPUSDT",
    output_md: str = "logs/position_protection_distance.md",
    base_url: str = "",
) -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    symbol_list = _parse_symbols(symbols)
    ts_utc = datetime.now(timezone.utc).isoformat()
    resolved_base_url = _resolve_testnet_base_url(base_url) if base_url else DEFAULT_TESTNET_BASE_URL

    if resolved_env != "testnet":
        report = {
            "ok": False,
            "ts_utc": ts_utc,
            "env": resolved_env,
            "symbols": symbol_list,
            "aggregate_status": "FAIL",
            "aggregate_reason": "env_not_testnet",
            "per_symbol": [],
            "output_md": output_md,
        }
        _write_md(Path(output_md), report)
        return report

    api_key = str(os.getenv("BINANCE_TESTNET_API_KEY", "")).strip()
    api_secret = str(os.getenv("BINANCE_TESTNET_API_SECRET", "")).strip()
    if not api_key or not api_secret:
        per_symbol = [
            {
                "symbol": symbol,
                "side": "UNKNOWN",
                "positionAmt": 0.0,
                "entryPrice": 0.0,
                "breakEvenPrice": 0.0,
                "markPrice": 0.0,
                "unrealizedProfit": 0.0,
                "notional": 0.0,
                "stop_loss_trigger_price": 0.0,
                "take_profit_trigger_price": 0.0,
                "distance_to_stop_pct": 0.0,
                "distance_to_take_profit_pct": 0.0,
                "distance_to_breakeven_pct": 0.0,
                "risk_to_stop_usdt_estimate": 0.0,
                "reward_to_tp_usdt_estimate": 0.0,
                "reward_risk_ratio_estimate": 0.0,
                "protection_health": "UNKNOWN",
                "severity": "WARNING",
                "alerts": ["missing_testnet_api_key"],
            }
            for symbol in symbol_list
        ]
        report = {
            "ok": False,
            "ts_utc": ts_utc,
            "env": resolved_env,
            "symbols": symbol_list,
            "aggregate_status": "PARTIAL",
            "aggregate_reason": "missing_testnet_api_key",
            "per_symbol": per_symbol,
            "output_md": output_md,
        }
        _write_md(Path(output_md), report)
        return report

    client = BinanceFuturesTestnetClient(api_key=api_key, api_secret=api_secret, base_url=resolved_base_url)
    per_symbol: list[dict[str, Any]] = []
    for symbol in symbol_list:
        pos_resp = client.get_position_risk(symbol=symbol)
        algo_resp = client.get_open_algo_orders(symbol=symbol, algo_type="CONDITIONAL")
        if (not bool(pos_resp.get("ok", False))) or (not bool(algo_resp.get("ok", False))):
            row_payload = {
                "symbol": symbol,
                "side": "UNKNOWN",
                "positionAmt": 0.0,
                "entryPrice": 0.0,
                "breakEvenPrice": 0.0,
                "markPrice": 0.0,
                "unrealizedProfit": 0.0,
                "notional": 0.0,
                "stop_loss_trigger_price": 0.0,
                "take_profit_trigger_price": 0.0,
                "distance_to_stop_pct": 0.0,
                "distance_to_take_profit_pct": 0.0,
                "distance_to_breakeven_pct": 0.0,
                "risk_to_stop_usdt_estimate": 0.0,
                "reward_to_tp_usdt_estimate": 0.0,
                "reward_risk_ratio_estimate": 0.0,
                "protection_health": "UNKNOWN",
                "severity": "WARNING",
                "alerts": ["state_query_failed"],
            }
            row_payload["distance_state"] = classify_protection_distance_state(row_payload)
            per_symbol.append(row_payload)
            continue

        protection = _build_protection_state(symbol=symbol, position_response=pos_resp, open_algo_response=algo_resp)
        open_rows = [row for row in _normalize_algo_rows(algo_resp.get("response", {})) if _normalize_algo_status(row) == "NEW"]
        position_amt = _to_float(protection.get("position_amt", 0.0), 0.0)
        abs_qty = abs(position_amt)
        entry = _to_float(protection.get("entry_price", 0.0), 0.0)
        mark = _to_float(protection.get("mark_price", 0.0), 0.0)
        notional = abs_qty * mark
        side = "LONG" if position_amt > 0 else ("SHORT" if position_amt < 0 else "FLAT")
        break_even = 0.0
        unrealized_profit = 0.0
        if isinstance(pos_resp.get("response", []), list):
            for row in [item for item in pos_resp.get("response", []) if isinstance(item, dict)]:
                if str(row.get("symbol", "")).strip().upper() != symbol:
                    continue
                break_even = _to_float(row.get("breakEvenPrice", 0.0), 0.0)
                unrealized_profit = _to_float(row.get("unRealizedProfit", row.get("unrealizedProfit", 0.0)), 0.0)
                break

        sl_price = _extract_trigger(open_rows, "STOP_MARKET")
        tp_price = _extract_trigger(open_rows, "TAKE_PROFIT_MARKET")
        sl_qty = _extract_qty(open_rows, "STOP_MARKET")
        tp_qty = _extract_qty(open_rows, "TAKE_PROFIT_MARKET")
        sl_reduce_ok = _is_reduce_only_ok(open_rows, "STOP_MARKET")
        tp_reduce_ok = _is_reduce_only_ok(open_rows, "TAKE_PROFIT_MARKET")

        dist_stop_pct = 0.0
        dist_tp_pct = 0.0
        dist_be_pct = 0.0
        risk_stop = 0.0
        reward_tp = 0.0
        rr = 0.0
        alerts: list[str] = []
        severity = "INFO"
        protection_health = "NO_POSITION" if abs_qty <= 0 else "HEALTHY"

        if abs_qty > 0 and mark > 0:
            if side == "LONG":
                dist_stop_pct = _safe_pct(mark - sl_price, mark) if sl_price > 0 else 0.0
                dist_tp_pct = _safe_pct(tp_price - mark, mark) if tp_price > 0 else 0.0
                dist_be_pct = _safe_pct(mark - break_even, break_even) if break_even > 0 else 0.0
                risk_stop = max(mark - sl_price, 0.0) * abs_qty if sl_price > 0 else 0.0
                reward_tp = max(tp_price - mark, 0.0) * abs_qty if tp_price > 0 else 0.0
            else:
                dist_stop_pct = _safe_pct(sl_price - mark, mark) if sl_price > 0 else 0.0
                dist_tp_pct = _safe_pct(mark - tp_price, mark) if tp_price > 0 else 0.0
                dist_be_pct = _safe_pct(break_even - mark, break_even) if break_even > 0 else 0.0
                risk_stop = max(sl_price - mark, 0.0) * abs_qty if sl_price > 0 else 0.0
                reward_tp = max(mark - tp_price, 0.0) * abs_qty if tp_price > 0 else 0.0
            rr = (reward_tp / risk_stop) if risk_stop > 0 else 0.0

            if sl_price <= 0:
                alerts.append("missing_stop_loss")
                protection_health = "MISSING_STOP_LOSS"
            if tp_price <= 0:
                alerts.append("missing_take_profit")
                protection_health = "MISSING_TAKE_PROFIT" if protection_health == "HEALTHY" else protection_health
            if sl_price > 0 and tp_price > 0 and (sl_qty + 1e-9 < abs_qty or tp_qty + 1e-9 < abs_qty):
                alerts.append("protective_quantity_insufficient")
                protection_health = "PARTIAL_PROTECTION"
            if (sl_price > 0 and not sl_reduce_ok) or (tp_price > 0 and not tp_reduce_ok):
                alerts.append("reduce_only_not_true")
                protection_health = "PARTIAL_PROTECTION"
            if side == "LONG":
                if sl_price > 0 and not (sl_price < mark):
                    alerts.append("stop_loss_direction_invalid")
                if tp_price > 0 and not (tp_price > mark):
                    alerts.append("take_profit_direction_invalid")
                if sl_price > 0 and mark <= sl_price:
                    alerts.append("mark_crossed_stop_not_triggered")
                if tp_price > 0 and mark >= tp_price:
                    alerts.append("near_or_cross_tp")
            else:
                if sl_price > 0 and not (sl_price > mark):
                    alerts.append("stop_loss_direction_invalid")
                if tp_price > 0 and not (tp_price < mark):
                    alerts.append("take_profit_direction_invalid")
                if sl_price > 0 and mark >= sl_price:
                    alerts.append("mark_crossed_stop_not_triggered")
                if tp_price > 0 and mark <= tp_price:
                    alerts.append("near_or_cross_tp")
            if dist_stop_pct > 0 and dist_stop_pct < 0.3:
                alerts.append("near_stop")
            if dist_tp_pct > 0 and dist_tp_pct < 0.3:
                alerts.append("near_take_profit")
            if risk_stop > 0 and unrealized_profit < -risk_stop:
                alerts.append("drawdown_beyond_1R")

            if any(item in alerts for item in {"missing_stop_loss", "missing_take_profit", "protective_quantity_insufficient", "stop_loss_direction_invalid", "take_profit_direction_invalid", "mark_crossed_stop_not_triggered", "reduce_only_not_true"}):
                severity = "CRITICAL"
            elif any(item in alerts for item in {"near_stop", "drawdown_beyond_1R"}):
                severity = "WARNING"
            elif alerts:
                severity = "INFO"
        else:
            alerts.append("no_position")

        row_payload = {
            "symbol": symbol,
            "side": side,
            "positionAmt": position_amt,
            "entryPrice": entry,
            "breakEvenPrice": break_even,
            "markPrice": mark,
            "unrealizedProfit": unrealized_profit,
            "notional": notional,
            "stop_loss_trigger_price": sl_price,
            "take_profit_trigger_price": tp_price,
            "distance_to_stop_pct": round(dist_stop_pct, 8),
            "distance_to_take_profit_pct": round(dist_tp_pct, 8),
            "distance_to_breakeven_pct": round(dist_be_pct, 8),
            "risk_to_stop_usdt_estimate": round(risk_stop, 8),
            "reward_to_tp_usdt_estimate": round(reward_tp, 8),
            "reward_risk_ratio_estimate": round(rr, 8),
            "protection_health": protection_health,
            "severity": severity,
            "alerts": alerts,
            "protection_status": str(protection.get("protection_status", "UNKNOWN")),
        }
        row_payload["distance_state"] = classify_protection_distance_state(row_payload)
        per_symbol.append(row_payload)

    helper_summary = summarize_protection_distance(per_symbol)
    aggregate_status = str(helper_summary.get("aggregate_status", "PASS"))
    aggregate_reason = "no_critical_alerts"
    if aggregate_status == "FAIL":
        aggregate_reason = "critical_protection_distance_alerts_present"
    elif aggregate_status == "PARTIAL":
        aggregate_reason = "warning_level_distance_alerts_present"

    report = {
        "ok": aggregate_status != "FAIL",
        "ts_utc": ts_utc,
        "env": resolved_env,
        "symbols": symbol_list,
        "aggregate_status": aggregate_status,
        "aggregate_reason": aggregate_reason,
        "counts": dict(helper_summary.get("counts", {})),
        "per_symbol": list(helper_summary.get("per_symbol", per_symbol)),
        "output_md": output_md,
    }
    _write_md(Path(output_md), report)
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor position PnL and protection distance (read-only)")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--symbols", default="FETUSDT,OPUSDT")
    parser.add_argument("--output-md", default="logs/position_protection_distance.md")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    report = monitor_position_protection_distance(
        env=str(args.env or "testnet"),
        symbols=str(args.symbols or "FETUSDT,OPUSDT"),
        output_md=str(args.output_md or "logs/position_protection_distance.md"),
        base_url=str(args.base_url or ""),
    )
    if bool(args.json):
        print(json.dumps(report, ensure_ascii=False))
        return
    print(f"aggregate_status={report.get('aggregate_status', '')}")
    print(f"aggregate_reason={report.get('aggregate_reason', '')}")
    print(f"output_md={report.get('output_md', '')}")


if __name__ == "__main__":
    main()
