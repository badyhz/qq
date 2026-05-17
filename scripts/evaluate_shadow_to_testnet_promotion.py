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
    "real_sample_count",
    "shadow_sample_count",
    "weighted_sample_count",
    "real_avg_r",
    "shadow_avg_r",
    "weighted_avg_r",
    "sample_confidence_level",
    "system_health_verdict",
    "reset_readiness_verdict",
    "promotion_decision",
    "allowed_action",
    "submit_permission",
    "risk_level",
    "reason",
]


def _decide_promotion(
    *,
    real_count: int,
    shadow_count: int,
    weighted_count: float,
    shadow_avg_r: float,
    weighted_avg_r: float,
    system_health_verdict: str,
    reset_readiness_verdict: str,
    can_submit_after_reset: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    decision = "UNKNOWN"
    allowed_action = "SHADOW_ONLY"
    submit_permission = "NO_TESTNET_SUBMIT"
    risk_level = "UNKNOWN"

    if shadow_count >= 20 and math.isfinite(shadow_avg_r) and shadow_avg_r < -0.2:
        decision = "REJECT_SHADOW_STRATEGY"
        allowed_action = "BLOCKED"
        submit_permission = "NO_TESTNET_SUBMIT"
        risk_level = "NEGATIVE_SHADOW_EDGE"
        reasons.append("shadow_expectancy_negative")
    elif (not math.isfinite(weighted_count)) or weighted_count < 5 or shadow_count <= 0:
        decision = "KEEP_SHADOW_ONLY"
        allowed_action = "SHADOW_ONLY"
        submit_permission = "NO_TESTNET_SUBMIT"
        risk_level = "LOW_SAMPLE"
        reasons.append("need_more_shadow_samples")
    elif (
        weighted_count >= 5
        and math.isfinite(weighted_avg_r)
        and weighted_avg_r > 0
        and system_health_verdict == "PASS"
        and real_count < 3
    ):
        decision = "ALLOW_TESTNET_DRY_RUN"
        allowed_action = "TESTNET_DRY_RUN_ONLY"
        submit_permission = "NO_TESTNET_SUBMIT"
        risk_level = "LOW_REAL_SAMPLE"
        reasons.append("weighted_positive_but_real_too_small")
    elif (
        real_count >= 3
        and math.isfinite(weighted_count)
        and weighted_count >= 20
        and math.isfinite(weighted_avg_r)
        and weighted_avg_r > 0.2
        and system_health_verdict == "PASS"
        and reset_readiness_verdict != "FAIL"
        and can_submit_after_reset
    ):
        decision = "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET"
        allowed_action = "TESTNET_SMALL_SIZE_ALLOWED_AFTER_RESET"
        submit_permission = "TESTNET_SUBMIT_ALLOWED_AFTER_RESET"
        risk_level = "CONTROLLED"
        reasons.append("meets_shadow_to_testnet_threshold")
    elif real_count < 3:
        decision = "REQUIRE_MORE_REAL_SAMPLES"
        allowed_action = "TESTNET_DRY_RUN_ONLY"
        submit_permission = "NO_TESTNET_SUBMIT"
        risk_level = "LOW_REAL_SAMPLE"
        reasons.append("require_more_real_samples")
    else:
        decision = "KEEP_SHADOW_ONLY"
        allowed_action = "SHADOW_ONLY"
        submit_permission = "NO_TESTNET_SUBMIT"
        risk_level = "CONSERVATIVE"
        reasons.append("default_shadow_collection")

    if real_count == 0 and decision == "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET":
        decision = "ALLOW_TESTNET_DRY_RUN"
        allowed_action = "TESTNET_DRY_RUN_ONLY"
        submit_permission = "NO_TESTNET_SUBMIT"
        reasons.append("no_real_samples_cap_dry_run_only")
    if real_count < 3 and decision == "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET":
        decision = "ALLOW_TESTNET_DRY_RUN"
        allowed_action = "TESTNET_DRY_RUN_ONLY"
        submit_permission = "NO_TESTNET_SUBMIT"
        reasons.append("real_sample_count_below_three_cap_dry_run_only")
    if shadow_count >= 50 and real_count == 0 and decision == "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET":
        decision = "ALLOW_TESTNET_DRY_RUN"
        allowed_action = "TESTNET_DRY_RUN_ONLY"
        submit_permission = "NO_TESTNET_SUBMIT"
        reasons.append("shadow_only_high_count_cap_dry_run")

    return {
        "promotion_decision": decision,
        "allowed_action": allowed_action,
        "submit_permission": submit_permission,
        "risk_level": risk_level,
        "reason": ";".join(sorted(set(reasons))) if reasons else "ok",
    }


def evaluate_shadow_to_testnet_promotion(
    *,
    real_vs_shadow_csv: str = "reports/real_vs_shadow_samples/real_vs_shadow_samples.csv",
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    testnet_reset_readiness_json: str = "reports/testnet_reset_readiness/testnet_reset_readiness.json",
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    output_dir: str = "reports/shadow_to_testnet_promotion",
) -> dict[str, Any]:
    rvss_rows = read_csv_rows(Path(real_vs_shadow_csv))
    strategy_rows = read_csv_rows(Path(strategy_candidate_csv))
    try:
        reset_payload = json.loads(Path(testnet_reset_readiness_json).read_text(encoding="utf-8")) if Path(testnet_reset_readiness_json).exists() else {}
    except (OSError, json.JSONDecodeError):
        reset_payload = {}
    try:
        health_payload = json.loads(Path(system_health_json).read_text(encoding="utf-8")) if Path(system_health_json).exists() else {}
    except (OSError, json.JSONDecodeError):
        health_payload = {}

    strategy_index = {
        str(row.get("strategy_key", "")).strip(): row
        for row in strategy_rows
        if str(row.get("strategy_key", "")).strip()
    }

    system_health_verdict = str(health_payload.get("final_verdict", "MISSING")).strip().upper() or "MISSING"
    reset_readiness_verdict = str(reset_payload.get("readiness_verdict", "MISSING")).strip().upper() or "MISSING"
    can_submit_after_reset = bool(reset_payload.get("can_submit_after_reset", False))

    rows: list[dict[str, Any]] = []
    for row in rvss_rows:
        strategy_key = str(row.get("strategy_key", "")).strip()
        candidate_row = strategy_index.get(strategy_key, {})
        symbol = str(row.get("symbol", "")).strip().upper()
        side = str(row.get("side", "")).strip().upper() or "LONG"
        timeframe = str(row.get("timeframe", "5m")).strip() or "5m"
        real_count = int(to_float_nan(row.get("real_sample_count")) if math.isfinite(to_float_nan(row.get("real_sample_count"))) else 0)
        shadow_count = int(to_float_nan(row.get("shadow_sample_count")) if math.isfinite(to_float_nan(row.get("shadow_sample_count"))) else 0)
        weighted_count = to_float_nan(row.get("weighted_sample_count"))
        real_avg_r = to_float_nan(row.get("real_avg_r"))
        shadow_avg_r = to_float_nan(row.get("shadow_avg_r"))
        weighted_avg_r = to_float_nan(row.get("weighted_avg_r"))
        confidence_level = str(candidate_row.get("sample_confidence_level", row.get("confidence_level", "UNKNOWN"))).strip().upper() or "UNKNOWN"

        result = _decide_promotion(
            real_count=real_count,
            shadow_count=shadow_count,
            weighted_count=weighted_count,
            shadow_avg_r=shadow_avg_r,
            weighted_avg_r=weighted_avg_r,
            system_health_verdict=system_health_verdict,
            reset_readiness_verdict=reset_readiness_verdict,
            can_submit_after_reset=can_submit_after_reset,
        )

        rows.append(
            {
                "strategy_key": strategy_key,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "real_sample_count": real_count,
                "shadow_sample_count": shadow_count,
                "weighted_sample_count": round(weighted_count, 8) if math.isfinite(weighted_count) else float("nan"),
                "real_avg_r": round(real_avg_r, 8) if math.isfinite(real_avg_r) else float("nan"),
                "shadow_avg_r": round(shadow_avg_r, 8) if math.isfinite(shadow_avg_r) else float("nan"),
                "weighted_avg_r": round(weighted_avg_r, 8) if math.isfinite(weighted_avg_r) else float("nan"),
                "sample_confidence_level": confidence_level,
                "system_health_verdict": system_health_verdict,
                "reset_readiness_verdict": reset_readiness_verdict,
                "promotion_decision": result["promotion_decision"],
                "allowed_action": result["allowed_action"],
                "submit_permission": result["submit_permission"],
                "risk_level": result["risk_level"],
                "reason": result["reason"],
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "shadow_to_testnet_promotion.csv"
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
        "strategy_count": len(rows),
        "keep_shadow_only_count": sum(1 for row in rows if str(row.get("promotion_decision", "")).upper() == "KEEP_SHADOW_ONLY"),
        "allow_dry_run_count": sum(1 for row in rows if str(row.get("promotion_decision", "")).upper() == "ALLOW_TESTNET_DRY_RUN"),
        "allow_small_size_count": sum(
            1 for row in rows if str(row.get("promotion_decision", "")).upper() == "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET"
        ),
        "reject_count": sum(1 for row in rows if str(row.get("promotion_decision", "")).upper() == "REJECT_SHADOW_STRATEGY"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["final_verdict"] = "PASS" if len(rows) > 0 else "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Shadow To Testnet Promotion Summary",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- strategy_count: {summary['strategy_count']}",
        f"- keep_shadow_only_count: {summary['keep_shadow_only_count']}",
        f"- allow_dry_run_count: {summary['allow_dry_run_count']}",
        f"- allow_small_size_count: {summary['allow_small_size_count']}",
        f"- reject_count: {summary['reject_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate shadow-to-testnet promotion readiness")
    parser.add_argument("--real-vs-shadow-csv", default="reports/real_vs_shadow_samples/real_vs_shadow_samples.csv")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--testnet-reset-readiness-json", default="reports/testnet_reset_readiness/testnet_reset_readiness.json")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--output-dir", default="reports/shadow_to_testnet_promotion")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = evaluate_shadow_to_testnet_promotion(
        real_vs_shadow_csv=str(args.real_vs_shadow_csv or "reports/real_vs_shadow_samples/real_vs_shadow_samples.csv"),
        strategy_candidate_csv=str(args.strategy_candidate_csv or "reports/strategy_candidate_score/strategy_candidate_score.csv"),
        testnet_reset_readiness_json=str(args.testnet_reset_readiness_json or "reports/testnet_reset_readiness/testnet_reset_readiness.json"),
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        output_dir=str(args.output_dir or "reports/shadow_to_testnet_promotion"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"strategy_count={result.get('strategy_count', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
