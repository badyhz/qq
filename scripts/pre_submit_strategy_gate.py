from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _find_strategy_row(rows: list[dict[str, Any]], strategy_key: str, symbol: str, side: str, timeframe: str) -> dict[str, Any]:
    strategy_key = str(strategy_key or "").strip()
    symbol = str(symbol or "").strip().upper()
    side = str(side or "").strip().upper()
    timeframe = str(timeframe or "").strip()
    for row in rows:
        if strategy_key and str(row.get("strategy_key", "")).strip() == strategy_key:
            return row
    for row in rows:
        row_symbol = str(row.get("symbol", "")).strip().upper()
        row_side = str(row.get("side", "")).strip().upper()
        row_tf = str(row.get("timeframe", "")).strip()
        if row_symbol == symbol and row_tf == timeframe and (row_side == side or (row_side in {"BUY", "LONG"} and side in {"BUY", "LONG"}) or (row_side in {"SELL", "SHORT"} and side in {"SELL", "SHORT"})):
            return row
    return {}


def pre_submit_strategy_gate(
    *,
    candidate_id: str,
    symbol: str,
    side: str,
    timeframe: str,
    strategy_key: str,
    reports_dir: str = "reports",
    logs_dir: str = "logs",
) -> dict[str, Any]:
    reports_root = Path(reports_dir)
    logs_root = Path(logs_dir)
    system_health = _load_json(reports_root / "system_health" / "trading_system_health_dashboard.json")
    promotion_rows = read_csv_rows(reports_root / "strategy_promotion" / "strategy_promotion_decisions.csv")
    symbol_side_rows = read_csv_rows(reports_root / "symbol_side_recommendations" / "symbol_side_recommendations.csv")
    candidate_rows = read_csv_rows(reports_root / "strategy_candidate_score" / "strategy_candidate_score.csv")
    multi_day = _load_json(logs_root / "multi_day_performance_report.json")

    symbol_u = str(symbol or "").strip().upper()
    side_u = str(side or "").strip().upper()
    timeframe_u = str(timeframe or "5m").strip()
    strategy_key_u = str(strategy_key or "").strip()

    health_verdict = str(system_health.get("final_verdict", "UNKNOWN")).strip().upper()
    health_next_action = str(system_health.get("next_action", "")).strip().upper()
    has_system_health = bool(system_health)

    promotion = _find_strategy_row(promotion_rows, strategy_key_u, symbol_u, side_u, timeframe_u)
    recommendation_row = _find_strategy_row(symbol_side_rows, strategy_key_u, symbol_u, side_u, timeframe_u)
    candidate = _find_strategy_row(candidate_rows, strategy_key_u, symbol_u, side_u, timeframe_u)

    recommendation = str(recommendation_row.get("recommendation", "UNKNOWN")).strip().upper()
    promotion_decision = str(promotion.get("promotion_decision", "UNKNOWN")).strip().upper()
    sample_confidence = str(candidate.get("sample_confidence_level", "UNKNOWN")).strip().upper()
    required_next_samples = int(to_float_nan(promotion.get("required_next_samples")) if str(promotion.get("required_next_samples", "")).strip() else 0)

    reasons: list[str] = []
    submit_allowed = False
    dry_run_allowed = True
    gate_decision = "BLOCK_UNKNOWN"

    if not has_system_health:
        gate_decision = "BLOCK_UNKNOWN"
        submit_allowed = False
        dry_run_allowed = True
        reasons.append("missing_system_health_report")
    elif health_verdict == "FAIL":
        gate_decision = "BLOCK_SYSTEM_HEALTH"
        submit_allowed = False
        dry_run_allowed = True
        reasons.append("system_health_fail")
    elif recommendation in {"BLACKLIST", "REJECT", "PAUSE"}:
        gate_decision = "BLOCK_SYMBOL_SIDE"
        submit_allowed = False
        dry_run_allowed = True
        reasons.append("symbol_side_policy_block")
    elif promotion_decision in {"REJECT_STRATEGY", "PAUSE_STRATEGY"}:
        gate_decision = "BLOCK_STRATEGY_REJECTED"
        submit_allowed = False
        dry_run_allowed = True
        reasons.append("promotion_decision_block")
    elif sample_confidence == "TOO_SMALL":
        gate_decision = "BLOCK_LOW_SAMPLE"
        submit_allowed = False
        dry_run_allowed = True
        reasons.append("sample_size_too_small")
    elif health_next_action == "DO_NOT_SUBMIT_TODAY_MAX_DAILY_SUBMITS_REACHED":
        gate_decision = "ALLOW_DRY_RUN"
        submit_allowed = False
        dry_run_allowed = True
        reasons.append("max_daily_submits_reached")
    else:
        allow_recommendation = recommendation in {"ALLOW_TESTNET_SMALL_SIZE", "PROMOTE", "WHITELIST"}
        allow_promotion = promotion_decision in {"PROMOTE_TO_OBSERVATION", "KEEP_COLLECTING"}
        if (
            health_verdict == "PASS"
            and allow_recommendation
            and allow_promotion
            and sample_confidence not in {"TOO_SMALL", "UNKNOWN"}
        ):
            gate_decision = "ALLOW_TESTNET_AFTER_RESET"
            submit_allowed = True
            dry_run_allowed = True
            reasons.append("meets_gate_requirements")
        else:
            gate_decision = "ALLOW_DRY_RUN"
            submit_allowed = False
            dry_run_allowed = True
            reasons.append("dry_run_only_until_more_evidence")

    # Ensure daily limit still blocks submission even in allow path.
    if health_next_action == "DO_NOT_SUBMIT_TODAY_MAX_DAILY_SUBMITS_REACHED":
        submit_allowed = False
        if "max_daily_submits_reached" not in reasons:
            reasons.append("max_daily_submits_reached")
        if gate_decision == "ALLOW_TESTNET_AFTER_RESET":
            gate_decision = "ALLOW_DRY_RUN"

    if gate_decision == "ALLOW_DRY_RUN" and sample_confidence == "TOO_SMALL":
        gate_decision = "BLOCK_LOW_SAMPLE"

    result = {
        "candidate_id": str(candidate_id or ""),
        "symbol": symbol_u,
        "side": side_u,
        "timeframe": timeframe_u,
        "strategy_key": strategy_key_u,
        "gate_decision": gate_decision,
        "submit_allowed": bool(submit_allowed),
        "dry_run_allowed": bool(dry_run_allowed),
        "reason": sorted(set(reasons)),
        "required_next_samples": required_next_samples,
        "system_health_verdict": health_verdict or "UNKNOWN",
        "recommendation": recommendation or "UNKNOWN",
        "promotion_decision": promotion_decision or "UNKNOWN",
        "sample_confidence_level": sample_confidence or "UNKNOWN",
        "multi_day_verdict": str(multi_day.get("final_verdict", "UNKNOWN")).strip().upper() if multi_day else "UNKNOWN",
    }
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only pre-submit strategy gate")
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--side", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--strategy-key", required=True)
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = pre_submit_strategy_gate(
        candidate_id=str(args.candidate_id or ""),
        symbol=str(args.symbol or ""),
        side=str(args.side or ""),
        timeframe=str(args.timeframe or ""),
        strategy_key=str(args.strategy_key or ""),
        reports_dir=str(args.reports_dir or "reports"),
        logs_dir=str(args.logs_dir or "logs"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"gate_decision={result.get('gate_decision', '')}")
    print(f"submit_allowed={result.get('submit_allowed', False)}")
    print(f"dry_run_allowed={result.get('dry_run_allowed', False)}")


if __name__ == "__main__":
    main()
