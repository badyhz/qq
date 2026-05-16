from __future__ import annotations

import argparse
import csv
import math
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "current_sample_count",
    "required_next_samples",
    "block_count",
    "last_gate_decision",
    "collection_priority",
    "collection_mode",
    "reason",
    "next_action",
]


def generate_collect_more_samples_plan(
    *,
    gate_replay_csv: str = "reports/gate_replay/gate_replay_results.csv",
    candidate_recovery_csv: str = "reports/candidate_recovery/candidate_recovery_decisions.csv",
    symbol_side_csv: str = "reports/symbol_side_recommendations/symbol_side_recommendations.csv",
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    output_dir: str = "reports/collect_more_samples_plan",
) -> dict[str, Any]:
    replay_rows = read_csv_rows(Path(gate_replay_csv))
    recovery_rows = read_csv_rows(Path(candidate_recovery_csv))
    symbol_side_rows = read_csv_rows(Path(symbol_side_csv))
    strategy_rows = read_csv_rows(Path(strategy_candidate_csv))

    recovery_index = {str(row.get("candidate_id", "")).strip(): row for row in recovery_rows if str(row.get("candidate_id", "")).strip()}
    symbol_side_index = {
        (
            str(row.get("symbol", "")).strip().upper(),
            str(row.get("side", "")).strip().upper(),
            str(row.get("timeframe", "5m")).strip(),
        ): row
        for row in symbol_side_rows
    }
    strategy_index = {str(row.get("strategy_key", "")).strip(): row for row in strategy_rows if str(row.get("strategy_key", "")).strip()}

    grouped: dict[str, dict[str, Any]] = {}
    for row in replay_rows:
        decision = str(row.get("gate_decision", "")).strip().upper()
        if decision != "BLOCK_LOW_SAMPLE":
            continue
        strategy_key = str(row.get("strategy_key", "")).strip()
        symbol = str(row.get("symbol", "")).strip().upper()
        side = str(row.get("side", "")).strip().upper()
        timeframe = str(row.get("timeframe", "5m")).strip()
        key = strategy_key or f"{symbol}_{side}_{timeframe}"
        current = grouped.setdefault(
            key,
            {
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "strategy_key": key,
                "block_count": 0,
                "last_gate_decision": decision,
                "reasons": set(),
            },
        )
        current["block_count"] = int(current.get("block_count", 0)) + 1
        current["last_gate_decision"] = decision
        reason_text = str(row.get("reason", "")).strip()
        if reason_text:
            for item in reason_text.split(";"):
                if item.strip():
                    current["reasons"].add(item.strip())
        cid = str(row.get("candidate_id", "")).strip()
        recovery = recovery_index.get(cid, {})
        rec_reason = str(recovery.get("recovery_reason", "")).strip()
        if rec_reason:
            current["reasons"].add(rec_reason)

    out_rows: list[dict[str, Any]] = []
    for key in sorted(grouped.keys()):
        group = grouped[key]
        strategy = strategy_index.get(key, {})
        sample_count = int(to_float_nan(strategy.get("sample_count")) if math.isfinite(to_float_nan(strategy.get("sample_count"))) else 0)
        minimum_required = int(to_float_nan(strategy.get("minimum_required_samples")) if math.isfinite(to_float_nan(strategy.get("minimum_required_samples"))) else 20)
        required_next_samples = max(0, minimum_required - sample_count)
        block_count = int(group.get("block_count", 0))
        side_row = symbol_side_index.get((group["symbol"], group["side"], group["timeframe"]), {})
        recommendation = str(side_row.get("recommendation", "WATCH")).strip().upper()
        candidate_verdict = str(strategy.get("candidate_verdict", "PARTIAL")).strip().upper()

        priority = "P1"
        if recommendation in {"BLACKLIST", "REJECT", "PAUSE"}:
            priority = "P3"
        elif block_count >= 3 and candidate_verdict in {"PASS", "PARTIAL"}:
            priority = "P0"
        elif candidate_verdict == "FAIL":
            priority = "P2"
        collection_mode = "SHADOW_ONLY" if priority in {"P0", "P1", "P2"} else "BLOCKED"
        next_action = "collect_shadow_samples" if collection_mode == "SHADOW_ONLY" else "hold_and_review"
        reasons = set(group.get("reasons", set()))
        reasons.add("collect_more_samples")

        out_rows.append(
            {
                "symbol": group["symbol"],
                "side": group["side"],
                "timeframe": group["timeframe"],
                "strategy_key": key,
                "current_sample_count": sample_count,
                "required_next_samples": required_next_samples,
                "block_count": block_count,
                "last_gate_decision": str(group.get("last_gate_decision", "BLOCK_LOW_SAMPLE")),
                "collection_priority": priority,
                "collection_mode": collection_mode,
                "reason": ";".join(sorted(reasons)),
                "next_action": next_action,
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "collect_more_samples_plan.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if out_rows else "PARTIAL",
        "total_rows": len(out_rows),
        "p0_count": sum(1 for row in out_rows if str(row.get("collection_priority", "")).upper() == "P0"),
        "shadow_only_count": sum(1 for row in out_rows if str(row.get("collection_mode", "")).upper() == "SHADOW_ONLY"),
        "blocked_count": sum(1 for row in out_rows if str(row.get("collection_mode", "")).upper() == "BLOCKED"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Collect More Samples Plan",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_rows: {summary['total_rows']}",
        f"- p0_count: {summary['p0_count']}",
        f"- shadow_only_count: {summary['shadow_only_count']}",
        f"- blocked_count: {summary['blocked_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate collect-more-samples plan from LOW_SAMPLE gate blocks")
    parser.add_argument("--gate-replay-csv", default="reports/gate_replay/gate_replay_results.csv")
    parser.add_argument("--candidate-recovery-csv", default="reports/candidate_recovery/candidate_recovery_decisions.csv")
    parser.add_argument("--symbol-side-csv", default="reports/symbol_side_recommendations/symbol_side_recommendations.csv")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--output-dir", default="reports/collect_more_samples_plan")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_collect_more_samples_plan(
        gate_replay_csv=str(args.gate_replay_csv or "reports/gate_replay/gate_replay_results.csv"),
        candidate_recovery_csv=str(args.candidate_recovery_csv or "reports/candidate_recovery/candidate_recovery_decisions.csv"),
        symbol_side_csv=str(args.symbol_side_csv or "reports/symbol_side_recommendations/symbol_side_recommendations.csv"),
        strategy_candidate_csv=str(args.strategy_candidate_csv or "reports/strategy_candidate_score/strategy_candidate_score.csv"),
        output_dir=str(args.output_dir or "reports/collect_more_samples_plan"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"total_rows={result.get('total_rows', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
