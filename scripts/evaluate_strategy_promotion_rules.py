from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "param_signature",
    "sample_count",
    "sample_confidence_level",
    "strategy_candidate_score",
    "candidate_verdict",
    "recommendation",
    "promotion_decision",
    "priority",
    "risk_flags",
    "required_next_samples",
    "reason",
]


def evaluate_strategy_promotion_rules(
    *,
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    symbol_side_recommendation_csv: str = "reports/symbol_side_recommendations/symbol_side_recommendations.csv",
    anomalies_top_json: str = "reports/trade_lifecycle_anomalies/top_anomalies.json",
    output_dir: str = "reports/strategy_promotion",
) -> dict[str, Any]:
    candidate_rows = read_csv_rows(Path(strategy_candidate_csv))
    rec_rows = read_csv_rows(Path(symbol_side_recommendation_csv))
    try:
        anomalies = json.loads(Path(anomalies_top_json).read_text(encoding="utf-8")) if Path(anomalies_top_json).exists() else {}
    except (OSError, json.JSONDecodeError):
        anomalies = {}
    severity_counts = dict(anomalies.get("severity_counts", {})) if isinstance(anomalies.get("severity_counts", {}), dict) else {}
    has_critical = int(severity_counts.get("critical_count", 0) or 0) > 0
    has_high = int(severity_counts.get("high_count", 0) or 0) > 0

    rec_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rec_rows:
        key = (
            str(row.get("symbol", "")).strip().upper(),
            str(row.get("side", "")).strip().upper(),
            str(row.get("timeframe", "")).strip(),
        )
        rec_index[key] = row

    rows: list[dict[str, Any]] = []
    for row in candidate_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        side_raw = str(row.get("side", "")).strip().upper()
        side = "SHORT" if side_raw in {"SELL", "SHORT"} else "LONG" if side_raw in {"BUY", "LONG"} else side_raw
        timeframe = str(row.get("timeframe", "5m") or "5m")
        recommendation_row = rec_index.get((symbol, side, timeframe)) or rec_index.get((symbol, side_raw, timeframe)) or {}
        recommendation = str(recommendation_row.get("recommendation", "UNKNOWN")).strip().upper()
        sample_count = int(to_float_nan(row.get("sample_count")) if math.isfinite(to_float_nan(row.get("sample_count"))) else 0)
        minimum_required = int(to_float_nan(row.get("minimum_required_samples")) if math.isfinite(to_float_nan(row.get("minimum_required_samples"))) else 20)
        required_next_samples = max(0, minimum_required - sample_count)
        confidence = str(row.get("sample_confidence_level", "UNKNOWN")).strip().upper()
        candidate_verdict = str(row.get("candidate_verdict", "UNKNOWN")).strip().upper()
        score = to_float_nan(row.get("strategy_candidate_score"))

        risk_flags: list[str] = []
        reasons: list[str] = []
        decision = "UNKNOWN"
        priority = "P2"

        if has_critical:
            risk_flags.append("critical_anomaly_present")
            decision = "PAUSE_STRATEGY"
            priority = "P3"
            reasons.append("critical_anomaly_present")
        elif recommendation in {"BLACKLIST", "REJECT"}:
            decision = "REJECT_STRATEGY"
            priority = "P4"
            reasons.append("symbol_side_rejected")
        elif recommendation == "PAUSE":
            decision = "PAUSE_STRATEGY"
            priority = "P3"
            reasons.append("symbol_side_paused")
        elif candidate_verdict == "FAIL" and sample_count >= 10:
            decision = "REJECT_STRATEGY"
            priority = "P4"
            reasons.append("candidate_verdict_fail")
        elif confidence in {"TOO_SMALL", "LOW"}:
            decision = "KEEP_COLLECTING"
            priority = "P1" if confidence == "TOO_SMALL" else "P2"
            reasons.append("sample_size_too_small")
        elif recommendation in {"PROMOTE", "WHITELIST"} and candidate_verdict == "PASS" and not has_high:
            decision = "PROMOTE_TO_OBSERVATION"
            priority = "P0"
            reasons.append("meets_promotion_conditions")
        elif recommendation == "ALLOW_TESTNET_SMALL_SIZE" and candidate_verdict in {"PASS", "PARTIAL"}:
            decision = "KEEP_COLLECTING"
            priority = "P1"
            reasons.append("allow_small_size_continue_sampling")
        elif candidate_verdict == "PARTIAL":
            decision = "REDUCE_PRIORITY"
            priority = "P2"
            reasons.append("partial_quality")
        else:
            decision = "KEEP_COLLECTING"
            priority = "P2"
            reasons.append("default_collecting")

        if has_high and decision == "PROMOTE_TO_OBSERVATION":
            decision = "KEEP_COLLECTING"
            priority = "P1"
            reasons.append("high_anomaly_blocks_promotion")

        if decision in {"REJECT_STRATEGY", "PAUSE_STRATEGY"}:
            required_next_samples = max(required_next_samples, 0)

        rows.append(
            {
                "strategy_key": str(row.get("strategy_key", "")),
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "param_signature": str(row.get("param_signature", "N/A")),
                "sample_count": sample_count,
                "sample_confidence_level": confidence,
                "strategy_candidate_score": round(score, 8) if math.isfinite(score) else float("nan"),
                "candidate_verdict": candidate_verdict,
                "recommendation": recommendation,
                "promotion_decision": decision,
                "priority": priority,
                "risk_flags": ";".join(sorted(set(risk_flags))),
                "required_next_samples": required_next_samples,
                "reason": ";".join(sorted(set(reasons))),
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "strategy_promotion_decisions.csv"
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
        "promote_count": sum(1 for row in rows if str(row.get("promotion_decision", "")).upper() == "PROMOTE_TO_OBSERVATION"),
        "keep_collecting_count": sum(1 for row in rows if str(row.get("promotion_decision", "")).upper() == "KEEP_COLLECTING"),
        "reduce_priority_count": sum(1 for row in rows if str(row.get("promotion_decision", "")).upper() == "REDUCE_PRIORITY"),
        "pause_or_reject_count": sum(1 for row in rows if str(row.get("promotion_decision", "")).upper() in {"PAUSE_STRATEGY", "REJECT_STRATEGY"}),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["final_verdict"] = "PASS" if summary["total_rows"] > 0 else "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Strategy Promotion Summary",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- total_rows: {summary['total_rows']}",
        f"- promote_count: {summary['promote_count']}",
        f"- keep_collecting_count: {summary['keep_collecting_count']}",
        f"- reduce_priority_count: {summary['reduce_priority_count']}",
        f"- pause_or_reject_count: {summary['pause_or_reject_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate promotion rules for strategy candidates")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--symbol-side-recommendation-csv", default="reports/symbol_side_recommendations/symbol_side_recommendations.csv")
    parser.add_argument("--anomalies-top-json", default="reports/trade_lifecycle_anomalies/top_anomalies.json")
    parser.add_argument("--output-dir", default="reports/strategy_promotion")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = evaluate_strategy_promotion_rules(
        strategy_candidate_csv=str(args.strategy_candidate_csv or "reports/strategy_candidate_score/strategy_candidate_score.csv"),
        symbol_side_recommendation_csv=str(args.symbol_side_recommendation_csv or "reports/symbol_side_recommendations/symbol_side_recommendations.csv"),
        anomalies_top_json=str(args.anomalies_top_json or "reports/trade_lifecycle_anomalies/top_anomalies.json"),
        output_dir=str(args.output_dir or "reports/strategy_promotion"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"total_rows={result.get('total_rows', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
