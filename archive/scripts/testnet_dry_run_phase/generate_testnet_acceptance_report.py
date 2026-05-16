from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.risk_event_logger import DEFAULT_RISK_EVENTS_PATH
from core.trade_logger import read_jsonl_rows


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def classify_acceptance_result(payload: dict[str, Any]) -> str:
    submit_status = str(payload.get("submit_status", "")).strip().lower()
    skipped_reason = str(payload.get("skipped_reason", "")).strip()
    rejected_count = _to_int(payload.get("rejected_count", 0), 0)
    error_code = str(payload.get("error_code", "")).strip()
    protective_error_code = str(payload.get("protective_orders_error_code", "")).strip()
    protective_partial = _to_bool(payload.get("protective_orders_partial", False), False)
    protective_submitted = _to_bool(payload.get("protective_orders_submitted", False), False)
    protective_attempted = _to_bool(payload.get("protective_orders_submit_attempted", False), False)
    stop_algo_id = str(payload.get("stop_loss_algo_id", "")).strip()
    take_algo_id = str(payload.get("take_profit_algo_id", "")).strip()
    open_stop_count = _to_int(payload.get("open_stop_market_count", 0), 0)
    open_tp_count = _to_int(payload.get("open_take_profit_market_count", 0), 0)

    if submit_status == "submit_failed" or rejected_count > 0 or error_code:
        return "FAIL"
    if protective_error_code and not (stop_algo_id or take_algo_id):
        return "FAIL"

    pass_submit = submit_status == "submitted" or (
        submit_status == "skipped" and skipped_reason == "skipped_existing_fully_protected_position"
    )

    if pass_submit and protective_attempted:
        if protective_submitted and (not protective_partial):
            if open_stop_count == 0 or open_tp_count == 0:
                return "PARTIAL"
            return "PASS"
        if protective_partial:
            return "PARTIAL"
        if (stop_algo_id or take_algo_id) and not protective_submitted:
            return "PARTIAL"

    if pass_submit and not protective_attempted:
        return "PASS"

    return "PARTIAL"


def generate_testnet_acceptance_report(
    *,
    log_jsonl: str,
    output_md: str,
    symbol: str,
    env: str,
    state_json: str = "",
    run_dir: str = "",
) -> dict[str, Any]:
    resolved_log_jsonl = str(log_jsonl or "").strip()
    resolved_state_json = str(state_json or "").strip()
    run_path = Path(run_dir) if str(run_dir or "").strip() else None
    if run_path is not None:
        if not resolved_log_jsonl:
            candidate = run_path / "acceptance_source.jsonl"
            if candidate.exists():
                resolved_log_jsonl = str(candidate)
        if not resolved_state_json:
            finals = sorted(run_path.glob("final_state_*.json"))
            if finals:
                resolved_state_json = str(finals[0])

    rows = read_jsonl_rows(resolved_log_jsonl)
    latest = rows[-1] if rows else {}

    if resolved_state_json:
        state_rows = read_jsonl_rows(resolved_state_json)
        if state_rows:
            latest_state = state_rows[-1]
            if isinstance(latest_state, dict):
                latest = {**latest, "state_snapshot": latest_state}
        else:
            state_file = Path(resolved_state_json)
            if state_file.exists():
                try:
                    payload = json.loads(state_file.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        latest = {**latest, "state_snapshot": payload}
                except (OSError, json.JSONDecodeError):
                    pass

    summary = {
        "env": str(latest.get("env", env or "")).strip().lower(),
        "symbol": str(latest.get("symbol", symbol or "")).strip().upper(),
        "submit_mode": str(latest.get("submit_mode", "")),
        "live_submit": _to_bool(latest.get("live_submit", False), False),
        "submit_attempted": _to_bool(latest.get("submit_attempted", False), False),
        "submit_status": str(latest.get("submit_status", "")),
        "submitted_count": _to_int(latest.get("submitted_count", 0), 0),
        "rejected_count": _to_int(latest.get("rejected_count", 0), 0),
        "exchange_order_id": str(latest.get("exchange_order_id", "")),
        "client_order_id": str(latest.get("client_order_id", "")),
        "quantity": latest.get("quantity", 0),
        "notional_usdt": latest.get("notional_usdt", 0),
        "protective_orders_submit_attempted": _to_bool(latest.get("protective_orders_submit_attempted", False), False),
        "protective_orders_submitted": _to_bool(latest.get("protective_orders_submitted", False), False),
        "protective_orders_partial": _to_bool(latest.get("protective_orders_partial", False), False),
        "stop_loss_algo_id": str(latest.get("stop_loss_algo_id", "")),
        "take_profit_algo_id": str(latest.get("take_profit_algo_id", "")),
        "open_algo_orders_checked": _to_bool(latest.get("open_algo_orders_checked", False), False),
        "open_stop_market_count": _to_int(latest.get("open_stop_market_count", 0), 0),
        "open_take_profit_market_count": _to_int(latest.get("open_take_profit_market_count", 0), 0),
        "preflight_protection_status": str(latest.get("preflight_protection_status", "")),
        "skipped_reason": str(latest.get("skipped_reason", "")),
        "error_code": str(latest.get("error_code", "")),
        "error_message": str(latest.get("error_message", "")),
        "protective_orders_error_code": str(latest.get("protective_orders_error_code", "")),
        "protective_orders_error_message": str(latest.get("protective_orders_error_message", "")),
        "state_snapshot": dict(latest.get("state_snapshot", {})) if isinstance(latest.get("state_snapshot", {}), dict) else {},
    }

    verdict = classify_acceptance_result(summary)
    timestamp = datetime.now(timezone.utc).isoformat()
    risk_events = read_jsonl_rows(DEFAULT_RISK_EVENTS_PATH)
    related_events: list[dict[str, Any]] = []
    for event in reversed(risk_events):
        if not isinstance(event, dict):
            continue
        if str(event.get("env", "")).strip().lower() != summary["env"]:
            continue
        event_symbol = str(event.get("symbol", "")).strip().upper()
        if event_symbol and event_symbol != summary["symbol"]:
            continue
        related_events.append(event)
        if len(related_events) >= 5:
            break

    md_lines = [
        "# Testnet Acceptance Report",
        "",
        f"- Time (UTC): {timestamp}",
        f"- Env: {summary['env']}",
        f"- Symbol: {summary['symbol']}",
        f"- Verdict: **{verdict}**",
        f"- run_dir: {str(run_path) if run_path is not None else ''}",
        "",
        "## Entry Submit",
        f"- submit_mode: {summary['submit_mode']}",
        f"- live_submit: {summary['live_submit']}",
        f"- submit_attempted: {summary['submit_attempted']}",
        f"- submit_status: {summary['submit_status']}",
        f"- exchange_order_id: {summary['exchange_order_id']}",
        f"- client_order_id: {summary['client_order_id']}",
        f"- quantity: {summary['quantity']}",
        f"- notional_usdt: {summary['notional_usdt']}",
        "",
        "## Protective Orders",
        f"- protective_orders_submit_attempted: {summary['protective_orders_submit_attempted']}",
        f"- protective_orders_submitted: {summary['protective_orders_submitted']}",
        f"- protective_orders_partial: {summary['protective_orders_partial']}",
        f"- stop_loss_algo_id: {summary['stop_loss_algo_id']}",
        f"- take_profit_algo_id: {summary['take_profit_algo_id']}",
        f"- open_algo_orders_checked: {summary['open_algo_orders_checked']}",
        f"- open_stop_market_count: {summary['open_stop_market_count']}",
        f"- open_take_profit_market_count: {summary['open_take_profit_market_count']}",
        "",
        "## Lifecycle Preflight",
        f"- preflight_protection_status: {summary['preflight_protection_status']}",
        f"- skipped_reason: {summary['skipped_reason']}",
        "",
        "## Final State Snapshot",
        f"- {json.dumps(summary.get('state_snapshot', {}), ensure_ascii=False)}",
        "",
        "## Risks And Errors",
        f"- rejected_count: {summary['rejected_count']}",
        f"- error_code: {summary['error_code']}",
        f"- error_message: {summary['error_message']}",
        f"- protective_orders_error_code: {summary['protective_orders_error_code']}",
        f"- protective_orders_error_message: {summary['protective_orders_error_message']}",
        "",
        "## Recent Risk Events",
    ]
    if related_events:
        for event in related_events:
            md_lines.append(f"- [{event.get('severity', '')}] {event.get('event_type', '')}: {event.get('message', '')}")
    else:
        md_lines.append("- none")
    md_lines.extend([
        "",
        "## Next Actions",
    ])

    if verdict == "PASS":
        md_lines.append("- Keep current safeguards and continue observation shifts.")
    elif verdict == "PARTIAL":
        md_lines.append("- Inspect partial protective order state and re-run check_testnet_state before next submit.")
    else:
        md_lines.append("- Resolve submit/protective errors first, do not continue submit attempts.")

    output_path = Path(output_md)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "verdict": verdict,
        "output_md": str(output_path),
        "summary": summary,
        "resolved_log_jsonl": resolved_log_jsonl,
        "resolved_state_json": resolved_state_json,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate testnet acceptance markdown report from JSONL logs")
    parser.add_argument("--log-jsonl", default="")
    parser.add_argument("--state-json", default="")
    parser.add_argument("--output-md", default="logs/testnet_acceptance_report.md")
    parser.add_argument("--symbol", default="FETUSDT")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--run-dir", default="")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_testnet_acceptance_report(
        log_jsonl=str(args.log_jsonl or ""),
        state_json=str(args.state_json or ""),
        output_md=str(args.output_md or "logs/testnet_acceptance_report.md"),
        symbol=str(args.symbol or "FETUSDT"),
        env=str(args.env or "testnet"),
        run_dir=str(args.run_dir or ""),
    )
    summary = dict(result.get("summary", {}))
    print(f"env={summary.get('env', '')}")
    print(f"symbol={summary.get('symbol', '')}")
    print(f"submit_status={summary.get('submit_status', '')}")
    print(f"protective_orders_submitted={summary.get('protective_orders_submitted', False)}")
    print(f"verdict={result.get('verdict', 'FAIL')}")
    print(f"output_md={result.get('output_md', '')}")


if __name__ == "__main__":
    main()
