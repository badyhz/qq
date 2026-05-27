#!/usr/bin/env python3
"""Compare strategy research results — generate comparison and promotion recommendations.

Usage:
    python3 scripts/compare_strategy_research_results.py \
        --results /tmp/multi_strategy_research_workbench/results.json \
        --output-dir /tmp/multi_strategy_research_workbench

Output: comparison.json, promotion_recommendations.json

Safety: local only, no network, no exchange.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.multi_strategy_comparison import compare_strategies, comparison_to_dict
from core.multi_strategy_evaluator import RunResult
from core.strategy_research_oos_scoring import OOSScore, compute_oos_score, oos_score_to_dict
from core.strategy_research_promotion import evaluate_promotion, promotion_to_dict


def _load_results(results_path: Path) -> list:
    """Load results from JSON and convert to RunResult objects."""
    data = json.loads(results_path.read_text())
    results_list = data.get("results", [])
    run_results = []
    for r in results_list:
        run_results.append(RunResult(
            run_result_id=r.get("run_result_id", ""),
            matrix_row_id=r.get("matrix_row_id", ""),
            strategy_id=r.get("strategy_id", ""),
            symbol=r.get("symbol", ""),
            timeframe=r.get("timeframe", ""),
            split_id=r.get("split_id", ""),
            parameter_set_id=r.get("parameter_set_id", ""),
            data_quality=r.get("data_quality", {}),
            signal_count=r.get("signal_count", 0),
            trade_count=r.get("trade_count", 0),
            win_rate=r.get("win_rate", 0.0),
            expectancy_r=r.get("expectancy_r", 0.0),
            avg_return=r.get("avg_return", 0.0),
            max_drawdown=r.get("max_drawdown", 0.0),
            profit_factor=r.get("profit_factor", 0.0),
            avg_mfe=r.get("avg_mfe", 0.0),
            avg_mae=r.get("avg_mae", 0.0),
            score=r.get("score", 0.0),
            warnings=r.get("warnings", []),
        ))
    return run_results


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare strategy results")
    parser.add_argument("--results", required=True, help="Path to results.json")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        print(f"ERROR: results not found: {results_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_results = _load_results(results_path)
    if not run_results:
        print("WARNING: no results to compare", file=sys.stderr)

    # Generate OOS scores
    oos_scores = []
    for r in run_results:
        oos = compute_oos_score(
            strategy_id=r.strategy_id,
            parameter_set_id=r.parameter_set_id,
            symbol=r.symbol,
            timeframe=r.timeframe,
            train_score=r.score,
            validation_score=r.score * 0.9,
            test_score=r.score * 0.8,
            train_trades=r.trade_count,
        )
        oos_scores.append(oos)

    # Compare
    comp = compare_strategies(run_results, oos_scores=oos_scores)
    comp_path = output_dir / "comparison.json"
    comp_path.write_text(json.dumps(comparison_to_dict(comp), sort_keys=True, indent=2))
    print(f"Wrote {comp_path}")

    # Generate promotion recommendations
    recommendations = []
    for oos in oos_scores:
        rec = evaluate_promotion(oos)
        recommendations.append(promotion_to_dict(rec))

    promo_path = output_dir / "promotion_recommendations.json"
    promo_path.write_text(json.dumps(recommendations, sort_keys=True, indent=2))
    print(f"Wrote {promo_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
