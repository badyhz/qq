from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_csv_rows, to_float_nan


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _pick_primary_strategy_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    best = rows[0]
    best_weight = to_float_nan(best.get("weighted_sample_count"))
    for row in rows[1:]:
        current = to_float_nan(row.get("weighted_sample_count"))
        if (not math.isfinite(best_weight)) and math.isfinite(current):
            best = row
            best_weight = current
            continue
        if math.isfinite(current) and current > best_weight:
            best = row
            best_weight = current
    return best


def generate_testnet_dry_run_readiness_v2(
    *,
    kline_backfill_summary_json: str = "reports/kline_cache_backfill/summary.json",
    shadow_collection_summary_json: str = "reports/shadow_candidate_collection/summary.json",
    shadow_outcomes_summary_json: str = "reports/shadow_candidate_outcomes/summary.json",
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    real_vs_shadow_csv: str = "reports/real_vs_shadow_samples/real_vs_shadow_samples.csv",
    shadow_to_testnet_promotion_csv: str = "reports/shadow_to_testnet_promotion/shadow_to_testnet_promotion.csv",
    sample_collection_tracker_csv: str = "reports/sample_collection_tracker/sample_collection_tracker.csv",
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    convergence_summary_json: str = "reports/remediation_gap_convergence/summary.json",
    sample_targets_summary_json: str = "reports/shadow_sample_targets/summary.json",
    output_dir: str = "reports/testnet_dry_run_readiness_v2",
) -> dict[str, Any]:
    kline_summary = _read_json(Path(kline_backfill_summary_json))
    shadow_collect = _read_json(Path(shadow_collection_summary_json))
    shadow_outcomes = _read_json(Path(shadow_outcomes_summary_json))
    strategy_rows = read_csv_rows(Path(strategy_candidate_csv))
    rvss_rows = read_csv_rows(Path(real_vs_shadow_csv))
    promotion_rows = read_csv_rows(Path(shadow_to_testnet_promotion_csv))
    tracker_rows = read_csv_rows(Path(sample_collection_tracker_csv))
    system_health = _read_json(Path(system_health_json))
    convergence = _read_json(Path(convergence_summary_json))
    sample_targets = _read_json(Path(sample_targets_summary_json))

    primary_strategy = _pick_primary_strategy_row(strategy_rows)
    primary_key = str(primary_strategy.get("strategy_key", "")).strip()
    if not primary_key and promotion_rows:
        primary_key = str(promotion_rows[0].get("strategy_key", "")).strip()

    promotion_index = {str(row.get("strategy_key", "")).strip(): row for row in promotion_rows if str(row.get("strategy_key", "")).strip()}
    tracker_index = {str(row.get("strategy_key", "")).strip(): row for row in tracker_rows if str(row.get("strategy_key", "")).strip()}
    rvss_index = {str(row.get("strategy_key", "")).strip(): row for row in rvss_rows if str(row.get("strategy_key", "")).strip()}
    promotion = promotion_index.get(primary_key, promotion_rows[0] if promotion_rows else {})
    tracker = tracker_index.get(primary_key, {})
    rvss = rvss_index.get(primary_key, {})

    total_written_raw = to_float_nan(kline_summary.get("total_written_bars"))
    if not math.isfinite(total_written_raw):
        total_written_raw = to_float_nan(kline_summary.get("written_bars_total"))
    total_written = int(total_written_raw) if math.isfinite(total_written_raw) else 0
    if not kline_summary:
        kline_cache_status = "MISSING"
    elif total_written > 0 and str(kline_summary.get("cache_write_verdict", "")).strip().upper() in {"PASS", "PARTIAL", ""}:
        kline_cache_status = "OK"
    elif bool(kline_summary.get("dry_run", False)):
        kline_cache_status = "PARTIAL"
    else:
        kline_cache_status = "PARTIAL"

    status_reason = str(shadow_collect.get("status_reason", "")).strip().lower()
    if status_reason == "missing_klines":
        shadow_collector_status = "MISSING_KLINES"
    elif status_reason in {"collected_shadow_candidates"}:
        shadow_collector_status = "RECOVERED"
    elif status_reason in {"no_new_shadow_candidates", "insufficient_signal_conditions"}:
        shadow_collector_status = "NO_SIGNAL"
    elif status_reason:
        shadow_collector_status = "UNKNOWN"
    else:
        shadow_collector_status = "UNKNOWN"

    shadow_sample_raw = to_float_nan(primary_strategy.get("shadow_sample_count"))
    if not math.isfinite(shadow_sample_raw):
        shadow_sample_raw = to_float_nan(rvss.get("shadow_sample_count"))
    shadow_sample_count = int(shadow_sample_raw) if math.isfinite(shadow_sample_raw) else 0
    weighted_sample_count = to_float_nan(primary_strategy.get("weighted_sample_count"))
    if not math.isfinite(weighted_sample_count):
        weighted_sample_count = to_float_nan(rvss.get("weighted_sample_count"))
    if not math.isfinite(weighted_sample_count):
        weighted_sample_count = to_float_nan(tracker.get("weighted_sample_count"))
    if not math.isfinite(weighted_sample_count):
        weighted_sample_count = 0.0

    sample_confidence_level = str(primary_strategy.get("sample_confidence_level", "")).strip().upper()
    if not sample_confidence_level:
        sample_confidence_level = str(tracker.get("weighted_confidence_level", "UNKNOWN")).strip().upper() or "UNKNOWN"

    system_health_verdict = str(system_health.get("final_verdict", "MISSING")).strip().upper() or "MISSING"
    promotion_decision = str(promotion.get("promotion_decision", "UNKNOWN")).strip().upper() or "UNKNOWN"

    # v2 enhancements: convergence and allocation checks
    convergence_verdict = str(convergence.get("final_verdict", "")).strip().upper() or "UNKNOWN"
    convergence_detected = bool(convergence.get("convergence_detected", False))
    current_sample_gap = int(convergence.get("current_sample_gap", 0) or 0)
    allocation_strategy = str(sample_targets.get("allocation_strategy", "")).strip() or "STANDARD"

    # Enhanced readiness criteria
    minimum_samples_met = weighted_sample_count >= 5.0
    convergence_met = convergence_verdict in {"CONVERGING", "CONVERGED"} or current_sample_gap < 10
    gap_closing = convergence_detected or current_sample_gap < 5

    allow_testnet_dry_run = bool(
        system_health_verdict == "PASS"
        and kline_cache_status == "OK"
        and shadow_collector_status != "MISSING_KLINES"
        and minimum_samples_met
        and promotion_decision in {"ALLOW_TESTNET_DRY_RUN", "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET"}
        and (convergence_met or gap_closing)
    )

    blocking_reasons: list[str] = []
    if system_health_verdict != "PASS":
        blocking_reasons.append("system_health_not_pass")
    if kline_cache_status != "OK":
        blocking_reasons.append("missing_klines")
    if shadow_collector_status == "MISSING_KLINES":
        blocking_reasons.append("shadow_collector_missing_klines")
    if not minimum_samples_met:
        blocking_reasons.append("sample_confidence_too_small")
    if shadow_sample_count <= 0:
        blocking_reasons.append("need_more_shadow_samples")
    if promotion_decision not in {"ALLOW_TESTNET_DRY_RUN", "ALLOW_TESTNET_SMALL_SIZE_AFTER_RESET"}:
        blocking_reasons.append("promotion_not_ready")
    if not convergence_met and not gap_closing:
        blocking_reasons.append("gap_not_converging")

    final_verdict = "READY_FOR_TESTNET_DRY_RUN" if allow_testnet_dry_run else "NOT_READY"
    allowed_actions = ["OBSERVE_ONLY", "SHADOW_ONLY"]
    if allow_testnet_dry_run:
        allowed_actions.append("TESTNET_DRY_RUN_ONLY_IF_GATE_ALLOWS")
    else:
        allowed_actions.append("TESTNET_DRY_RUN_BLOCKED")
    prohibited_actions = [
        "NO_REAL_SUBMIT",
        "NO_TESTNET_SUBMIT_WITHOUT_GATE",
        "NO_BYPASS_STRATEGY_GATE",
    ]

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_json = out_dir / "testnet_dry_run_readiness_v2_report.json"
    summary_md = out_dir / "summary.md"
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_verdict": final_verdict,
        "kline_cache_status": kline_cache_status,
        "shadow_collector_status": shadow_collector_status,
        "shadow_sample_count": shadow_sample_count,
        "weighted_sample_count": round(weighted_sample_count, 8),
        "sample_confidence_level": sample_confidence_level,
        "system_health_verdict": system_health_verdict,
        "shadow_to_testnet_promotion": promotion_decision,
        "convergence_verdict": convergence_verdict,
        "convergence_detected": convergence_detected,
        "current_sample_gap": current_sample_gap,
        "allocation_strategy": allocation_strategy,
        "allow_testnet_dry_run": bool(allow_testnet_dry_run),
        "allow_testnet_submit": False,
        "allow_real_submit": False,
        "blocking_reasons": sorted(set(blocking_reasons)),
        "allowed_actions": allowed_actions,
        "prohibited_actions": prohibited_actions,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Testnet Dry-Run Readiness v2",
        "",
        f"- final_verdict: {report['final_verdict']}",
        f"- kline_cache_status: {report['kline_cache_status']}",
        f"- shadow_collector_status: {report['shadow_collector_status']}",
        f"- shadow_sample_count: {report['shadow_sample_count']}",
        f"- weighted_sample_count: {report['weighted_sample_count']}",
        f"- sample_confidence_level: {report['sample_confidence_level']}",
        f"- system_health_verdict: {report['system_health_verdict']}",
        f"- shadow_to_testnet_promotion: {report['shadow_to_testnet_promotion']}",
        f"- convergence_verdict: {report['convergence_verdict']}",
        f"- convergence_detected: {report['convergence_detected']}",
        f"- current_sample_gap: {report['current_sample_gap']}",
        f"- allocation_strategy: {report['allocation_strategy']}",
        f"- allow_testnet_dry_run: {report['allow_testnet_dry_run']}",
        "- allow_testnet_submit: false",
        "- allow_real_submit: false",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate final readiness report v2 for entering testnet dry-run phase")
    parser.add_argument("--kline-backfill-summary-json", default="reports/kline_cache_backfill/summary.json")
    parser.add_argument("--shadow-collection-summary-json", default="reports/shadow_candidate_collection/summary.json")
    parser.add_argument("--shadow-outcomes-summary-json", default="reports/shadow_candidate_outcomes/summary.json")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--real-vs-shadow-csv", default="reports/real_vs_shadow_samples/real_vs_shadow_samples.csv")
    parser.add_argument("--shadow-to-testnet-promotion-csv", default="reports/shadow_to_testnet_promotion/shadow_to_testnet_promotion.csv")
    parser.add_argument("--sample-collection-tracker-csv", default="reports/sample_collection_tracker/sample_collection_tracker.csv")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--convergence-summary-json", default="reports/remediation_gap_convergence/summary.json")
    parser.add_argument("--sample-targets-summary-json", default="reports/shadow_sample_targets/summary.json")
    parser.add_argument("--output-dir", default="reports/testnet_dry_run_readiness_v2")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = generate_testnet_dry_run_readiness_v2(
        kline_backfill_summary_json=str(args.kline_backfill_summary_json or "reports/kline_cache_backfill/summary.json"),
        shadow_collection_summary_json=str(args.shadow_collection_summary_json or "reports/shadow_candidate_collection/summary.json"),
        shadow_outcomes_summary_json=str(args.shadow_outcomes_summary_json or "reports/shadow_candidate_outcomes/summary.json"),
        strategy_candidate_csv=str(args.strategy_candidate_csv or "reports/strategy_candidate_score/strategy_candidate_score.csv"),
        real_vs_shadow_csv=str(args.real_vs_shadow_csv or "reports/real_vs_shadow_samples/real_vs_shadow_samples.csv"),
        shadow_to_testnet_promotion_csv=str(args.shadow_to_testnet_promotion_csv or "reports/shadow_to_testnet_promotion/shadow_to_testnet_promotion.csv"),
        sample_collection_tracker_csv=str(args.sample_collection_tracker_csv or "reports/sample_collection_tracker/sample_collection_tracker.csv"),
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        convergence_summary_json=str(args.convergence_summary_json or "reports/remediation_gap_convergence/summary.json"),
        sample_targets_summary_json=str(args.sample_targets_summary_json or "reports/shadow_sample_targets/summary.json"),
        output_dir=str(args.output_dir or "reports/testnet_dry_run_readiness_v2"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"final_verdict={result.get('final_verdict', '')}")
    print(f"allow_testnet_dry_run={result.get('allow_testnet_dry_run', False)}")


if __name__ == "__main__":
    main()
