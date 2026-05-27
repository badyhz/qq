#!/usr/bin/env python3
"""CLI: Full offline shadow research pipeline orchestrator.

Orchestrates: load fixtures -> generate plan -> materialize matrix ->
evaluate -> scorecard -> render reports -> build bundle.

All safety constraints enforced: release_hold=HOLD, no_live, no_submit,
no_exchange.  No network calls.  No live/submit/exchange integration.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_shadow_bundle_builder import build_bundle
from core.offline_shadow_evaluator import evaluate_experiment
from core.offline_shadow_fixture_loader import (
    load_outcomes,
    load_symbols,
    load_timeframes,
)
from core.offline_shadow_metric_engine import compute_run_metrics
from core.offline_shadow_plan_generator import (
    PARAM_GRIDS,
    TIMEFRAME_DEFS,
    generate_experiment_plan,
)
from core.offline_shadow_report_renderer import (
    render_report_html,
    render_report_json,
    render_report_markdown,
)
from core.offline_shadow_run_config import OfflineShadowRunConfig
from core.offline_shadow_scorecard import grade_run


def _plan_to_dict(plan) -> dict:
    """Convert OfflineShadowExperimentPlan to a JSON-serializable dict."""
    experiments = []
    for exp in plan.experiments:
        experiments.append({
            "experiment_id": exp.experiment_id,
            "symbol": exp.symbol.symbol,
            "base_asset": exp.symbol.base_asset,
            "quote_asset": exp.symbol.quote_asset,
            "exchange": exp.symbol.exchange,
            "timeframe": exp.timeframe.label,
            "timeframe_minutes": exp.timeframe.minutes,
            "window_id": exp.window.window_id,
            "window_type": exp.window.window_type,
            "window_start_index": exp.window.start_index,
            "window_end_index": exp.window.end_index,
            "param_id": exp.parameter_set.param_id,
            "param_label": exp.parameter_set.label,
            "entry_threshold": exp.parameter_set.entry_threshold,
            "exit_threshold": exp.parameter_set.exit_threshold,
            "stop_loss_r": exp.parameter_set.stop_loss_r,
            "take_profit_r": exp.parameter_set.take_profit_r,
            "max_hold_bars": exp.parameter_set.max_hold_bars,
            "min_sample_quality": exp.parameter_set.min_sample_quality,
            "safety": {
                "no_live": exp.safety_policy.no_live,
                "no_submit": exp.safety_policy.no_submit,
                "no_exchange": exp.safety_policy.no_exchange,
                "release_hold": exp.safety_policy.release_hold,
            },
        })
    return {
        "plan_id": plan.plan_id,
        "experiments": experiments,
        "run_config": {
            "config_id": plan.run_config.config_id,
            "symbols": list(plan.run_config.symbols),
            "timeframes": list(plan.run_config.timeframes),
            "windows": list(plan.run_config.windows),
            "param_grid": list(plan.run_config.param_grid),
            "fixture_dir": plan.run_config.fixture_dir,
            "output_dir": plan.run_config.output_dir,
        },
        "safety_policy": {
            "no_live": plan.safety_policy.no_live,
            "no_submit": plan.safety_policy.no_submit,
            "no_exchange": plan.safety_policy.no_exchange,
            "release_hold": plan.safety_policy.release_hold,
        },
    }


def _evaluate_plan(plan, fixture_dir: str) -> list[dict]:
    """Evaluate all experiments in a plan against fixture outcomes.

    For each experiment, loads the appropriate outcome file and computes
    metrics and scorecard.
    """
    results = []
    for exp in plan.experiments:
        sym = exp.symbol.symbol
        tf = exp.timeframe.label
        outcomes = load_outcomes(fixture_dir, sym, tf)
        metrics = compute_run_metrics(outcomes)

        run_grade = grade_run(metrics)

        results.append({
            "experiment_id": exp.experiment_id,
            "symbol": sym,
            "timeframe": tf,
            "param_label": exp.parameter_set.label,
            "window_id": exp.window.window_id,
            "window_type": exp.window.window_type,
            "metrics": metrics,
            "scorecard": {
                "grade": run_grade["grade"],
                "reason_codes": run_grade["reason_codes"],
                "blockers": run_grade["blockers"],
            },
        })
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run offline shadow research pipeline"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write all pipeline artifacts",
    )
    parser.add_argument(
        "--fixture-dir",
        required=True,
        help="Directory containing fixture data files",
    )
    parser.add_argument(
        "--symbols",
        default="BTCUSDT,ETHUSDT",
        help="Comma-separated symbols (default: BTCUSDT,ETHUSDT)",
    )
    parser.add_argument(
        "--timeframes",
        default="5m,15m",
        help="Comma-separated timeframes (default: 5m,15m)",
    )
    parser.add_argument(
        "--param-grid",
        default="conservative,balanced,aggressive",
        help="Comma-separated param grid labels (default: conservative,balanced,aggressive)",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    fixture_dir = args.fixture_dir
    symbols = [s.strip() for s in args.symbols.split(",")]
    timeframes = [t.strip() for t in args.timeframes.split(",")]
    param_grid = [p.strip() for p in args.param_grid.split(",")]

    # Validate inputs
    for sym in symbols:
        for tf in timeframes:
            outcome_path = Path(fixture_dir) / f"outcomes_{sym}_{tf}.json"
            if not outcome_path.exists():
                print(f"WARNING: missing {outcome_path}", file=sys.stderr)

    for tf in timeframes:
        if tf not in TIMEFRAME_DEFS:
            print(f"ERROR: unknown timeframe '{tf}', known: {list(TIMEFRAME_DEFS.keys())}", file=sys.stderr)
            return 1

    for pg in param_grid:
        if pg not in PARAM_GRIDS:
            print(f"ERROR: unknown param grid '{pg}', known: {list(PARAM_GRIDS.keys())}", file=sys.stderr)
            return 1

    # Step 1: Generate experiment plan
    print("Step 1: Generating experiment plan...")
    run_config = OfflineShadowRunConfig(
        config_id="pipeline_run",
        symbols=tuple(symbols),
        timeframes=tuple(timeframes),
        windows=("train",),
        param_grid=tuple(param_grid),
        fixture_dir=fixture_dir,
        output_dir=str(output_dir),
    )
    plan = generate_experiment_plan(run_config)
    print(f"  Generated {len(plan.experiments)} experiments")

    # Step 2: Evaluate all experiments
    print("Step 2: Evaluating experiments...")
    results = _evaluate_plan(plan, fixture_dir)
    print(f"  Evaluated {len(results)} experiments")

    # Step 3: Build scorecard summary
    print("Step 3: Building scorecard...")
    pass_count = sum(1 for r in results if r["scorecard"]["grade"] == "PASS")
    watch_count = sum(1 for r in results if r["scorecard"]["grade"] == "WATCH")
    reject_count = sum(1 for r in results if r["scorecard"]["grade"] == "REJECT")
    scorecard_data = {
        "scorecard_id": "pipeline_scorecard",
        "experiment_count": len(results),
        "pass_count": pass_count,
        "watch_count": watch_count,
        "reject_count": reject_count,
        "experiments": [
            {
                "experiment_id": r["experiment_id"],
                "symbol": r["symbol"],
                "timeframe": r["timeframe"],
                "param_label": r["param_label"],
                "grade": r["scorecard"]["grade"],
                "reason_codes": r["scorecard"]["reason_codes"],
            }
            for r in results
        ],
    }
    print(f"  PASS={pass_count} WATCH={watch_count} REJECT={reject_count}")

    # Step 4: Render reports
    print("Step 4: Rendering reports...")
    report_md = render_report_markdown(results)
    report_html_str = render_report_html(results)
    report_json_data = render_report_json(results)

    # Step 5: Build plan dict and matrix dict
    plan_dict = _plan_to_dict(plan)
    matrix_dict = {
        "plan_id": plan.plan_id,
        "fixture_dir": fixture_dir,
        "run_count": len(plan.experiments),
        "runs": [
            {
                "run_id": f"run_{exp.experiment_id}",
                "experiment_id": exp.experiment_id,
                "symbol": exp.symbol.symbol,
                "timeframe": exp.timeframe.label,
                "param_label": exp.parameter_set.label,
                "fixture_outcomes": f"outcomes_{exp.symbol.symbol}_{exp.timeframe.label}.json",
            }
            for exp in plan.experiments
        ],
    }

    # Step 6: Build bundle
    print("Step 5: Building artifact bundle...")
    bundle = build_bundle(
        plan_data=plan_dict,
        matrix_data=matrix_dict,
        results_data=results,
        scorecard_data=scorecard_data,
        report_markdown=report_md,
        report_html=report_html_str,
        report_json=report_json_data,
    )

    # Step 7: Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in bundle.items():
        (output_dir / name).write_text(content)

    # Verify
    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["release_hold"] == "HOLD"
    assert manifest["no_live"] is True
    assert manifest["no_submit"] is True
    assert manifest["no_exchange"] is True

    print(f"\nPipeline complete. Artifacts written to {output_dir}")
    print(f"  Total artifacts: {manifest['artifact_count']}")
    print(f"  Manifest artifacts: {len(manifest['artifacts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
