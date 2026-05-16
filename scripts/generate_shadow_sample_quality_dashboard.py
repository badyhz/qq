from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


BY_STRATEGY_FIELDS = [
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "shadow_candidate_count",
    "strict_candidate_count",
    "near_miss_candidate_count",
    "tp_first_count",
    "sl_first_count",
    "timeout_count",
    "avg_mfe_r",
    "avg_mae_r",
    "avg_realized_r_multiple",
    "duplicate_filtered_count",
    "cooldown_blocked_count",
    "quality_verdict",
    "reason",
]

BY_COLLECTOR_MODE_FIELDS = [
    "collector_mode",
    "candidate_count",
    "near_miss_count",
    "strict_count",
    "evaluated_count",
    "tp_first_count",
    "sl_first_count",
    "timeout_count",
    "avg_realized_r",
    "quality_verdict",
    "reason",
]

BY_HORIZON_FIELDS = [
    "horizon_bars",
    "candidate_count",
    "evaluated_count",
    "tp_first_count",
    "sl_first_count",
    "timeout_count",
    "avg_mfe_r",
    "avg_mae_r",
    "avg_realized_r",
    "quality_verdict",
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text or "LONG"


def generate_shadow_sample_quality_dashboard(
    *,
    shadow_collection_summary_json: str = "reports/shadow_candidate_collection/summary.json",
    shadow_candidates_csv: str = "reports/shadow_candidate_collection/shadow_candidates.csv",
    shadow_outcomes_csv: str = "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv",
    shadow_outcomes_by_horizon_csv: str = "reports/shadow_candidate_outcomes/shadow_candidate_outcomes_by_horizon.csv",
    sample_collection_tracker_csv: str = "reports/sample_collection_tracker/sample_collection_tracker.csv",
    real_vs_shadow_csv: str = "reports/real_vs_shadow_samples/real_vs_shadow_samples.csv",
    output_dir: str = "reports/shadow_sample_quality",
) -> dict[str, Any]:
    collection_summary = _read_json(Path(shadow_collection_summary_json))
    candidate_rows = read_csv_rows(Path(shadow_candidates_csv))
    outcome_rows = read_csv_rows(Path(shadow_outcomes_csv))
    horizon_rows = read_csv_rows(Path(shadow_outcomes_by_horizon_csv))
    tracker_rows = read_csv_rows(Path(sample_collection_tracker_csv))
    rvss_rows = read_csv_rows(Path(real_vs_shadow_csv))

    tracker_index = {str(row.get("strategy_key", "")).strip(): row for row in tracker_rows if str(row.get("strategy_key", "")).strip()}
    rvss_index = {str(row.get("strategy_key", "")).strip(): row for row in rvss_rows if str(row.get("strategy_key", "")).strip()}
    outcome_by_id = {
        str(row.get("shadow_candidate_id", "")).strip(): row
        for row in outcome_rows
        if str(row.get("shadow_candidate_id", "")).strip()
    }
    horizon_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in horizon_rows:
        cid = str(row.get("shadow_candidate_id", "")).strip()
        if cid:
            horizon_map[cid].append(row)

    by_strategy: dict[str, dict[str, Any]] = {}
    duplicate_filtered_count = int(to_float_nan(collection_summary.get("duplicate_count")) if math.isfinite(to_float_nan(collection_summary.get("duplicate_count"))) else 0)
    cooldown_blocked_count = int(
        to_float_nan(collection_summary.get("cooldown_blocked_count")) if math.isfinite(to_float_nan(collection_summary.get("cooldown_blocked_count"))) else 0
    )

    for row in candidate_rows:
        strategy_key = str(row.get("strategy_key", "")).strip() or "UNKNOWN"
        info = by_strategy.setdefault(
            strategy_key,
            {
                "strategy_key": strategy_key,
                "symbol": str(row.get("symbol", "")).strip().upper(),
                "side": _normalize_side(row.get("side", "")),
                "timeframe": str(row.get("timeframe", "5m")).strip() or "5m",
                "shadow_candidate_count": 0,
                "strict_candidate_count": 0,
                "near_miss_candidate_count": 0,
                "tp_first_count": 0,
                "sl_first_count": 0,
                "timeout_count": 0,
                "mfe_values": [],
                "mae_values": [],
                "r_values": [],
                "duplicate_filtered_count": 0,
                "cooldown_blocked_count": 0,
            },
        )
        info["shadow_candidate_count"] += 1
        if str(row.get("candidate_status", "")).strip().upper() == "SHADOW_ONLY":
            info["strict_candidate_count"] += 1
        if str(row.get("near_miss", "")).strip().lower() in {"1", "true", "yes", "y"}:
            info["near_miss_candidate_count"] += 1

        cid = str(row.get("candidate_id", "")).strip()
        outcome = outcome_by_id.get(cid, {})
        outcome_name = str(outcome.get("outcome", "")).strip().upper()
        if outcome_name == "SHADOW_TP_FIRST":
            info["tp_first_count"] += 1
        if outcome_name == "SHADOW_SL_FIRST":
            info["sl_first_count"] += 1
        if outcome_name.startswith("SHADOW_TIMEOUT_"):
            info["timeout_count"] += 1
        r_value = to_float_nan(outcome.get("realized_r_multiple"))
        if math.isfinite(r_value):
            info["r_values"].append(r_value)

        for hrow in horizon_map.get(cid, []):
            mfe = to_float_nan(hrow.get("mfe_r"))
            mae = to_float_nan(hrow.get("mae_r"))
            if math.isfinite(mfe):
                info["mfe_values"].append(mfe)
            if math.isfinite(mae):
                info["mae_values"].append(mae)

    by_strategy_rows: list[dict[str, Any]] = []
    for strategy_key, info in sorted(by_strategy.items()):
        rvss = rvss_index.get(strategy_key, {})
        tracker = tracker_index.get(strategy_key, {})
        avg_r = sum(info["r_values"]) / len(info["r_values"]) if info["r_values"] else float("nan")
        avg_mfe = sum(info["mfe_values"]) / len(info["mfe_values"]) if info["mfe_values"] else float("nan")
        avg_mae = sum(info["mae_values"]) / len(info["mae_values"]) if info["mae_values"] else float("nan")
        reason_parts: list[str] = []
        verdict = "PASS"
        if info["shadow_candidate_count"] == 0:
            verdict = "PARTIAL"
            reason_parts.append("no_shadow_candidates_collected")
        if info["tp_first_count"] + info["sl_first_count"] + info["timeout_count"] == 0:
            verdict = "PARTIAL"
            reason_parts.append("no_outcome_evaluated")
        if str(tracker.get("weighted_confidence_level", "")).strip().upper() in {"TOO_SMALL", "LOW"}:
            reason_parts.append("low_confidence")
        if str(rvss.get("verdict", "")).strip().upper() == "FAIL":
            verdict = "FAIL"
            reason_parts.append("real_vs_shadow_fail")
        row = {
            "strategy_key": strategy_key,
            "symbol": info["symbol"],
            "side": info["side"],
            "timeframe": info["timeframe"],
            "shadow_candidate_count": info["shadow_candidate_count"],
            "strict_candidate_count": info["strict_candidate_count"],
            "near_miss_candidate_count": info["near_miss_candidate_count"],
            "tp_first_count": info["tp_first_count"],
            "sl_first_count": info["sl_first_count"],
            "timeout_count": info["timeout_count"],
            "avg_mfe_r": round(avg_mfe, 8) if math.isfinite(avg_mfe) else float("nan"),
            "avg_mae_r": round(avg_mae, 8) if math.isfinite(avg_mae) else float("nan"),
            "avg_realized_r_multiple": round(avg_r, 8) if math.isfinite(avg_r) else float("nan"),
            "duplicate_filtered_count": 0,
            "cooldown_blocked_count": 0,
            "quality_verdict": verdict,
            "reason": ";".join(sorted(set(reason_parts))) if reason_parts else "ok",
        }
        by_strategy_rows.append(row)

    for row in by_strategy_rows:
        row["duplicate_filtered_count"] = duplicate_filtered_count
        row["cooldown_blocked_count"] = cooldown_blocked_count

    evaluated_shadow_count = len(outcome_rows)
    tp_first_count = sum(1 for row in outcome_rows if str(row.get("outcome", "")).strip().upper() == "SHADOW_TP_FIRST")
    sl_first_count = sum(1 for row in outcome_rows if str(row.get("outcome", "")).strip().upper() == "SHADOW_SL_FIRST")
    r_values = [to_float_nan(row.get("realized_r_multiple")) for row in outcome_rows if math.isfinite(to_float_nan(row.get("realized_r_multiple")))]
    avg_shadow_r = (sum(r_values) / len(r_values)) if r_values else None
    strict_candidate_count = sum(1 for row in candidate_rows if str(row.get("candidate_status", "")).strip().upper() == "SHADOW_ONLY")
    near_miss_candidate_count = sum(1 for row in candidate_rows if str(row.get("near_miss", "")).strip().lower() in {"1", "true", "yes", "y"})

    top_strategy_keys = sorted(
        (
            {
                "strategy_key": row["strategy_key"],
                "shadow_candidate_count": int(row["shadow_candidate_count"]),
                "avg_realized_r_multiple": None if (not math.isfinite(to_float_nan(row["avg_realized_r_multiple"]))) else float(row["avg_realized_r_multiple"]),
            }
            for row in by_strategy_rows
        ),
        key=lambda item: (item["shadow_candidate_count"], item["avg_realized_r_multiple"] if item["avg_realized_r_multiple"] is not None else -999.0),
        reverse=True,
    )[:5]

    operator_attention: list[str] = []
    if len(candidate_rows) == 0:
        operator_attention.append("no_shadow_candidates_collected")
    if evaluated_shadow_count == 0:
        operator_attention.append("no_shadow_outcomes_evaluated")
    if duplicate_filtered_count > 0:
        operator_attention.append("duplicate_signals_filtered")
    if cooldown_blocked_count > 0:
        operator_attention.append("cooldown_blocks_present")

    final_verdict = "PASS"
    if len(candidate_rows) == 0 or evaluated_shadow_count == 0:
        final_verdict = "PARTIAL"
    unknown_or_missing = sum(
        1
        for row in outcome_rows
        if str(row.get("outcome", "")).strip().upper() in {"UNKNOWN", "MISSING_KLINES", "INSUFFICIENT_DATA"}
    )
    if evaluated_shadow_count >= 10 and (unknown_or_missing / max(1, evaluated_shadow_count)) >= 0.8:
        final_verdict = "FAIL"
        operator_attention.append("outcome_quality_degraded")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dashboard_json = out_dir / "shadow_sample_quality_dashboard.json"
    by_strategy_csv = out_dir / "by_strategy.csv"
    by_collector_mode_csv = out_dir / "by_collector_mode.csv"
    by_horizon_csv = out_dir / "by_horizon.csv"
    summary_md = out_dir / "summary.md"

    with by_strategy_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BY_STRATEGY_FIELDS)
        writer.writeheader()
        for row in by_strategy_rows:
            writer.writerow({field: row.get(field, "") for field in BY_STRATEGY_FIELDS})

    # Collector mode layer (strict / observation / diagnostic / unknown)
    merged_meta: dict[str, dict[str, Any]] = {}
    for row in candidate_rows:
        cid = str(row.get("candidate_id", row.get("shadow_candidate_id", ""))).strip()
        if not cid:
            continue
        merged_meta[cid] = {**merged_meta.get(cid, {}), **row}
    for row in outcome_rows:
        cid = str(row.get("shadow_candidate_id", row.get("candidate_id", ""))).strip()
        if not cid:
            continue
        merged_meta[cid] = {**merged_meta.get(cid, {}), **row}

    by_mode_acc: dict[str, dict[str, Any]] = {}
    for cid, row in merged_meta.items():
        mode = str(row.get("collector_mode", "")).strip().lower()
        if not mode:
            if str(row.get("candidate_status", "")).strip().upper() == "SHADOW_OBSERVATION_ONLY":
                mode = "observation"
            elif str(row.get("candidate_status", "")).strip().upper() == "SHADOW_ONLY":
                mode = "strict"
            else:
                mode = "unknown"
        acc = by_mode_acc.setdefault(
            mode,
            {
                "collector_mode": mode,
                "candidate_count": 0,
                "near_miss_count": 0,
                "strict_count": 0,
                "evaluated_count": 0,
                "tp_first_count": 0,
                "sl_first_count": 0,
                "timeout_count": 0,
                "r_values": [],
            },
        )
        acc["candidate_count"] += 1
        if str(row.get("candidate_status", "")).strip().upper() == "SHADOW_ONLY":
            acc["strict_count"] += 1
        if str(row.get("near_miss", "")).strip().lower() in {"1", "true", "yes", "y"}:
            acc["near_miss_count"] += 1
        outcome_name = str(row.get("outcome", "")).strip().upper()
        if outcome_name:
            acc["evaluated_count"] += 1
            if outcome_name == "SHADOW_TP_FIRST":
                acc["tp_first_count"] += 1
            if outcome_name == "SHADOW_SL_FIRST":
                acc["sl_first_count"] += 1
            if outcome_name.startswith("SHADOW_TIMEOUT_"):
                acc["timeout_count"] += 1
        r_value = to_float_nan(row.get("realized_r_multiple"))
        if math.isfinite(r_value):
            acc["r_values"].append(r_value)

    by_collector_rows: list[dict[str, Any]] = []
    for mode in sorted(by_mode_acc.keys()):
        item = by_mode_acc[mode]
        avg_r = (sum(item["r_values"]) / len(item["r_values"])) if item["r_values"] else float("nan")
        verdict = "PASS"
        reasons: list[str] = []
        if int(item["candidate_count"]) <= 0:
            verdict = "PARTIAL"
            reasons.append("no_candidates")
        if int(item["evaluated_count"]) <= 0:
            verdict = "PARTIAL"
            reasons.append("no_outcomes")
        by_collector_rows.append(
            {
                "collector_mode": mode,
                "candidate_count": int(item["candidate_count"]),
                "near_miss_count": int(item["near_miss_count"]),
                "strict_count": int(item["strict_count"]),
                "evaluated_count": int(item["evaluated_count"]),
                "tp_first_count": int(item["tp_first_count"]),
                "sl_first_count": int(item["sl_first_count"]),
                "timeout_count": int(item["timeout_count"]),
                "avg_realized_r": round(avg_r, 8) if math.isfinite(avg_r) else float("nan"),
                "quality_verdict": verdict,
                "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
            }
        )
    with by_collector_mode_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BY_COLLECTOR_MODE_FIELDS)
        writer.writeheader()
        for row in by_collector_rows:
            writer.writerow({field: row.get(field, "") for field in BY_COLLECTOR_MODE_FIELDS})

    # Horizon layer
    by_horizon_acc: dict[int, dict[str, Any]] = {}
    for row in horizon_rows:
        h = int(to_float_nan(row.get("horizon_bars")) if math.isfinite(to_float_nan(row.get("horizon_bars"))) else 0)
        if h <= 0:
            continue
        item = by_horizon_acc.setdefault(
            h,
            {
                "horizon_bars": h,
                "candidate_ids": set(),
                "evaluated_count": 0,
                "tp_first_count": 0,
                "sl_first_count": 0,
                "timeout_count": 0,
                "mfe_values": [],
                "mae_values": [],
                "r_values": [],
            },
        )
        cid = str(row.get("shadow_candidate_id", "")).strip()
        if cid:
            item["candidate_ids"].add(cid)
        outcome_name = str(row.get("outcome", "")).strip().upper()
        if outcome_name:
            item["evaluated_count"] += 1
            if outcome_name == "SHADOW_TP_FIRST":
                item["tp_first_count"] += 1
            if outcome_name == "SHADOW_SL_FIRST":
                item["sl_first_count"] += 1
            if outcome_name.startswith("SHADOW_TIMEOUT_"):
                item["timeout_count"] += 1
        mfe = to_float_nan(row.get("mfe_r"))
        mae = to_float_nan(row.get("mae_r"))
        rr = to_float_nan(row.get("realized_r_multiple"))
        if math.isfinite(mfe):
            item["mfe_values"].append(mfe)
        if math.isfinite(mae):
            item["mae_values"].append(mae)
        if math.isfinite(rr):
            item["r_values"].append(rr)

    by_horizon_rows_out: list[dict[str, Any]] = []
    for h in sorted(by_horizon_acc.keys()):
        item = by_horizon_acc[h]
        avg_mfe = (sum(item["mfe_values"]) / len(item["mfe_values"])) if item["mfe_values"] else float("nan")
        avg_mae = (sum(item["mae_values"]) / len(item["mae_values"])) if item["mae_values"] else float("nan")
        avg_r = (sum(item["r_values"]) / len(item["r_values"])) if item["r_values"] else float("nan")
        verdict = "PASS"
        if int(item["evaluated_count"]) <= 0:
            verdict = "PARTIAL"
        by_horizon_rows_out.append(
            {
                "horizon_bars": h,
                "candidate_count": len(item["candidate_ids"]),
                "evaluated_count": int(item["evaluated_count"]),
                "tp_first_count": int(item["tp_first_count"]),
                "sl_first_count": int(item["sl_first_count"]),
                "timeout_count": int(item["timeout_count"]),
                "avg_mfe_r": round(avg_mfe, 8) if math.isfinite(avg_mfe) else float("nan"),
                "avg_mae_r": round(avg_mae, 8) if math.isfinite(avg_mae) else float("nan"),
                "avg_realized_r": round(avg_r, 8) if math.isfinite(avg_r) else float("nan"),
                "quality_verdict": verdict,
            }
        )
    with by_horizon_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BY_HORIZON_FIELDS)
        writer.writeheader()
        for row in by_horizon_rows_out:
            writer.writerow({field: row.get(field, "") for field in BY_HORIZON_FIELDS})

    dashboard = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "shadow_candidate_count": len(candidate_rows),
        "strict_candidate_count": strict_candidate_count,
        "near_miss_candidate_count": near_miss_candidate_count,
        "duplicate_filtered_count": duplicate_filtered_count,
        "cooldown_blocked_count": cooldown_blocked_count,
        "evaluated_shadow_count": evaluated_shadow_count,
        "tp_first_count": tp_first_count,
        "sl_first_count": sl_first_count,
        "avg_shadow_realized_r_multiple": None if avg_shadow_r is None else round(avg_shadow_r, 8),
        "top_strategy_keys": top_strategy_keys,
        "operator_attention": sorted(set(operator_attention)),
        "strict_layer": {
            "candidate_count": int(sum(1 for row in merged_meta.values() if str(row.get("collector_mode", "")).strip().lower() == "strict")),
            "evaluated_count": int(sum(1 for row in outcome_rows if str(row.get("collector_mode", "")).strip().lower() == "strict")),
            "avg_realized_r": None,
            "verdict": "PARTIAL" if strict_candidate_count <= 0 else "PASS",
        },
        "observation_layer": {
            "candidate_count": int(
                sum(
                    1
                    for row in merged_meta.values()
                    if str(row.get("collector_mode", "")).strip().lower() == "observation"
                    or str(row.get("candidate_status", "")).strip().upper() == "SHADOW_OBSERVATION_ONLY"
                )
            ),
            "near_miss_count": near_miss_candidate_count,
            "evaluated_count": int(
                sum(
                    1
                    for row in outcome_rows
                    if str(row.get("collector_mode", "")).strip().lower() == "observation"
                    or str(row.get("candidate_status", "")).strip().upper() == "SHADOW_OBSERVATION_ONLY"
                    or str(row.get("near_miss", "")).strip().lower() in {"1", "true", "yes", "y"}
                )
            ),
            "avg_realized_r": None,
            "verdict": "PARTIAL",
        },
        "horizon_layer": {
            str(int(row["horizon_bars"])): {
                "evaluated_count": int(row["evaluated_count"]),
                "avg_realized_r": None
                if (not math.isfinite(to_float_nan(row.get("avg_realized_r"))))
                else float(row.get("avg_realized_r")),
            }
            for row in by_horizon_rows_out
        },
        "dashboard_inputs": {
            "shadow_collection_summary_json": shadow_collection_summary_json,
            "shadow_candidates_csv": shadow_candidates_csv,
            "shadow_outcomes_csv": shadow_outcomes_csv,
            "shadow_outcomes_by_horizon_csv": shadow_outcomes_by_horizon_csv,
            "sample_collection_tracker_csv": sample_collection_tracker_csv,
        "real_vs_shadow_csv": real_vs_shadow_csv,
        },
        "by_strategy_csv": str(by_strategy_csv),
        "by_collector_mode_csv": str(by_collector_mode_csv),
        "by_horizon_csv": str(by_horizon_csv),
        "summary_md": str(summary_md),
    }
    strict_r_values = [
        to_float_nan(row.get("realized_r_multiple"))
        for row in outcome_rows
        if str(row.get("collector_mode", "")).strip().lower() == "strict" and math.isfinite(to_float_nan(row.get("realized_r_multiple")))
    ]
    obs_r_values = [
        to_float_nan(row.get("realized_r_multiple"))
        for row in outcome_rows
        if (
            str(row.get("collector_mode", "")).strip().lower() == "observation"
            or str(row.get("candidate_status", "")).strip().upper() == "SHADOW_OBSERVATION_ONLY"
            or str(row.get("near_miss", "")).strip().lower() in {"1", "true", "yes", "y"}
        )
        and math.isfinite(to_float_nan(row.get("realized_r_multiple")))
    ]
    dashboard["strict_layer"]["avg_realized_r"] = (
        round(sum(strict_r_values) / len(strict_r_values), 8) if strict_r_values else None
    )
    dashboard["observation_layer"]["avg_realized_r"] = (
        round(sum(obs_r_values) / len(obs_r_values), 8) if obs_r_values else None
    )
    if int(dashboard["observation_layer"]["candidate_count"]) > 0 and int(dashboard["observation_layer"]["evaluated_count"]) <= 0:
        operator_attention.append("observation_candidates_need_outcome")
        dashboard["operator_attention"] = sorted(set(operator_attention))
    dashboard_json.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Sample Quality Dashboard",
        "",
        f"- final_verdict: {final_verdict}",
        f"- shadow_candidate_count: {len(candidate_rows)}",
        f"- strict_candidate_count: {strict_candidate_count}",
        f"- near_miss_candidate_count: {near_miss_candidate_count}",
        f"- evaluated_shadow_count: {evaluated_shadow_count}",
        f"- tp_first_count: {tp_first_count}",
        f"- sl_first_count: {sl_first_count}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dashboard


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate shadow sample quality dashboard")
    parser.add_argument("--shadow-collection-summary-json", default="reports/shadow_candidate_collection/summary.json")
    parser.add_argument("--shadow-candidates-csv", default="reports/shadow_candidate_collection/shadow_candidates.csv")
    parser.add_argument("--shadow-outcomes-csv", default="reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv")
    parser.add_argument("--shadow-outcomes-by-horizon-csv", default="reports/shadow_candidate_outcomes/shadow_candidate_outcomes_by_horizon.csv")
    parser.add_argument("--sample-collection-tracker-csv", default="reports/sample_collection_tracker/sample_collection_tracker.csv")
    parser.add_argument("--real-vs-shadow-csv", default="reports/real_vs_shadow_samples/real_vs_shadow_samples.csv")
    parser.add_argument("--output-dir", default="reports/shadow_sample_quality")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_sample_quality_dashboard(
        shadow_collection_summary_json=str(args.shadow_collection_summary_json or "reports/shadow_candidate_collection/summary.json"),
        shadow_candidates_csv=str(args.shadow_candidates_csv or "reports/shadow_candidate_collection/shadow_candidates.csv"),
        shadow_outcomes_csv=str(args.shadow_outcomes_csv or "reports/shadow_candidate_outcomes/shadow_candidate_outcomes.csv"),
        shadow_outcomes_by_horizon_csv=str(
            args.shadow_outcomes_by_horizon_csv or "reports/shadow_candidate_outcomes/shadow_candidate_outcomes_by_horizon.csv"
        ),
        sample_collection_tracker_csv=str(args.sample_collection_tracker_csv or "reports/sample_collection_tracker/sample_collection_tracker.csv"),
        real_vs_shadow_csv=str(args.real_vs_shadow_csv or "reports/real_vs_shadow_samples/real_vs_shadow_samples.csv"),
        output_dir=str(args.output_dir or "reports/shadow_sample_quality"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"shadow_candidate_count={result.get('shadow_candidate_count', 0)}")


if __name__ == "__main__":
    main()
