from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows


ADJUSTMENT_FIELDS = [
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "current_priority",
    "recommended_priority",
    "adjustment_action",
    "reason",
    "cooldown_adjustment",
    "max_candidates_adjustment",
    "next_action",
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _priority_rank(value: str) -> int:
    text = str(value or "").strip().upper()
    table = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    return table.get(text, 9)


def _rank_to_priority(rank: int) -> str:
    table = {0: "P0", 1: "P1", 2: "P2", 3: "P3", 4: "P4"}
    return table.get(max(0, min(4, int(rank))), "P3")


def adjust_shadow_scan_universe(
    *,
    shadow_scan_universe_csv: str = "reports/shadow_scan_universe/shadow_scan_universe.csv",
    shadow_quality_dashboard_json: str = "reports/shadow_sample_quality/shadow_sample_quality_dashboard.json",
    by_strategy_csv: str = "reports/shadow_sample_quality/by_strategy.csv",
    near_miss_scores_csv: str = "reports/shadow_near_miss/near_miss_scores.csv",
    shadow_universe_collection_summary_json: str = "reports/shadow_universe_collection/summary.json",
    kline_cache_backfill_summary_json: str = "reports/kline_cache_backfill/summary.json",
    output_dir: str = "reports/shadow_universe_adjustment",
) -> dict[str, Any]:
    universe_rows = read_csv_rows(Path(shadow_scan_universe_csv))
    quality_dashboard = _read_json(Path(shadow_quality_dashboard_json))
    strategy_rows = read_csv_rows(Path(by_strategy_csv))
    near_miss_rows = read_csv_rows(Path(near_miss_scores_csv))
    universe_summary = _read_json(Path(shadow_universe_collection_summary_json))
    backfill_summary = _read_json(Path(kline_cache_backfill_summary_json))

    strategy_index = {
        str(row.get("strategy_key", "")).strip(): row
        for row in strategy_rows
        if str(row.get("strategy_key", "")).strip()
    }
    near_miss_by_strategy: dict[str, list[dict[str, Any]]] = {}
    for row in near_miss_rows:
        key = str(row.get("strategy_key", "")).strip()
        if not key:
            continue
        near_miss_by_strategy.setdefault(key, []).append(row)

    adjustments: list[dict[str, Any]] = []
    adjusted_rows: list[dict[str, Any]] = []
    for row in universe_rows:
        strategy_key = str(row.get("strategy_key", "")).strip()
        symbol = str(row.get("symbol", "")).strip().upper()
        side = str(row.get("side", "")).strip().upper()
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        current_priority = str(row.get("scan_priority", "P2")).strip().upper() or "P2"
        current_rank = _priority_rank(current_priority)
        cache_status = str(row.get("cache_status", "")).strip().upper() or "UNKNOWN"
        strategy_stat = strategy_index.get(strategy_key, {})
        near_list = list(near_miss_by_strategy.get(strategy_key, []))

        action = "KEEP_PRIORITY"
        reason_parts: list[str] = []
        cooldown_adjustment = "KEEP"
        max_candidates_adjustment = "KEEP"
        next_action = "continue_shadow_collection"
        recommended_rank = current_rank

        quality_verdict = str(strategy_stat.get("quality_verdict", "")).strip().upper()
        if quality_verdict == "FAIL":
            action = "REDUCE_PRIORITY"
            recommended_rank = min(4, current_rank + 1)
            reason_parts.append("quality_verdict_fail")
            next_action = "reduce_scan_focus"

        if cache_status != "OK":
            action = "REQUIRE_MORE_DATA"
            reason_parts.append("cache_not_ready")
            next_action = "run_public_kline_backfill"

        # Conservative near-miss handling: do not promote on tiny data.
        if near_list:
            with_outcome = [
                item
                for item in near_list
                if str(item.get("near_miss_verdict", "")).strip().upper() not in {"NO_OUTCOME", ""}
            ]
            promoting_hints = {
                "RELAX_BREAKOUT_FILTER",
                "RELAX_TREND_FILTER",
                "RELAX_RISK_REWARD_FILTER",
            }
            hint_rows = [
                item
                for item in with_outcome
                if str(item.get("near_miss_promotion_hint", "")).strip().upper() in promoting_hints
            ]
            if len(with_outcome) < 3:
                if action == "KEEP_PRIORITY":
                    action = "REQUIRE_MORE_DATA"
                reason_parts.append("need_more_outcome_data")
                next_action = "collect_more_near_miss_outcomes"
            elif len(hint_rows) >= 2 and action not in {"REDUCE_PRIORITY", "PAUSE_UNIVERSE_ROW"}:
                action = "PROMOTE_PRIORITY"
                recommended_rank = max(0, current_rank - 1)
                reason_parts.append("near_miss_outcomes_positive")
                next_action = "increase_shadow_observation_focus"
            else:
                reason_parts.append("near_miss_signal_inconclusive")

        # If repeated no-signal with broad universe, keep but request more data.
        strict_count = int(universe_summary.get("strict_candidate_count", 0) or 0)
        if strict_count <= 0 and action == "KEEP_PRIORITY":
            action = "REQUIRE_MORE_DATA"
            reason_parts.append("strict_candidates_absent")
            next_action = "continue_observation_mode"

        if int(quality_dashboard.get("duplicate_filtered_count", 0) or 0) > 0:
            cooldown_adjustment = "INCREASE"
        if int(quality_dashboard.get("cooldown_blocked_count", 0) or 0) > 0:
            max_candidates_adjustment = "DECREASE"

        recommended_priority = _rank_to_priority(recommended_rank)
        reason = ";".join(sorted(set(reason_parts))) if reason_parts else "stable"

        adjustments.append(
            {
                "strategy_key": strategy_key,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "current_priority": current_priority,
                "recommended_priority": recommended_priority,
                "adjustment_action": action,
                "reason": reason,
                "cooldown_adjustment": cooldown_adjustment,
                "max_candidates_adjustment": max_candidates_adjustment,
                "next_action": next_action,
            }
        )
        updated = dict(row)
        updated["scan_priority"] = recommended_priority
        updated["reason"] = reason
        adjusted_rows.append(updated)

    adjusted_rows.sort(
        key=lambda item: (
            _priority_rank(str(item.get("scan_priority", "P9"))),
            str(item.get("symbol", "")),
            str(item.get("timeframe", "")),
        )
    )
    for idx, row in enumerate(adjusted_rows, start=1):
        row["rank"] = idx

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    adjustments_csv = out_dir / "shadow_universe_adjustments.csv"
    adjusted_universe_csv = out_dir / "adjusted_shadow_scan_universe.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"

    with adjustments_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ADJUSTMENT_FIELDS)
        writer.writeheader()
        for row in adjustments:
            writer.writerow({field: row.get(field, "") for field in ADJUSTMENT_FIELDS})

    universe_fields = list(universe_rows[0].keys()) if universe_rows else [
        "rank",
        "symbol",
        "side",
        "timeframe",
        "strategy_key",
        "source",
        "scan_priority",
        "allowed_collection_mode",
        "max_shadow_candidates_per_day",
        "needs_kline_cache",
        "cache_status",
        "reason",
    ]
    with adjusted_universe_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=universe_fields)
        writer.writeheader()
        for row in adjusted_rows:
            writer.writerow({field: row.get(field, "") for field in universe_fields})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if adjustments else "PARTIAL",
        "total_rows": len(adjustments),
        "action_counts": {
            "PROMOTE_PRIORITY": sum(1 for row in adjustments if str(row.get("adjustment_action", "")).upper() == "PROMOTE_PRIORITY"),
            "KEEP_PRIORITY": sum(1 for row in adjustments if str(row.get("adjustment_action", "")).upper() == "KEEP_PRIORITY"),
            "REDUCE_PRIORITY": sum(1 for row in adjustments if str(row.get("adjustment_action", "")).upper() == "REDUCE_PRIORITY"),
            "PAUSE_UNIVERSE_ROW": sum(1 for row in adjustments if str(row.get("adjustment_action", "")).upper() == "PAUSE_UNIVERSE_ROW"),
            "REQUIRE_MORE_DATA": sum(1 for row in adjustments if str(row.get("adjustment_action", "")).upper() == "REQUIRE_MORE_DATA"),
            "UNKNOWN": sum(1 for row in adjustments if str(row.get("adjustment_action", "")).upper() == "UNKNOWN"),
        },
        "adjustments_csv": str(adjustments_csv),
        "adjusted_shadow_scan_universe_csv": str(adjusted_universe_csv),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Universe Adjustment Summary",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_rows: {summary['total_rows']}",
        f"- require_more_data: {summary['action_counts']['REQUIRE_MORE_DATA']}",
        f"- promote_priority: {summary['action_counts']['PROMOTE_PRIORITY']}",
        f"- keep_priority: {summary['action_counts']['KEEP_PRIORITY']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Adjust shadow scan universe by quality and near-miss outcomes")
    parser.add_argument("--shadow-scan-universe-csv", default="reports/shadow_scan_universe/shadow_scan_universe.csv")
    parser.add_argument("--shadow-quality-dashboard-json", default="reports/shadow_sample_quality/shadow_sample_quality_dashboard.json")
    parser.add_argument("--by-strategy-csv", default="reports/shadow_sample_quality/by_strategy.csv")
    parser.add_argument("--near-miss-scores-csv", default="reports/shadow_near_miss/near_miss_scores.csv")
    parser.add_argument("--shadow-universe-collection-summary-json", default="reports/shadow_universe_collection/summary.json")
    parser.add_argument("--kline-cache-backfill-summary-json", default="reports/kline_cache_backfill/summary.json")
    parser.add_argument("--output-dir", default="reports/shadow_universe_adjustment")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = adjust_shadow_scan_universe(
        shadow_scan_universe_csv=str(args.shadow_scan_universe_csv or "reports/shadow_scan_universe/shadow_scan_universe.csv"),
        shadow_quality_dashboard_json=str(args.shadow_quality_dashboard_json or "reports/shadow_sample_quality/shadow_sample_quality_dashboard.json"),
        by_strategy_csv=str(args.by_strategy_csv or "reports/shadow_sample_quality/by_strategy.csv"),
        near_miss_scores_csv=str(args.near_miss_scores_csv or "reports/shadow_near_miss/near_miss_scores.csv"),
        shadow_universe_collection_summary_json=str(
            args.shadow_universe_collection_summary_json or "reports/shadow_universe_collection/summary.json"
        ),
        kline_cache_backfill_summary_json=str(args.kline_cache_backfill_summary_json or "reports/kline_cache_backfill/summary.json"),
        output_dir=str(args.output_dir or "reports/shadow_universe_adjustment"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"total_rows={result.get('total_rows', 0)}")


if __name__ == "__main__":
    main()
