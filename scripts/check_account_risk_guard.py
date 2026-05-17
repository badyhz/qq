from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core.account_risk_guard import load_account_risk_config, validate_account_risk_before_submit
from core.trade_logger import read_jsonl_rows
from scripts.account_protection_report_common import classify_account_risk_guard, summarize_account_risk_state
from scripts.check_testnet_state import check_testnet_state


def _parse_csv(value: str) -> list[str]:
    return [item.strip().upper() for item in str(value or "").split(",") if item.strip()]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _load_approved_run_summaries(approved_runs_dir: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    root = Path(approved_runs_dir)
    if not root.exists():
        return rows
    for summary_path in root.glob("*/summary.json"):
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _state_notional_usdt(state: dict[str, Any]) -> float:
    try:
        position_amt = abs(float(state.get("positionAmt", 0.0) or 0.0))
    except (TypeError, ValueError):
        position_amt = 0.0
    if position_amt <= 0:
        return 0.0
    try:
        mark = abs(float(state.get("markPrice", 0.0) or 0.0))
    except (TypeError, ValueError):
        mark = 0.0
    if mark <= 0:
        try:
            mark = abs(float(state.get("entryPrice", 0.0) or 0.0))
        except (TypeError, ValueError):
            mark = 0.0
    return position_amt * mark


def check_account_risk_guard(
    *,
    env: str = "testnet",
    symbols: str = "FETUSDT,OPUSDT",
    target_symbol: str = "",
    target_notional_usdt: float = 0.0,
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    approved_runs_dir: str = "logs/approved_candidate_runs",
    config: str = "config.yaml",
) -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    symbol_list = _parse_csv(symbols)
    per_symbol_state = [check_testnet_state(env=resolved_env, symbol=symbol) for symbol in symbol_list]
    candidates = [row for row in read_jsonl_rows(candidates_jsonl) if isinstance(row, dict)]
    run_summaries = _load_approved_run_summaries(approved_runs_dir)
    target = str(target_symbol or "").strip().upper() or (symbol_list[0] if symbol_list else "")
    result = validate_account_risk_before_submit(
        env=resolved_env,
        target_symbol=target,
        target_notional_usdt=float(target_notional_usdt or 0.0),
        per_symbol_state=per_symbol_state,
        candidates=candidates,
        approved_run_summaries=run_summaries,
        config=load_account_risk_config(config),
    )
    current_open_positions = int(result.get("checks", {}).get("open_positions", 0))
    total_notional = sum(_state_notional_usdt(state) for state in per_symbol_state if isinstance(state, dict))
    payload = {
        "ok": True,
        "env": resolved_env,
        "symbols": symbol_list,
        "target_symbol": target,
        "target_notional_usdt": float(target_notional_usdt or 0.0),
        "allowed": bool(result.get("allowed", False)),
        "reason": str(result.get("reason", "")),
        "severity": str(result.get("severity", "")),
        "checks": dict(result.get("checks", {})),
        "current_open_positions": current_open_positions,
        "total_notional": round(total_notional, 8),
        "daily_submitted_count": int(result.get("checks", {}).get("daily_submitted_count", 0)),
        "pending_or_approved_count": int(result.get("checks", {}).get("pending_or_approved_candidates", 0)),
        "duplicate_candidate_id_count": int(result.get("checks", {}).get("duplicate_candidate_ids", 0)),
        "action_required": str(result.get("action_required", "")),
        "per_symbol_state": per_symbol_state,
    }
    account_summary = summarize_account_risk_state([payload])
    payload.update(account_summary)
    payload.update(classify_account_risk_guard(account_summary))
    return payload


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only account risk guard checker for next submit decision")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--symbols", default="FETUSDT,OPUSDT")
    parser.add_argument("--target-symbol", default="")
    parser.add_argument("--target-notional-usdt", default="0")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--approved-runs-dir", default="logs/approved_candidate_runs")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    payload = check_account_risk_guard(
        env=str(args.env or "testnet"),
        symbols=str(args.symbols or "FETUSDT,OPUSDT"),
        target_symbol=str(args.target_symbol or ""),
        target_notional_usdt=_to_float(args.target_notional_usdt, 0.0),
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        approved_runs_dir=str(args.approved_runs_dir or "logs/approved_candidate_runs"),
        config=str(args.config or "config.yaml"),
    )
    if bool(args.json):
        print(json.dumps(payload, ensure_ascii=False))
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
