#!/usr/bin/env python3
"""Backtest matrix evaluator CLI.

Reads a matrix JSON describing backtest runs, evaluates each run against
quality gates, and outputs per-run + aggregate results.

Usage:
    python3 scripts/evaluate_historical_backtest_matrix.py \
        --matrix-json path/to/matrix.json \
        --fixture-dir path/to/fixtures \
        --output-json results.json \
        --output-md results.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path setup
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_backtest_metrics_engine import (
    compute_aggregate_metrics,
    compute_run_metrics,
)
from core.offline_backtest_scorecard import grade_run


# ---------------------------------------------------------------------------
# Fixture loading (stub — Wave 2 modules not yet available)
# ---------------------------------------------------------------------------

def _load_fixture(fixture_dir: Path, symbol: str, timeframe: str) -> dict:
    """Load fixture data for a symbol/timeframe from the fixture directory.

    Returns dict with 'trades' list. Stub implementation returns empty trades.
    """
    fixture_file = fixture_dir / f"{symbol}_{timeframe}.json"
    if fixture_file.exists():
        with open(fixture_file, "r") as f:
            return json.load(f)
    # Stub: no fixture found
    return {"trades": [], "symbol": symbol, "timeframe": timeframe}


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------

def _evaluate_single_run(
    run_cfg: dict,
    fixture_dir: Path,
    run_index: int,
) -> dict:
    """Evaluate a single backtest run configuration.

    Returns dict with run_id, metrics, grade, scorecard details.
    """
    symbol = run_cfg.get("symbol", "UNKNOWN")
    timeframe = run_cfg.get("timeframe", "1h")
    param_id = run_cfg.get("param_id", f"P{run_index}")
    run_id = run_cfg.get("run_id", f"R{run_index}-{symbol}-{timeframe}")

    # Load fixture
    fixture = _load_fixture(fixture_dir, symbol, timeframe)
    trades = fixture.get("trades", [])

    # If run_cfg has inline trades, prefer those
    if "trades" in run_cfg:
        trades = run_cfg["trades"]

    # Compute metrics
    metrics = compute_run_metrics(trades)

    # Add metadata from run config
    metrics["symbol"] = symbol
    metrics["timeframe"] = timeframe
    metrics["param_id"] = param_id
    metrics["data_quality_clean"] = run_cfg.get("data_quality_clean", True)
    metrics["split_coverage_full"] = run_cfg.get("split_coverage_full", True)

    # Grade
    scorecard = grade_run(metrics, run_id=run_id)

    return {
        "run_id": run_id,
        "param_id": param_id,
        "symbol": symbol,
        "timeframe": timeframe,
        "metrics": metrics,
        "grade": scorecard.grade,
        "quality_gates": scorecard.quality_gates,
        "reasons": list(scorecard.reasons),
        "scorecard_id": scorecard.scorecard_id,
    }


def evaluate_matrix(
    matrix: list[dict],
    fixture_dir: Path,
) -> dict:
    """Evaluate all runs in a matrix.

    Returns dict with:
        run_results: list of per-run results
        aggregate: aggregated metrics
        rejection_reasons: list of {run_id, reasons} for non-PASS runs
    """
    run_results = []
    rejection_reasons = []

    for i, run_cfg in enumerate(matrix):
        result = _evaluate_single_run(run_cfg, fixture_dir, i)
        run_results.append(result)
        if result["grade"] != "PASS":
            rejection_reasons.append({
                "run_id": result["run_id"],
                "grade": result["grade"],
                "reasons": result["reasons"],
            })

    # Aggregate metrics from all runs
    aggregate = compute_aggregate_metrics(run_results)

    return {
        "run_results": run_results,
        "aggregate": aggregate,
        "rejection_reasons": rejection_reasons,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate historical backtest matrix."
    )
    parser.add_argument(
        "--matrix-json",
        required=True,
        help="Path to matrix JSON file describing backtest runs.",
    )
    parser.add_argument(
        "--fixture-dir",
        default=".",
        help="Directory containing fixture data files.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Path to write JSON results.",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="Path to write Markdown results.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    matrix_path = Path(args.matrix_json)
    if not matrix_path.exists():
        print(f"ERROR: matrix file not found: {matrix_path}", file=sys.stderr)
        return 1

    with open(matrix_path, "r") as f:
        matrix = json.load(f)

    if not isinstance(matrix, list):
        print("ERROR: matrix JSON must be a list of run configurations", file=sys.stderr)
        return 1

    fixture_dir = Path(args.fixture_dir)
    results = evaluate_matrix(matrix, fixture_dir)

    # Output JSON
    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"JSON results written to {out_path}")
    else:
        print(json.dumps(results, indent=2, default=str))

    # Output Markdown summary
    if args.output_md:
        from core.offline_backtest_report_renderer import render_backtest_report_markdown

        md_data = {
            "title": "Backtest Matrix Evaluation",
            "release_hold": "HOLD",
            "executive_summary": (
                f"Evaluated {len(results['run_results'])} runs. "
                f"{sum(1 for r in results['run_results'] if r['grade'] == 'PASS')} passed."
            ),
            "walk_forward_matrix": results["run_results"],
            "top_params": [
                r for r in results["run_results"] if r["grade"] == "PASS"
            ],
            "rejected_params": [
                {"param_id": r["run_id"], "reasons": r["reasons"]}
                for r in results["run_results"]
                if r["grade"] != "PASS"
            ],
        }
        md_text = render_backtest_report_markdown(md_data)
        out_path = Path(args.output_md)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            f.write(md_text)
        print(f"Markdown results written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
