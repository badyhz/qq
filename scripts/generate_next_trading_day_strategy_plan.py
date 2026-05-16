from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "rank",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "promotion_decision",
    "priority",
    "sample_count",
    "required_next_samples",
    "risk_level",
    "watch_reason",
    "allowed_action",
    "submit_permission",
    "notes",
]

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def generate_next_trading_day_strategy_plan(
    *,
    promotion_csv: str = "reports/strategy_promotion/strategy_promotion_decisions.csv",
    symbol_side_csv: str = "reports/symbol_side_recommendations/symbol_side_recommendations.csv",
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    output_dir: str = "reports/next_trading_day_strategy_plan",
) -> dict[str, Any]:
    promotion_rows = read_csv_rows(Path(promotion_csv))
    symbol_side_rows = read_csv_rows(Path(symbol_side_csv))
    candidate_rows = read_csv_rows(Path(strategy_candidate_csv))
    try:
        system_health = json.loads(Path(system_health_json).read_text(encoding="utf-8")) if Path(system_health_json).exists() else {}
    except (OSError, json.JSONDecodeError):
        system_health = {}

    symbol_side_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in symbol_side_rows:
        key = (
            str(row.get("symbol", "")).strip().upper(),
            str(row.get("side", "")).strip().upper(),
            str(row.get("timeframe", "")).strip(),
        )
        symbol_side_index[key] = row

    candidate_index = {str(row.get("strategy_key", "")).strip(): row for row in candidate_rows if str(row.get("strategy_key", "")).strip()}
    health_verdict = str(system_health.get("final_verdict", "UNKNOWN")).strip().upper()
    next_action = str(system_health.get("next_action", "")).strip().upper()
    no_submit_today = next_action == "DO_NOT_SUBMIT_TODAY_MAX_DAILY_SUBMITS_REACHED"

    rows: list[dict[str, Any]] = []
    for row in promotion_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        side = str(row.get("side", "")).strip().upper()
        timeframe = str(row.get("timeframe", "5m")).strip()
        strategy_key = str(row.get("strategy_key", "")).strip()
        promotion_decision = str(row.get("promotion_decision", "UNKNOWN")).strip().upper()
        priority = str(row.get("priority", "P2")).strip().upper() or "P2"
        sample_count = int(to_float_nan(row.get("sample_count")) if str(row.get("sample_count", "")).strip() else 0)
        required_next_samples = int(to_float_nan(row.get("required_next_samples")) if str(row.get("required_next_samples", "")).strip() else 0)
        reason = str(row.get("reason", "")).strip()
        side_row = symbol_side_index.get((symbol, side, timeframe), {})
        if not side_row:
            side_row = symbol_side_index.get((symbol, "LONG" if side == "BUY" else side, timeframe), {})
        recommendation = str(side_row.get("recommendation", "UNKNOWN")).strip().upper()
        risk_level = str(side_row.get("risk_level", "UNKNOWN")).strip().upper()

        watch_reason_parts: list[str] = []
        if "sample_size_too_small" in reason:
            watch_reason_parts.append("collect_more_samples")
        if recommendation == "WATCH":
            watch_reason_parts.append("watch_mode")
        if required_next_samples > 0:
            watch_reason_parts.append(f"need_{required_next_samples}_more_samples")
        if not watch_reason_parts:
            watch_reason_parts.append("monitor_strategy_behavior")

        allowed_action = "OBSERVE_ONLY"
        if health_verdict == "FAIL":
            allowed_action = "BLOCKED"
        elif promotion_decision in {"REJECT_STRATEGY", "PAUSE_STRATEGY"} or recommendation in {"REJECT", "BLACKLIST", "PAUSE"}:
            allowed_action = "BLOCKED"
        elif promotion_decision == "PROMOTE_TO_OBSERVATION" and recommendation in {"PROMOTE", "WHITELIST"}:
            allowed_action = "TESTNET_SMALL_SIZE_ALLOWED"
        elif recommendation == "ALLOW_TESTNET_SMALL_SIZE":
            allowed_action = "TESTNET_SMALL_SIZE_ALLOWED"
        elif promotion_decision in {"KEEP_COLLECTING", "REDUCE_PRIORITY"}:
            allowed_action = "TESTNET_DRY_RUN_ONLY"
        else:
            allowed_action = "SHADOW_ONLY"

        submit_permission = "NO_REAL_SUBMIT"
        if health_verdict == "FAIL":
            submit_permission = "BLOCKED"
        elif no_submit_today:
            submit_permission = "NO_TESTNET_SUBMIT_TODAY"
            if allowed_action == "TESTNET_SMALL_SIZE_ALLOWED":
                allowed_action = "TESTNET_DRY_RUN_ONLY"
        elif allowed_action == "TESTNET_SMALL_SIZE_ALLOWED":
            submit_permission = "TESTNET_SUBMIT_ALLOWED_AFTER_RESET"
        elif allowed_action in {"TESTNET_DRY_RUN_ONLY", "SHADOW_ONLY", "OBSERVE_ONLY"}:
            submit_permission = "TESTNET_DRY_RUN_ONLY"
        elif allowed_action == "BLOCKED":
            submit_permission = "BLOCKED"

        notes: list[str] = []
        if no_submit_today:
            notes.append("max_daily_submits_reached")
        notes.append(f"system_health={health_verdict}")
        if strategy_key in candidate_index:
            conf = str(candidate_index[strategy_key].get("sample_confidence_level", "")).strip().upper()
            if conf:
                notes.append(f"sample_confidence={conf}")

        rows.append(
            {
                "rank": 0,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "strategy_key": strategy_key,
                "promotion_decision": promotion_decision,
                "priority": priority,
                "sample_count": sample_count,
                "required_next_samples": required_next_samples,
                "risk_level": risk_level or "UNKNOWN",
                "watch_reason": ";".join(sorted(set(watch_reason_parts))),
                "allowed_action": allowed_action,
                "submit_permission": submit_permission,
                "notes": ";".join(notes),
            }
        )

    rows.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(str(item.get("priority", "P4")).upper(), 9),
            -int(item.get("sample_count", 0) or 0),
            str(item.get("symbol", "")),
        )
    )
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "strategy_watchlist.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(rows),
        "observe_only_count": sum(1 for row in rows if str(row.get("allowed_action", "")).upper() == "OBSERVE_ONLY"),
        "dry_run_only_count": sum(1 for row in rows if str(row.get("allowed_action", "")).upper() == "TESTNET_DRY_RUN_ONLY"),
        "blocked_count": sum(1 for row in rows if str(row.get("allowed_action", "")).upper() == "BLOCKED"),
        "submit_permission_no_testnet_today_count": sum(1 for row in rows if str(row.get("submit_permission", "")).upper() == "NO_TESTNET_SUBMIT_TODAY"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["final_verdict"] = "PASS" if rows else "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Next Trading Day Strategy Plan",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_rows: {summary['total_rows']}",
        f"- observe_only_count: {summary['observe_only_count']}",
        f"- dry_run_only_count: {summary['dry_run_only_count']}",
        f"- blocked_count: {summary['blocked_count']}",
        f"- submit_permission_no_testnet_today_count: {summary['submit_permission_no_testnet_today_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate next trading day strategy watchlist")
    parser.add_argument("--promotion-csv", default="reports/strategy_promotion/strategy_promotion_decisions.csv")
    parser.add_argument("--symbol-side-csv", default="reports/symbol_side_recommendations/symbol_side_recommendations.csv")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--output-dir", default="reports/next_trading_day_strategy_plan")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_next_trading_day_strategy_plan(
        promotion_csv=str(args.promotion_csv or "reports/strategy_promotion/strategy_promotion_decisions.csv"),
        symbol_side_csv=str(args.symbol_side_csv or "reports/symbol_side_recommendations/symbol_side_recommendations.csv"),
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        strategy_candidate_csv=str(args.strategy_candidate_csv or "reports/strategy_candidate_score/strategy_candidate_score.csv"),
        output_dir=str(args.output_dir or "reports/next_trading_day_strategy_plan"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"total_rows={result.get('total_rows', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
