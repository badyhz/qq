from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import (
    compute_weighted_sample_count,
    sample_mix_status,
    to_float_nan,
    read_csv_rows,
)


FIELDS = [
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "real_sample_count",
    "shadow_sample_count",
    "weighted_sample_count",
    "real_win_rate",
    "shadow_win_rate",
    "real_avg_r",
    "shadow_avg_r",
    "weighted_avg_r",
    "real_total_pnl_usdt",
    "shadow_total_r",
    "sample_mix_status",
    "confidence_level",
    "verdict",
    "reason",
]


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text or "LONG"


def _to_key(symbol: str, side: str, timeframe: str) -> str:
    return f"{symbol}_{side}_{timeframe}"


def _avg(values: list[float]) -> float:
    return (sum(values) / len(values)) if values else float("nan")


def analyze_real_vs_shadow_samples(
    *,
    lifecycle_csv: str = "reports/trade_lifecycle/trade_lifecycle.csv",
    shadow_candidate_outcomes_csv: str = "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv",
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    output_dir: str = "reports/real_vs_shadow_samples",
) -> dict[str, Any]:
    lifecycle_rows = read_csv_rows(Path(lifecycle_csv))
    shadow_rows = read_csv_rows(Path(shadow_candidate_outcomes_csv))
    strategy_rows = read_csv_rows(Path(strategy_candidate_csv))

    strategy_index: dict[str, dict[str, Any]] = {}
    meta: dict[str, dict[str, str]] = {}
    for row in strategy_rows:
        strategy_key = str(row.get("strategy_key", "")).strip()
        if not strategy_key:
            continue
        strategy_index[strategy_key] = row
        meta[strategy_key] = {
            "symbol": str(row.get("symbol", "")).strip().upper(),
            "side": _normalize_side(row.get("side", "")),
            "timeframe": str(row.get("timeframe", "5m")).strip() or "5m",
        }

    real_by_key: dict[str, list[dict[str, Any]]] = {}
    for row in lifecycle_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        side = _normalize_side(row.get("side", "LONG"))
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        strategy_key = str(row.get("strategy_key", "")).strip() or _to_key(symbol, side, timeframe)
        if strategy_key not in meta:
            meta[strategy_key] = {"symbol": symbol, "side": side, "timeframe": timeframe}
        real_by_key.setdefault(strategy_key, []).append(row)

    shadow_by_key: dict[str, list[dict[str, Any]]] = {}
    for row in shadow_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        side = _normalize_side(row.get("side", "LONG"))
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        strategy_key = str(row.get("strategy_key", "")).strip() or _to_key(symbol, side, timeframe)
        if strategy_key not in meta:
            meta[strategy_key] = {"symbol": symbol, "side": side, "timeframe": timeframe}
        shadow_by_key.setdefault(strategy_key, []).append(row)

    all_keys = sorted(set(meta.keys()) | set(real_by_key.keys()) | set(shadow_by_key.keys()))
    out_rows: list[dict[str, Any]] = []
    for strategy_key in all_keys:
        m = meta.get(strategy_key, {"symbol": "", "side": "LONG", "timeframe": "5m"})
        real_items = real_by_key.get(strategy_key, [])
        shadow_items = shadow_by_key.get(strategy_key, [])
        real_count = len(real_items)
        shadow_count = len(shadow_items)
        shadow_weight = to_float_nan(strategy_index.get(strategy_key, {}).get("shadow_weight"))
        if not math.isfinite(shadow_weight) or shadow_weight <= 0:
            shadow_weight = 0.3
        weighted_count = compute_weighted_sample_count(
            real_sample_count=real_count,
            shadow_sample_count=shadow_count,
            shadow_sample_weight=shadow_weight,
        )

        real_r_values: list[float] = []
        real_pnl_values: list[float] = []
        real_wins = 0
        for item in real_items:
            realized_r = to_float_nan(item.get("realized_r_multiple"))
            pnl = to_float_nan(item.get("pnl_estimate_usdt"))
            if math.isfinite(realized_r):
                real_r_values.append(realized_r)
                if realized_r > 0:
                    real_wins += 1
            elif math.isfinite(pnl) and pnl > 0:
                real_wins += 1
            if math.isfinite(pnl):
                real_pnl_values.append(pnl)

        shadow_r_values: list[float] = []
        shadow_wins = 0
        for item in shadow_items:
            outcome = str(item.get("outcome", "")).strip().upper()
            realized_r = to_float_nan(item.get("realized_r_multiple"))
            if math.isfinite(realized_r):
                shadow_r_values.append(realized_r)
                if realized_r > 0:
                    shadow_wins += 1
            elif outcome in {"SHADOW_TP_FIRST", "SHADOW_TIMEOUT_PROFIT"}:
                shadow_wins += 1

        real_win_rate = (real_wins / real_count) if real_count > 0 else float("nan")
        shadow_win_rate = (shadow_wins / shadow_count) if shadow_count > 0 else float("nan")
        real_avg_r = _avg(real_r_values)
        shadow_avg_r = _avg(shadow_r_values)
        weighted_avg_r = float("nan")
        if weighted_count > 0 and (math.isfinite(real_avg_r) or math.isfinite(shadow_avg_r)):
            real_part = (real_avg_r * real_count) if math.isfinite(real_avg_r) else 0.0
            shadow_part = (shadow_avg_r * shadow_count * shadow_weight) if math.isfinite(shadow_avg_r) else 0.0
            weighted_avg_r = (real_part + shadow_part) / weighted_count

        confidence = str(strategy_index.get(strategy_key, {}).get("sample_confidence_level", "UNKNOWN")).strip().upper() or "UNKNOWN"
        verdict = "PARTIAL"
        reasons: list[str] = []
        if real_count >= 20 and weighted_count >= 20 and math.isfinite(real_avg_r) and real_avg_r > 0 and math.isfinite(weighted_avg_r) and weighted_avg_r > 0:
            verdict = "PASS"
            reasons.append("meets_real_and_weighted_threshold")
        elif real_count >= 10 and math.isfinite(real_avg_r) and real_avg_r < 0:
            verdict = "FAIL"
            reasons.append("real_samples_negative_expectancy")
        elif weighted_count > 0:
            verdict = "PARTIAL"
            reasons.append("insufficient_real_samples")
        else:
            verdict = "PARTIAL"
            reasons.append("no_samples")

        out_rows.append(
            {
                "strategy_key": strategy_key,
                "symbol": m.get("symbol", ""),
                "side": m.get("side", "LONG"),
                "timeframe": m.get("timeframe", "5m"),
                "real_sample_count": real_count,
                "shadow_sample_count": shadow_count,
                "weighted_sample_count": round(weighted_count, 8),
                "real_win_rate": round(real_win_rate, 8) if math.isfinite(real_win_rate) else float("nan"),
                "shadow_win_rate": round(shadow_win_rate, 8) if math.isfinite(shadow_win_rate) else float("nan"),
                "real_avg_r": round(real_avg_r, 8) if math.isfinite(real_avg_r) else float("nan"),
                "shadow_avg_r": round(shadow_avg_r, 8) if math.isfinite(shadow_avg_r) else float("nan"),
                "weighted_avg_r": round(weighted_avg_r, 8) if math.isfinite(weighted_avg_r) else float("nan"),
                "real_total_pnl_usdt": round(sum(real_pnl_values), 8) if real_pnl_values else float("nan"),
                "shadow_total_r": round(sum(shadow_r_values), 8) if shadow_r_values else float("nan"),
                "sample_mix_status": sample_mix_status(real_sample_count=real_count, shadow_sample_count=shadow_count),
                "confidence_level": confidence,
                "verdict": verdict,
                "reason": ";".join(sorted(set(reasons))),
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "real_vs_shadow_samples.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "strategy_count": len(out_rows),
        "pass_count": sum(1 for row in out_rows if str(row.get("verdict", "")).strip().upper() == "PASS"),
        "partial_count": sum(1 for row in out_rows if str(row.get("verdict", "")).strip().upper() == "PARTIAL"),
        "fail_count": sum(1 for row in out_rows if str(row.get("verdict", "")).strip().upper() == "FAIL"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["final_verdict"] = "PASS"
    if summary["fail_count"] > 0:
        summary["final_verdict"] = "FAIL"
    elif summary["partial_count"] > 0 or summary["strategy_count"] == 0:
        summary["final_verdict"] = "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Real vs Shadow Samples Summary",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- strategy_count: {summary['strategy_count']}",
        f"- pass_count: {summary['pass_count']}",
        f"- partial_count: {summary['partial_count']}",
        f"- fail_count: {summary['fail_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze real trade samples vs shadow samples")
    parser.add_argument("--lifecycle-csv", default="reports/trade_lifecycle/trade_lifecycle.csv")
    parser.add_argument("--shadow-candidate-outcomes-csv", default="reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--output-dir", default="reports/real_vs_shadow_samples")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = analyze_real_vs_shadow_samples(
        lifecycle_csv=str(args.lifecycle_csv or "reports/trade_lifecycle/trade_lifecycle.csv"),
        shadow_candidate_outcomes_csv=str(args.shadow_candidate_outcomes_csv or "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv"),
        strategy_candidate_csv=str(args.strategy_candidate_csv or "reports/strategy_candidate_score/strategy_candidate_score.csv"),
        output_dir=str(args.output_dir or "reports/real_vs_shadow_samples"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"strategy_count={result.get('strategy_count', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
