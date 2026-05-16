from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


FIELDS = [
    "experiment_id",
    "strategy_key",
    "symbol",
    "side",
    "timeframe",
    "experiment_type",
    "collector_mode",
    "min_trend_score",
    "min_breakout_score",
    "min_risk_reward",
    "near_miss_threshold",
    "allow_near_miss",
    "sample_target",
    "max_candidates_per_day",
    "allowed_mode",
    "submit_permission",
    "experiment_status",
    "risk_level",
    "reason",
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _add_experiment(rows: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    unique_key = (
        str(payload.get("strategy_key", "")),
        str(payload.get("experiment_type", "")),
        str(payload.get("collector_mode", "")),
        str(payload.get("min_trend_score", "")),
        str(payload.get("min_breakout_score", "")),
        str(payload.get("min_risk_reward", "")),
        str(payload.get("near_miss_threshold", "")),
    )
    for old in rows:
        old_key = (
            str(old.get("strategy_key", "")),
            str(old.get("experiment_type", "")),
            str(old.get("collector_mode", "")),
            str(old.get("min_trend_score", "")),
            str(old.get("min_breakout_score", "")),
            str(old.get("min_risk_reward", "")),
            str(old.get("near_miss_threshold", "")),
        )
        if old_key == unique_key:
            return
    rows.append(payload)


def generate_shadow_observation_experiment_matrix(
    *,
    strategy_relaxation_suggestions_csv: str = "reports/strategy_relaxation_suggestions/strategy_relaxation_suggestions.csv",
    near_miss_strict_gap_csv: str = "reports/near_miss_strict_gap/near_miss_strict_gap.csv",
    shadow_scan_universe_csv: str = "reports/shadow_scan_universe/shadow_scan_universe.csv",
    testnet_dry_run_readiness_report_json: str = "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json",
    output_dir: str = "reports/shadow_observation_experiments",
) -> dict[str, Any]:
    suggestion_rows = read_csv_rows(Path(strategy_relaxation_suggestions_csv))
    gap_rows = read_csv_rows(Path(near_miss_strict_gap_csv))
    universe_rows = read_csv_rows(Path(shadow_scan_universe_csv))
    readiness = _read_json(Path(testnet_dry_run_readiness_report_json))

    universe_index = {
        str(row.get("strategy_key", "")).strip(): row
        for row in universe_rows
        if str(row.get("strategy_key", "")).strip()
    }
    gap_index: dict[str, list[dict[str, Any]]] = {}
    for row in gap_rows:
        key = str(row.get("strategy_key", "")).strip()
        if key:
            gap_index.setdefault(key, []).append(row)

    rows: list[dict[str, Any]] = []
    for suggestion in suggestion_rows:
        strategy_key = str(suggestion.get("strategy_key", "")).strip()
        if not strategy_key:
            continue
        universe = universe_index.get(strategy_key, {})
        symbol = str(suggestion.get("symbol", universe.get("symbol", ""))).strip().upper()
        side = str(suggestion.get("side", universe.get("side", ""))).strip().upper()
        timeframe = str(suggestion.get("timeframe", universe.get("timeframe", "5m"))).strip() or "5m"
        max_cands = int(to_float_nan(universe.get("max_shadow_candidates_per_day")) if str(universe.get("max_shadow_candidates_per_day", "")).strip() else 10)
        if max_cands <= 0:
            max_cands = 10
        verdict = str(suggestion.get("suggestion_verdict", "INSUFFICIENT_DATA")).strip().upper()
        experiment_status = "WATCH_ONLY"
        if verdict == "INSUFFICIENT_DATA":
            experiment_status = "INSUFFICIENT_DATA"
        elif verdict == "REJECT":
            experiment_status = "WATCH_ONLY"
        risk_level = str(suggestion.get("risk_level", "LOW_CONFIDENCE")).strip().upper() or "LOW_CONFIDENCE"
        base_reason = str(suggestion.get("reason", "")).strip() or "need_more_observation_samples"

        _add_experiment(
            rows,
            {
                "experiment_id": f"exp_{strategy_key}_baseline_strict",
                "strategy_key": strategy_key,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "experiment_type": "BASELINE_STRICT",
                "collector_mode": "strict",
                "min_trend_score": 60.0,
                "min_breakout_score": 60.0,
                "min_risk_reward": 1.0,
                "near_miss_threshold": 0.8,
                "allow_near_miss": False,
                "sample_target": 20,
                "max_candidates_per_day": max_cands,
                "allowed_mode": "SHADOW_ONLY",
                "submit_permission": "NO_SUBMIT",
                "experiment_status": experiment_status,
                "risk_level": risk_level,
                "reason": base_reason,
            },
        )

        # Always produce conservative observation experiment to collect evidence.
        _add_experiment(
            rows,
            {
                "experiment_id": f"exp_{strategy_key}_relax_near_miss",
                "strategy_key": strategy_key,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "experiment_type": "RELAX_NEAR_MISS",
                "collector_mode": "observation",
                "min_trend_score": 60.0,
                "min_breakout_score": 60.0,
                "min_risk_reward": 1.0,
                "near_miss_threshold": 0.75,
                "allow_near_miss": True,
                "sample_target": 20,
                "max_candidates_per_day": max_cands,
                "allowed_mode": "SHADOW_ONLY",
                "submit_permission": "NO_SUBMIT",
                "experiment_status": experiment_status,
                "risk_level": "LOW_CONFIDENCE",
                "reason": "collect_more_observation_samples",
            },
        )

        s_type = str(suggestion.get("suggestion_type", "")).strip().upper()
        if s_type == "RELAX_MIN_TREND_SCORE":
            _add_experiment(
                rows,
                {
                    "experiment_id": f"exp_{strategy_key}_relax_trend",
                    "strategy_key": strategy_key,
                    "symbol": symbol,
                    "side": side,
                    "timeframe": timeframe,
                    "experiment_type": "RELAX_TREND",
                    "collector_mode": "observation",
                    "min_trend_score": 55.0,
                    "min_breakout_score": 60.0,
                    "min_risk_reward": 1.0,
                    "near_miss_threshold": 0.8,
                    "allow_near_miss": True,
                    "sample_target": 20,
                    "max_candidates_per_day": max_cands,
                    "allowed_mode": "SHADOW_ONLY",
                    "submit_permission": "NO_SUBMIT",
                    "experiment_status": experiment_status,
                    "risk_level": risk_level,
                    "reason": base_reason,
                },
            )
        if s_type == "RELAX_MIN_BREAKOUT_SCORE":
            _add_experiment(
                rows,
                {
                    "experiment_id": f"exp_{strategy_key}_relax_breakout",
                    "strategy_key": strategy_key,
                    "symbol": symbol,
                    "side": side,
                    "timeframe": timeframe,
                    "experiment_type": "RELAX_BREAKOUT",
                    "collector_mode": "observation",
                    "min_trend_score": 60.0,
                    "min_breakout_score": 55.0,
                    "min_risk_reward": 1.0,
                    "near_miss_threshold": 0.8,
                    "allow_near_miss": True,
                    "sample_target": 20,
                    "max_candidates_per_day": max_cands,
                    "allowed_mode": "SHADOW_ONLY",
                    "submit_permission": "NO_SUBMIT",
                    "experiment_status": experiment_status,
                    "risk_level": risk_level,
                    "reason": base_reason,
                },
            )
        if s_type == "RELAX_MIN_RISK_REWARD":
            _add_experiment(
                rows,
                {
                    "experiment_id": f"exp_{strategy_key}_relax_rr",
                    "strategy_key": strategy_key,
                    "symbol": symbol,
                    "side": side,
                    "timeframe": timeframe,
                    "experiment_type": "RELAX_RISK_REWARD",
                    "collector_mode": "observation",
                    "min_trend_score": 60.0,
                    "min_breakout_score": 60.0,
                    "min_risk_reward": 0.9,
                    "near_miss_threshold": 0.8,
                    "allow_near_miss": True,
                    "sample_target": 20,
                    "max_candidates_per_day": max_cands,
                    "allowed_mode": "SHADOW_ONLY",
                    "submit_permission": "NO_SUBMIT",
                    "experiment_status": experiment_status,
                    "risk_level": risk_level,
                    "reason": base_reason,
                },
            )

    # Fallback when suggestions missing: still create baseline rows from universe.
    if not rows:
        for universe in universe_rows:
            strategy_key = str(universe.get("strategy_key", "")).strip()
            if not strategy_key:
                continue
            symbol = str(universe.get("symbol", "")).strip().upper()
            side = str(universe.get("side", "")).strip().upper()
            timeframe = str(universe.get("timeframe", "5m")).strip() or "5m"
            max_cands = int(to_float_nan(universe.get("max_shadow_candidates_per_day")) if str(universe.get("max_shadow_candidates_per_day", "")).strip() else 10)
            if max_cands <= 0:
                max_cands = 10
            _add_experiment(
                rows,
                {
                    "experiment_id": f"exp_{strategy_key}_baseline_strict",
                    "strategy_key": strategy_key,
                    "symbol": symbol,
                    "side": side,
                    "timeframe": timeframe,
                    "experiment_type": "BASELINE_STRICT",
                    "collector_mode": "strict",
                    "min_trend_score": 60.0,
                    "min_breakout_score": 60.0,
                    "min_risk_reward": 1.0,
                    "near_miss_threshold": 0.8,
                    "allow_near_miss": False,
                    "sample_target": 20,
                    "max_candidates_per_day": max_cands,
                    "allowed_mode": "SHADOW_ONLY",
                    "submit_permission": "NO_SUBMIT",
                    "experiment_status": "INSUFFICIENT_DATA",
                    "risk_level": "LOW_CONFIDENCE",
                    "reason": "missing_relaxation_suggestions",
                },
            )

    rows.sort(key=lambda item: (str(item.get("strategy_key", "")), str(item.get("experiment_type", ""))))

    # Conservative safety rails, no submit.
    for row in rows:
        row["allowed_mode"] = "SHADOW_ONLY"
        row["submit_permission"] = "NO_SUBMIT"
        row["reason"] = str(row.get("reason", "")).strip() or "collect_more_observation_samples"

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "experiment_matrix.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    readiness_verdict = str(readiness.get("final_verdict", readiness.get("readiness_verdict", "UNKNOWN"))).strip().upper()
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": "PASS" if rows else "PARTIAL",
        "experiment_count": len(rows),
        "watch_only_count": sum(1 for row in rows if str(row.get("experiment_status", "")).strip().upper() == "WATCH_ONLY"),
        "insufficient_data_count": sum(
            1 for row in rows if str(row.get("experiment_status", "")).strip().upper() == "INSUFFICIENT_DATA"
        ),
        "allowed_mode": "SHADOW_ONLY",
        "submit_allowed": False,
        "real_submit_allowed": False,
        "testnet_dry_run_readiness_verdict": readiness_verdict,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow Observation Experiment Matrix",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- experiment_count: {summary['experiment_count']}",
        f"- watch_only_count: {summary['watch_only_count']}",
        f"- insufficient_data_count: {summary['insufficient_data_count']}",
        "- allowed_mode: SHADOW_ONLY",
        "- submit_permission: NO_SUBMIT",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate shadow observation experiment matrix from relaxation suggestions")
    parser.add_argument("--strategy-relaxation-suggestions-csv", default="reports/strategy_relaxation_suggestions/strategy_relaxation_suggestions.csv")
    parser.add_argument("--near-miss-strict-gap-csv", default="reports/near_miss_strict_gap/near_miss_strict_gap.csv")
    parser.add_argument("--shadow-scan-universe-csv", default="reports/shadow_scan_universe/shadow_scan_universe.csv")
    parser.add_argument(
        "--testnet-dry-run-readiness-report-json",
        default="reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json",
    )
    parser.add_argument("--output-dir", default="reports/shadow_observation_experiments")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_shadow_observation_experiment_matrix(
        strategy_relaxation_suggestions_csv=str(
            args.strategy_relaxation_suggestions_csv or "reports/strategy_relaxation_suggestions/strategy_relaxation_suggestions.csv"
        ),
        near_miss_strict_gap_csv=str(args.near_miss_strict_gap_csv or "reports/near_miss_strict_gap/near_miss_strict_gap.csv"),
        shadow_scan_universe_csv=str(args.shadow_scan_universe_csv or "reports/shadow_scan_universe/shadow_scan_universe.csv"),
        testnet_dry_run_readiness_report_json=str(
            args.testnet_dry_run_readiness_report_json
            or "reports/testnet_dry_run_readiness/testnet_dry_run_readiness_report.json"
        ),
        output_dir=str(args.output_dir or "reports/shadow_observation_experiments"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"experiment_count={result.get('experiment_count', 0)}")


if __name__ == "__main__":
    main()
