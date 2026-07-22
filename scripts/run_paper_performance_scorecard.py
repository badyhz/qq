"""Phase 10H Paper Performance Scorecard runner.

Reads quarantine output, computes metrics from clean positions only.
No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.paper_performance_metrics import (
    compute_performance, PerformanceScorecard,
)
from core.paper_trading.paper_position import (
    load_canonical_positions, filter_canonical_closed_clean,
    classify_quarantine_status, classify_source_eligibility,
    load_canonical_closed_clean_positions, evaluate_canonical_eligibility,
    load_overlap_exclusion_manifest,
)
from core.paper_trading.net_friction import (
    FRICTION_MODEL_VERSION,
    aggregate_net_metrics,
    assess_position_friction,
    assumptions_hash,
    is_p1_03_population_member,
    is_p1_03_trusted,
    load_assumptions,
    validate_assumptions,
)

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")

SAFETY_FLAGS = [
    "PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT",
    "STATS_FROM_CLEAN_POSITIONS_ONLY",
]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default_quarantine_path(date_str: str) -> str:
    return os.path.join(REPORT_DIR, f"{date_str}_paper_positions_quarantine.json")


def render_markdown(
    scorecard: PerformanceScorecard,
    net_friction: dict | None = None,
) -> str:
    gm = scorecard.global_metrics
    lines = [
        "# Paper Performance Scorecard",
        "",
        f"**Date:** {scorecard.date}",
        "",
        "## Summary",
        "",
        "纸面交易表现统计",
        "",
        "说明：",
        "本报告只统计 clean positions。",
        "legacy / quarantine positions 已排除。",
        "",
        "当前状态：",
        f"- clean positions: {gm.clean_positions}",
        f"- excluded positions: {gm.excluded_positions}",
        f"- closed clean positions: {gm.closed_positions}",
        f"- sample_status: {gm.sample_status}",
        "",
    ]

    if gm.sample_status == "INSUFFICIENT_CLOSED_SAMPLE":
        lines.extend([
            "结论：",
            "样本不足，只能继续观察，不允许进入 testnet/live。",
            "",
        ])
    elif gm.sample_status == "LOW_SAMPLE_SIZE":
        lines.extend([
            "结论：",
            "样本偏少，继续 shadow 收集，暂不进入 testnet/live。",
            "",
        ])
    else:
        lines.extend([
            "结论：",
            "样本可评估，详见策略评分。",
            "",
        ])

    lines.extend([
        "## Global Metrics",
        "",
        f"- total_positions: {gm.total_positions}",
        f"- clean_positions: {gm.clean_positions}",
        f"- excluded_positions: {gm.excluded_positions}",
        f"- open_positions: {gm.open_positions}",
        f"- closed_positions: {gm.closed_positions}",
        f"- take_profit_hit: {gm.take_profit_hit}",
        f"- stop_loss_hit: {gm.stop_loss_hit}",
        f"- timeout_exit: {gm.timeout_exit}",
        f"- realized_pnl: {round(gm.realized_pnl, 8)}",
        f"- unrealized_pnl: {round(gm.unrealized_pnl, 8)}",
        f"- avg_r_multiple: {round(gm.avg_r_multiple, 4)}",
        f"- win_rate: {round(gm.win_rate, 4)}",
        f"- loss_rate: {round(gm.loss_rate, 4)}",
        f"- profit_factor: {round(gm.profit_factor, 4)}",
        f"- expectancy_r: {round(gm.expectancy_r, 4)}",
        f"- max_single_loss_r: {round(gm.max_single_loss_r, 4)}",
        f"- max_single_win_r: {round(gm.max_single_win_r, 4)}",
        f"- sample_status: {gm.sample_status}",
        "",
    ])

    if net_friction is not None:
        complete = net_friction.get("complete_metrics", {})
        trusted = net_friction.get("trusted_metrics", {})
        lines.extend([
            "## Gross / Net Friction Accounting",
            "",
            f"- friction_model_version: {net_friction.get('friction_model_version')}",
            f"- model_configuration_status: {net_friction.get('model_configuration_status')}",
            f"- assumptions_hash: {net_friction.get('friction_assumptions_hash')}",
            f"- gross_profit_factor: {net_friction.get('gross_profit_factor')}",
            f"- net_profit_factor: {complete.get('net_profit_factor')}",
            f"- gross_expectancy_r: {net_friction.get('gross_expectancy_r')}",
            f"- net_expectancy_r: {complete.get('net_expectancy_r')}",
            f"- mean_friction_r: {complete.get('mean_friction_r')}",
            f"- median_friction_r: {complete.get('median_friction_r')}",
            f"- p1_03_trusted_closed: {trusted.get('net_complete_closed_count', 0)}",
            "",
        ])

    # Strategy Scorecard
    sc_list = scorecard.strategy_scorecards
    if sc_list:
        lines.extend(["## Strategy Scorecard", ""])
        lines.append("| strategy | type | positions | closed | TP | SL | timeout | PnL | avg_R | win% | PF | exp_R | score | status |")
        lines.append("|----------|------|-----------|--------|----|----|---------|-----|-------|------|----|-------|-------|--------|")
        for sc in sc_list:
            lines.append(
                f"| {sc.strategy_id} | {sc.strategy_type} "
                f"| {sc.position_count} | {sc.closed_count} "
                f"| {sc.tp_count} | {sc.sl_count} | {sc.timeout_count} "
                f"| {round(sc.realized_pnl, 4)} | {round(sc.avg_r_multiple, 4)} "
                f"| {round(sc.win_rate * 100, 1)}% | {round(sc.profit_factor, 2)} "
                f"| {round(sc.expectancy_r, 4)} | {round(sc.strategy_score, 4)} "
                f"| {sc.strategy_status} |"
            )
        lines.append("")

    # Excluded Legacy Records
    excluded = scorecard.excluded_positions
    if excluded:
        lines.extend(["## Excluded Legacy Records", ""])
        lines.append(f"Total excluded: {len(excluded)}")
        lines.append("")
        for p in excluded:
            reasons = ", ".join(p.get("quarantine_reasons", []))
            lines.append(f"- {p.get('position_id', '')} | {p.get('symbol', '')} | {p.get('status', '')} | {reasons}")
        lines.append("")

    # Open Positions
    open_pos = [p for p in scorecard.clean_positions if p.get("status") == "OPEN"]
    if open_pos:
        lines.extend(["## Open Positions", ""])
        for p in open_pos:
            lines.append(
                f"- {p.get('strategy_id', '')} | {p.get('symbol', '')} "
                f"| {p.get('side', '')} | entry={p.get('entry_price', 0)} "
                f"| SL={p.get('stop_loss', 0)} | TP={p.get('take_profit', 0)}"
            )
        lines.append("")

    lines.extend([
        "## Safety",
        "",
        "- Paper-only: YES",
        "- Shadow-only: YES",
        "- No order: YES",
        "- No account: YES",
        "- No testnet/live: YES",
        "- No secret: YES",
        "- Stats from clean positions only: YES",
        "",
    ])
    return "\n".join(lines)


def render_csv(scorecard: PerformanceScorecard) -> list[dict[str, str]]:
    rows = []
    for sc in scorecard.strategy_scorecards:
        rows.append({
            "strategy_id": sc.strategy_id,
            "strategy_type": sc.strategy_type,
            "symbol_count": str(sc.symbol_count),
            "position_count": str(sc.position_count),
            "open_count": str(sc.open_count),
            "closed_count": str(sc.closed_count),
            "tp_count": str(sc.tp_count),
            "sl_count": str(sc.sl_count),
            "timeout_count": str(sc.timeout_count),
            "realized_pnl": str(round(sc.realized_pnl, 8)),
            "unrealized_pnl": str(round(sc.unrealized_pnl, 8)),
            "avg_r_multiple": str(round(sc.avg_r_multiple, 4)),
            "win_rate": str(round(sc.win_rate, 4)),
            "profit_factor": str(round(sc.profit_factor, 4)),
            "expectancy_r": str(round(sc.expectancy_r, 4)),
            "sample_status": sc.sample_status,
            "strategy_score": str(round(sc.strategy_score, 4)),
            "strategy_status": sc.strategy_status,
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description="Phase 10H paper performance scorecard")
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--input-file", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=REPORT_DIR)
    parser.add_argument("--friction-config", type=str, default=None)
    args = parser.parse_args()

    date_str = args.date or _today_str()

    # Use unified entry point for consistent eligibility
    eligible_positions, all_positions, diag = load_canonical_closed_clean_positions(args.output_dir)
    if not all_positions:
        print(f"No positions found in ledger files at {args.output_dir}")
        return 1

    # Check for fatal errors - fail closed
    if diag.get("fatal_errors"):
        print(f"FATAL: Accounting errors detected, cannot generate scorecard:")
        for err in diag["fatal_errors"]:
            print(f"  - {err}")
        return 1

    # Use eligible_positions directly - no re-evaluation
    # Tag all positions for display purposes only
    eligible_set = {id(p) for p in eligible_positions}
    for p in all_positions:
        p["excluded_from_performance_stats"] = id(p) not in eligible_set

    positions = all_positions
    print(f"Loaded {len(positions)} canonical positions from ledger files")
    print(f"  raw records: {diag.get('raw_records', '?')}")
    print(f"  eligible_closed_clean: {diag.get('eligible_closed_clean', '?')}")
    print(f"  explicit_clean: {diag.get('explicit_clean', '?')}")
    print(f"  derived_clean: {diag.get('derived_clean', '?')}")
    print(f"  exclusions: {diag.get('exclusions', '?')}")

    clean_count = len(eligible_positions)
    excluded_count = diag.get("exclusions", {}).get("total", 0)
    print(f"Eligible: {clean_count}, Excluded: {excluded_count}")

    # Compute performance on eligible positions only
    # Mark eligible positions as clean for compute_performance
    for p in eligible_positions:
        p["excluded_from_performance_stats"] = False

    scorecard = compute_performance(eligible_positions, date_str)
    scorecard_dict = scorecard.to_dict()

    # Use the same eligible count as the gate
    cumulative_closed = len(eligible_positions)
    scorecard_dict["cumulative_closed_clean"] = cumulative_closed
    scorecard_dict["raw_canonical_closed"] = diag.get("raw_canonical_closed", 0)
    scorecard_dict["excluded_overlap_closed"] = diag.get("excluded_overlap_closed", 0)
    scorecard_dict["eligible_closed"] = len(eligible_positions)
    scorecard_dict["trusted_cohort_closed"] = diag.get("trusted_cohort_closed", 0)
    scorecard_dict["trusted_cohort_start_at"] = diag.get("trusted_cohort_start_at")
    scorecard_dict["trusted_cohort_rule_version"] = diag.get("trusted_cohort_rule_version")
    scorecard_dict["diagnostics"] = diag

    friction_config = None
    config_errors: list[str] = []
    if args.friction_config:
        try:
            friction_config = load_assumptions(args.friction_config)
            config_errors = validate_assumptions(friction_config)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            config_errors = [str(exc)]
    manifest = None
    try:
        manifest = load_overlap_exclusion_manifest(args.output_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        config_errors.append(f"activation manifest: {exc}")
    assessments = (
        [assess_position_friction(position, friction_config) for position in eligible_positions]
        if friction_config is not None else []
    )
    # Preserve distinct historical interpretations in the existing derived
    # Scorecard artifact.  Same identity is a no-op; changed assumptions append
    # a new identity instead of silently replacing the prior assessment.
    scorecard_json_path = os.path.join(
        args.output_dir, f"{date_str}_paper_performance_scorecard.json",
    )
    prior_assessments: list[dict] = []
    try:
        with open(scorecard_json_path) as handle:
            previous_scorecard = json.load(handle)
        candidate_prior = previous_scorecard.get("net_friction", {}).get("assessments", [])
        if isinstance(candidate_prior, list):
            prior_assessments = [row for row in candidate_prior if isinstance(row, dict)]
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    assessment_versions = {
        row.get("assessment_id"): row
        for row in prior_assessments + assessments if row.get("assessment_id")
    }
    all_assessments = [assessment_versions[key] for key in sorted(assessment_versions)]
    trusted_population_assessments = [
        assessment for position, assessment in zip(eligible_positions, assessments)
        if is_p1_03_population_member(position, assessment, manifest)
    ]
    trusted_complete_count = sum(
        is_p1_03_trusted(position, assessment, manifest)
        for position, assessment in zip(eligible_positions, assessments)
    )
    complete_metrics = aggregate_net_metrics(assessments)
    trusted_metrics = aggregate_net_metrics(trusted_population_assessments)
    trusted_metrics["trusted_complete_assessment_count"] = trusted_complete_count
    integrity_rows = trusted_population_assessments
    integrity = {
        "symbol_mapping_invalid_count": sum(
            any("MAPPING" in error for error in row.get("errors", [])) for row in integrity_rows
        ),
        "notional_boundary_exceeded_count": sum(
            row.get("notional_boundary_result") == "EXCEEDED" for row in integrity_rows
        ),
        "funding_not_trusted_count": sum(
            row.get("funding_trusted") is False for row in integrity_rows
        ),
        "gap_evidence_incomplete_count": sum(
            row.get("lifecycle_status") == "STOP_LOSS_HIT"
            and row.get("friction_model_status") not in {"COMPLETE_ESTIMATED", "COMPLETE_OBSERVED"}
            for row in integrity_rows
        ),
    }
    net_friction = {
        "friction_model_version": FRICTION_MODEL_VERSION,
        "model_configuration_status": (
            "UNCONFIGURED" if friction_config is None and not config_errors
            else "INVALID" if config_errors else "CONFIGURED"
        ),
        "configuration_errors": config_errors,
        "friction_assumptions_hash": (
            assumptions_hash(friction_config) if friction_config is not None else None
        ),
        "friction_assumptions": friction_config,
        "gross_closed_count": scorecard.global_metrics.closed_positions,
        "gross_profit_factor": scorecard.global_metrics.profit_factor,
        "gross_expectancy_r": scorecard.global_metrics.expectancy_r,
        "gross_average_r": scorecard.global_metrics.avg_r_multiple,
        "complete_metrics": complete_metrics,
        "trusted_metrics": trusted_metrics,
        "integrity": integrity,
        "p1_03_activation": {
            key: (manifest or {}).get(key) for key in (
                "net_friction_trusted_cohort_start_at",
                "net_friction_trusted_cohort_rule_version",
                "net_friction_trusted_cohort_start_run_id",
                "net_friction_trusted_cohort_start_commit",
                "net_friction_model_version",
                "net_friction_assumptions_hash",
            )
        },
        "assessment_identity": "position_id+friction_model_version+friction_assumptions_hash",
        "current_assessment_ids": sorted(
            row["assessment_id"] for row in assessments if row.get("assessment_id")
        ),
        "assessments": all_assessments,
    }
    scorecard_dict["net_friction"] = net_friction

    os.makedirs(args.output_dir, exist_ok=True)

    # JSON
    json_path = os.path.join(args.output_dir, f"{date_str}_paper_performance_scorecard.json")
    with open(json_path, "w") as f:
        json.dump(scorecard_dict, f, indent=2)
    print(f"Scorecard JSON: {json_path}")

    # Markdown
    md_path = os.path.join(args.output_dir, f"{date_str}_paper_performance_scorecard.md")
    with open(md_path, "w") as f:
        f.write(render_markdown(scorecard, net_friction))
    print(f"Scorecard Markdown: {md_path}")

    # CSV
    csv_path = os.path.join(args.output_dir, f"{date_str}_strategy_scorecard.csv")
    csv_rows = render_csv(scorecard)
    if csv_rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"Scorecard CSV: {csv_path}")
    else:
        print(f"CSV: skipped (no strategy rows)")

    gm = scorecard.global_metrics
    print(f"\n=== Performance Scorecard Complete ===")
    print(f"Clean positions: {gm.clean_positions}")
    print(f"Excluded positions: {gm.excluded_positions}")
    print(f"Open: {gm.open_positions}")
    print(f"Closed: {gm.closed_positions}")
    print(f"Cumulative closed clean: {cumulative_closed}")
    print(f"TP: {gm.take_profit_hit}, SL: {gm.stop_loss_hit}, Timeout: {gm.timeout_exit}")
    print(f"Realized PnL: {round(gm.realized_pnl, 8)}")
    print(f"Avg R: {round(gm.avg_r_multiple, 4)}")
    print(f"Win rate: {round(gm.win_rate * 100, 1)}%")
    print(f"Profit factor: {round(gm.profit_factor, 4)}")
    print(f"Expectancy R: {round(gm.expectancy_r, 4)}")
    print(f"Net friction config: {net_friction['model_configuration_status']}")
    print(f"Net complete closed: {complete_metrics['net_complete_closed_count']}")
    print(f"P1-03 trusted closed: {trusted_metrics['net_complete_closed_count']}")
    print(f"Sample status: {gm.sample_status}")
    print(f"Strategies: {len(scorecard.strategy_scorecards)}")
    for sc in scorecard.strategy_scorecards:
        print(f"  {sc.strategy_id}: {sc.strategy_status} (score={round(sc.strategy_score, 4)}, closed={sc.closed_count})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
