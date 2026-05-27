#!/usr/bin/env python3
"""Run multi-strategy research workbench — end-to-end pipeline.

Usage:
    python3 scripts/run_multi_strategy_research_workbench.py \
        --fixture-dir tests/fixtures/historical_backtest_lab \
        --output-dir /tmp/multi_strategy_research_workbench \
        --strategies breakout,mean_reversion,momentum,volatility_compression \
        --symbols BTCUSDT,ETHUSDT \
        --timeframes 5m,15m \
        --split-mode rolling \
        --search-budget 120 \
        --chunk-size 25

Safety: local only, no network, no exchange, no live, no submit.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.multi_strategy_comparison import compare_strategies, comparison_to_dict
from core.multi_strategy_evaluator import EvaluationResult, evaluate_matrix_row, evaluation_to_dict
from core.multi_strategy_matrix import build_experiment_matrix, matrix_to_dict
from core.parameter_search_engine import run_parameter_search
from core.portfolio_research_aggregation import aggregate_portfolio, portfolio_to_dict
from core.portfolio_research_overlap import analyze_overlap, overlap_analysis_to_dict
from core.research_artifact_index import artifact_index_to_json, build_artifact_index
from core.research_workbench_manifest import build_manifest, manifest_to_dict, manifest_to_json
from core.research_workbench_report import render_html_report, render_markdown_report
from core.research_workbench_splits import generate_research_splits
from core.strategy_research_oos_scoring import compute_oos_score, oos_score_to_dict
from core.strategy_research_promotion import evaluate_promotion, promotion_to_dict
from core.strategy_registry_adapters import (
    PARAMETER_CLASSES,
    SIGNAL_GENERATORS,
    STRATEGY_DEFINITIONS,
    register_all_adapters,
)
from core.strategy_registry_core import StrategyRegistry
from core.strategy_research_parameters import ParameterSchema, ParameterSpec


def _load_csv_fixture(path: Path, max_rows: int = 0) -> list:
    """Load OHLCV bars from CSV fixture."""
    if not path.exists():
        return []
    bars = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if max_rows > 0 and i >= max_rows:
                break
            try:
                bars.append({
                    "timestamp": float(row.get("timestamp", row.get("open_time", 0))),
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": float(row.get("volume", 0)),
                })
            except (ValueError, KeyError):
                continue
    return bars


def _load_registry_schemas(registry_path: Path) -> dict:
    """Load strategy schemas from registry JSON."""
    data = json.loads(registry_path.read_text())
    schemas = {}
    for strat in data.get("strategies", []):
        sid = strat["strategy_id"]
        param_schema_raw = strat.get("parameter_schema", {})
        specs = []
        for pname, pdef in sorted(param_schema_raw.items()):
            if pdef.get("type") == "enum":
                specs.append(ParameterSpec(name=pname, type="enum", values=tuple(pdef.get("values", []))))
            else:
                specs.append(ParameterSpec(name=pname, type=pdef.get("type", "int"),
                                           min=pdef.get("min"), max=pdef.get("max"), default=pdef.get("default")))
        schemas[sid] = ParameterSchema(strategy_id=sid, parameters=tuple(specs))
    return schemas


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multi-strategy research workbench")
    parser.add_argument("--fixture-dir", required=True, help="Fixture directory")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--strategies", required=True, help="Comma-separated strategy ids")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--timeframes", required=True, help="Comma-separated timeframes")
    parser.add_argument("--split-mode", default="rolling", help="Split mode")
    parser.add_argument("--search-budget", type=int, default=120, help="Search budget")
    parser.add_argument("--chunk-size", type=int, default=25, help="Chunk size")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir = Path(args.fixture_dir)

    strategy_ids = [s.strip() for s in args.strategies.split(",")]
    symbols = [s.strip() for s in args.symbols.split(",")]
    timeframes = [t.strip() for t in args.timeframes.split(",")]

    # Step 1: Registry
    print("[1/10] Building strategy registry...")
    registry = StrategyRegistry()
    errors = register_all_adapters(registry, strategy_ids)
    if errors:
        print(f"ERROR: registry errors: {errors}", file=sys.stderr)
        return 2
    registry_path = output_dir / "strategy_registry.json"
    registry_path.write_text(registry.to_json())

    # Step 2: Parameter search
    print("[2/10] Running parameter search...")
    schemas = _load_registry_schemas(registry_path)
    search_result = run_parameter_search(schemas, search_budget=args.search_budget)
    search_path = output_dir / "parameter_search.json"
    search_path.write_text(search_result.to_json())

    # Step 3: Splits
    print("[3/10] Generating splits...")
    # Use first fixture to estimate bar count
    sample_fixture = fixture_dir / f"{symbols[0].lower()}_{timeframes[0]}_clean.csv"
    sample_bars = _load_csv_fixture(sample_fixture, max_rows=args.chunk_size * 10)
    total_bars = len(sample_bars) if sample_bars else 100
    split_plan = generate_research_splits(total_bars=total_bars, n_folds=2, dataset_id="main")
    split_ids = [s.split_id for s in split_plan.splits if s.split_type == "TRAIN"]
    if not split_ids:
        split_ids = [s.split_id for s in split_plan.splits]

    # Step 4: Matrix
    print("[4/10] Building experiment matrix...")
    matrix = build_experiment_matrix(
        strategy_ids=strategy_ids, symbols=symbols, timeframes=timeframes,
        split_ids=split_ids, parameter_sets=search_result.parameter_sets,
        fixture_dir=str(fixture_dir),
    )
    matrix_path = output_dir / "matrix.json"
    matrix_path.write_text(json.dumps(matrix_to_dict(matrix), sort_keys=True, indent=2))

    # Step 5: Evaluate
    print(f"[5/10] Evaluating {matrix.total_rows} matrix rows...")
    run_results = []
    for row in matrix.rows:
        bars = _load_csv_fixture(Path(row.fixture_path), max_rows=args.chunk_size * 10)
        gen = SIGNAL_GENERATORS.get(row.strategy_id)
        param_cls = PARAMETER_CLASSES.get(row.strategy_id)
        params = param_cls() if param_cls else None
        result = evaluate_matrix_row(row, bars, signal_generator=gen, params=params)
        run_results.append(result)

    eval_result = EvaluationResult(
        results=tuple(run_results), total_rows=matrix.total_rows,
        evaluated_rows=len(run_results), skipped_rows=matrix.total_rows - len(run_results), warnings=[],
    )
    results_path = output_dir / "results.json"
    results_path.write_text(json.dumps(evaluation_to_dict(eval_result), sort_keys=True, indent=2))

    # Step 6: Portfolio
    print("[6/10] Aggregating portfolio...")
    portfolio = aggregate_portfolio(run_results)
    portfolio_path = output_dir / "portfolio_summary.json"
    portfolio_path.write_text(json.dumps(portfolio_to_dict(portfolio), sort_keys=True, indent=2))

    # Step 7: Overlap
    print("[7/10] Analyzing overlap...")
    overlap = analyze_overlap(run_results)

    # Step 8: Comparison + Promotion
    print("[8/10] Comparing strategies...")
    oos_scores = []
    for r in run_results:
        oos = compute_oos_score(r.strategy_id, r.parameter_set_id, r.symbol, r.timeframe,
                                r.score, r.score * 0.9, r.score * 0.8, r.trade_count)
        oos_scores.append(oos)
    comp = compare_strategies(run_results, overlap_analysis=overlap_analysis_to_dict(overlap), oos_scores=oos_scores)
    comp_path = output_dir / "comparison.json"
    comp_path.write_text(json.dumps(comparison_to_dict(comp), sort_keys=True, indent=2))

    recommendations = [promotion_to_dict(evaluate_promotion(oos)) for oos in oos_scores]
    promo_path = output_dir / "promotion_recommendations.json"
    promo_path.write_text(json.dumps(recommendations, sort_keys=True, indent=2))

    # Step 9: Bundle (reports first, then index + manifest)
    print("[9/10] Building bundle...")

    # Write reports first so manifest can index them
    report_data = {
        "strategy_count": len(strategy_ids),
        "total_rows": matrix.total_rows,
        "strategy_registry": registry.to_dict(),
        "parameter_search": search_result.to_dict(),
        "results": evaluation_to_dict(eval_result),
        "portfolio_summary": portfolio_to_dict(portfolio),
        "comparison": comparison_to_dict(comp),
        "promotion_recommendations": recommendations,
    }
    (output_dir / "report.md").write_text(render_markdown_report(report_data))
    (output_dir / "report.html").write_text(render_html_report(report_data))

    # Build index and manifest after reports exist
    index = build_artifact_index(output_dir)
    index_path = output_dir / "artifact_index.json"
    index_path.write_text(artifact_index_to_json(index))

    manifest = build_manifest(output_dir)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(manifest_to_json(manifest))

    # Step 10: Verify
    print("[10/10] Verifying...")
    from core.research_workbench_manifest import validate_manifest
    manifest_errors = validate_manifest(manifest)
    if manifest_errors:
        print(f"ERROR: manifest validation failed: {manifest_errors}", file=sys.stderr)
        return 2

    print(f"Workbench complete. {len(run_results)} results in {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
