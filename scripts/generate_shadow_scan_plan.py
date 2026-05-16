from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows


FIELDS = [
    "rank",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "required_next_samples",
    "sample_count",
    "sample_confidence_level",
    "scan_priority",
    "allowed_collection_mode",
    "submit_permission",
    "reason",
    "max_shadow_candidates_per_day",
]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_shadow_scan_plan(
    *,
    watchlist_csv: str = "reports/next_trading_day_strategy_plan/strategy_watchlist.csv",
    strategy_promotion_csv: str = "reports/strategy_promotion/strategy_promotion_decisions.csv",
    reset_readiness_json: str = "reports/testnet_reset_readiness/testnet_reset_readiness.json",
    output_dir: str = "reports/shadow_scan_plan",
) -> dict[str, Any]:
    watch_rows = read_csv_rows(Path(watchlist_csv))
    promotion_rows = read_csv_rows(Path(strategy_promotion_csv))
    readiness = _load_json(Path(reset_readiness_json))

    promotion_index = {str(row.get("strategy_key", "")).strip(): row for row in promotion_rows if str(row.get("strategy_key", "")).strip()}
    can_submit_after_reset = bool(readiness.get("can_submit_after_reset", False))

    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(watch_rows, start=1):
        strategy_key = str(row.get("strategy_key", "")).strip()
        promotion = promotion_index.get(strategy_key, {})
        sample_conf = str(promotion.get("sample_confidence_level", "UNKNOWN")).strip().upper() or "UNKNOWN"
        sample_count = int(float(str(promotion.get("sample_count", "0") or "0")))
        required_next_samples = int(float(str(promotion.get("required_next_samples", "0") or "0")))
        priority = str(row.get("priority", "P2")).strip().upper() or "P2"
        allowed_action = str(row.get("allowed_action", "OBSERVE_ONLY")).strip().upper()
        submit_permission = "NO_TESTNET_SUBMIT"
        mode = "SHADOW_ONLY"
        reasons: list[str] = []
        if required_next_samples > 0:
            reasons.append("collect_more_samples")
        if sample_conf in {"TOO_SMALL", "LOW", "UNKNOWN"}:
            reasons.append("low_sample_confidence")
        if allowed_action == "BLOCKED":
            mode = "BLOCKED"
            reasons.append("watchlist_blocked")
        elif allowed_action == "TESTNET_DRY_RUN_ONLY":
            mode = "DRY_RUN_ONLY"
            reasons.append("dry_run_only_policy")
        else:
            mode = "SHADOW_ONLY"
        if can_submit_after_reset and mode != "BLOCKED":
            submit_permission = "NO_TESTNET_SUBMIT"
            reasons.append("shadow_only_pipeline")
        max_shadow_per_day = 10 if priority == "P0" else 8 if priority == "P1" else 5 if priority == "P2" else 3
        rows.append(
            {
                "rank": idx,
                "symbol": str(row.get("symbol", "")).strip().upper(),
                "side": str(row.get("side", "")).strip().upper(),
                "timeframe": str(row.get("timeframe", "5m")).strip(),
                "strategy_key": strategy_key,
                "required_next_samples": required_next_samples,
                "sample_count": sample_count,
                "sample_confidence_level": sample_conf,
                "scan_priority": priority,
                "allowed_collection_mode": mode,
                "submit_permission": submit_permission,
                "reason": ";".join(sorted(set(reasons))),
                "max_shadow_candidates_per_day": max_shadow_per_day,
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "shadow_scan_plan.csv"
    json_path = out_dir / "shadow_scan_plan.json"
    md_path = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if rows else "PARTIAL",
        "total_rows": len(rows),
        "shadow_only_count": sum(1 for row in rows if str(row.get("allowed_collection_mode", "")).upper() == "SHADOW_ONLY"),
        "dry_run_only_count": sum(1 for row in rows if str(row.get("allowed_collection_mode", "")).upper() == "DRY_RUN_ONLY"),
        "blocked_count": sum(1 for row in rows if str(row.get("allowed_collection_mode", "")).upper() == "BLOCKED"),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "summary_md": str(md_path),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Scan Plan",
        "",
        f"- final_verdict: {payload['final_verdict']}",
        f"- total_rows: {payload['total_rows']}",
        f"- shadow_only_count: {payload['shadow_only_count']}",
        f"- dry_run_only_count: {payload['dry_run_only_count']}",
        f"- blocked_count: {payload['blocked_count']}",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate next-day shadow scan plan from watchlist and readiness")
    parser.add_argument("--watchlist-csv", default="reports/next_trading_day_strategy_plan/strategy_watchlist.csv")
    parser.add_argument("--strategy-promotion-csv", default="reports/strategy_promotion/strategy_promotion_decisions.csv")
    parser.add_argument("--reset-readiness-json", default="reports/testnet_reset_readiness/testnet_reset_readiness.json")
    parser.add_argument("--output-dir", default="reports/shadow_scan_plan")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_scan_plan(
        watchlist_csv=str(args.watchlist_csv or "reports/next_trading_day_strategy_plan/strategy_watchlist.csv"),
        strategy_promotion_csv=str(args.strategy_promotion_csv or "reports/strategy_promotion/strategy_promotion_decisions.csv"),
        reset_readiness_json=str(args.reset_readiness_json or "reports/testnet_reset_readiness/testnet_reset_readiness.json"),
        output_dir=str(args.output_dir or "reports/shadow_scan_plan"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"total_rows={result.get('total_rows', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
