#!/usr/bin/env python3
"""CLI: Full historical OHLCV backtest research lab pipeline.

Orchestrates: data quality audit -> matrix generation -> matrix evaluation
-> scorecard -> comparison -> report rendering -> bundle manifest.

All safety constraints: release_hold=HOLD, no_live, no_submit, no_exchange.
No network calls.  No subprocess.  Stdlib + core modules only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_backtest_bundle_builder import (
    build_backtest_bundle,
    build_manifest,
)
from core.offline_shadow_comparison import compare_experiments
from core.offline_shadow_metric_engine import compute_run_metrics
from core.offline_shadow_report_renderer import (
    render_report_html,
    render_report_json,
    render_report_markdown,
)
from core.offline_shadow_scorecard import grade_run
from core.historical_ohlcv_chunked_reader import (
    OHLCVColumnMapping,
    read_ohlcv_chunks,
    summarize_dataset,
)


# ---------------------------------------------------------------------------
# canonical column mapping for historical OHLCV CSVs
# ---------------------------------------------------------------------------

_DEFAULT_COL_MAP = OHLCVColumnMapping(
    timestamp_col="timestamp",
    open_col="open",
    high_col="high",
    low_col="low",
    close_col="close",
    volume_col="volume",
)


# ---------------------------------------------------------------------------
# pipeline steps
# ---------------------------------------------------------------------------

def _step_data_quality(
    fixture_dir: Path,
    symbols: list[str],
    timeframes: list[str],
    chunk_size: int,
) -> tuple[dict, bool]:
    """Run data quality audit on all symbol/timeframe CSVs.

    Returns (quality_report_dict, all_clean).
    """
    reports = []
    all_clean = True

    for sym in symbols:
        for tf in timeframes:
            csv_path = fixture_dir / f"{sym}_{tf}.csv"
            if not csv_path.exists():
                reports.append({
                    "symbol": sym,
                    "timeframe": tf,
                    "status": "missing",
                    "csv_path": str(csv_path),
                })
                all_clean = False
                continue

            # Determine expected interval from timeframe
            interval_map = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
            expected_interval = interval_map.get(tf, 300)

            report = summarize_dataset(
                csv_path=csv_path,
                column_mapping=_DEFAULT_COL_MAP,
                chunk_size=chunk_size,
                symbol=sym,
                timeframe=tf,
                expected_interval_seconds=expected_interval,
            )
            reports.append({
                "symbol": report.symbol,
                "timeframe": report.timeframe,
                "total_rows": report.total_rows,
                "valid_rows": report.valid_rows,
                "duplicate_count": report.duplicate_count,
                "gap_count": report.gap_count,
                "invalid_ohlcv_count": report.invalid_ohlcv_count,
                "is_clean": report.is_clean,
                "status": "clean" if report.is_clean else "has_issues",
            })
            if not report.is_clean:
                all_clean = False

    return {
        "quality_reports": reports,
        "all_clean": all_clean,
        "dataset_count": len(reports),
    }, all_clean


def _step_matrix_generation(
    symbols: list[str],
    timeframes: list[str],
    split_mode: str,
    param_grid: list[str],
) -> dict:
    """Generate the backtest matrix (parameter x symbol x timeframe grid)."""
    cells = []
    cell_idx = 0
    for sym in symbols:
        for tf in timeframes:
            for param in param_grid:
                cells.append({
                    "cell_id": f"cell_{cell_idx:04d}",
                    "symbol": sym,
                    "timeframe": tf,
                    "param_label": param,
                    "split_mode": split_mode,
                })
                cell_idx += 1

    return {
        "matrix_id": "backtest_matrix",
        "cell_count": len(cells),
        "split_mode": split_mode,
        "cells": cells,
    }


def _step_matrix_evaluation(
    matrix: dict,
    fixture_dir: Path,
    chunk_size: int,
) -> list[dict]:
    """Evaluate each cell in the matrix against fixture data."""
    results = []
    for cell in matrix["cells"]:
        sym = cell["symbol"]
        tf = cell["timeframe"]
        csv_path = fixture_dir / f"{sym}_{tf}.csv"

        if not csv_path.exists():
            results.append({
                "cell_id": cell["cell_id"],
                "symbol": sym,
                "timeframe": tf,
                "param_label": cell["param_label"],
                "status": "missing_data",
                "metrics": _empty_metrics(),
            })
            continue

        # Read bars and compute simple metrics
        bars = []
        for chunk in read_ohlcv_chunks(csv_path, _DEFAULT_COL_MAP, chunk_size, sym, tf):
            bars.extend(chunk)

        if not bars:
            results.append({
                "cell_id": cell["cell_id"],
                "symbol": sym,
                "timeframe": tf,
                "param_label": cell["param_label"],
                "status": "no_bars",
                "metrics": _empty_metrics(),
            })
            continue

        # Simple mock signal generation: use close price changes as R-multiples
        outcomes = _generate_mock_outcomes(bars)
        metrics = compute_run_metrics(outcomes)

        results.append({
            "cell_id": cell["cell_id"],
            "symbol": sym,
            "timeframe": tf,
            "param_label": cell["param_label"],
            "status": "evaluated",
            "metrics": metrics,
        })

    return results


def _generate_mock_outcomes(bars: list) -> list[dict]:
    """Generate mock trade outcomes from bar close price changes."""
    outcomes = []
    for i in range(1, len(bars)):
        price_change = bars[i].close - bars[i - 1].close
        r_multiple = price_change / bars[i - 1].close * 100  # normalized
        outcomes.append({
            "return_r": r_multiple,
            "mfe_r": abs(r_multiple) * 1.2 if r_multiple > 0 else abs(r_multiple) * 0.3,
            "mae_r": abs(r_multiple) * 0.3 if r_multiple > 0 else abs(r_multiple) * 1.2,
        })
    return outcomes


def _empty_metrics() -> dict:
    return {
        "candidate_count": 0,
        "win_count": 0,
        "loss_count": 0,
        "neutral_count": 0,
        "win_rate": 0.0,
        "avg_return_r": 0.0,
        "expectancy_r": 0.0,
        "max_drawdown_r": 0.0,
        "avg_mfe_r": 0.0,
        "avg_mae_r": 0.0,
        "profit_factor": 0.0,
        "sample_quality_score": 0.0,
        "coverage_status": "empty",
    }


def _step_scorecard(results: list[dict]) -> dict:
    """Grade each evaluated cell and produce scorecard summary."""
    graded = []
    pass_count = 0
    watch_count = 0
    reject_count = 0

    for r in results:
        metrics = r.get("metrics", {})
        grade_result = grade_run(metrics)
        graded.append({
            "cell_id": r["cell_id"],
            "symbol": r["symbol"],
            "timeframe": r["timeframe"],
            "param_label": r["param_label"],
            "grade": grade_result["grade"],
            "reason_codes": grade_result["reason_codes"],
            "blockers": grade_result["blockers"],
        })
        if grade_result["grade"] == "PASS":
            pass_count += 1
        elif grade_result["grade"] == "WATCH":
            watch_count += 1
        else:
            reject_count += 1

    return {
        "scorecard_id": "backtest_scorecard",
        "cell_count": len(graded),
        "pass_count": pass_count,
        "watch_count": watch_count,
        "reject_count": reject_count,
        "cells": graded,
    }


def _step_comparison(scorecard: dict) -> dict:
    """Compare cells side-by-side using comparison engine."""
    cells = scorecard["cells"]
    experiment_ids = [c["cell_id"] for c in cells]
    comparisons = []
    if len(cells) >= 2:
        # Wrap cells as experiment result dicts with runs
        def _wrap(cell):
            return {
                "experiment_id": cell["cell_id"],
                "runs": [{"run_id": "r1", "metrics": {
                    "candidate_count": cell.get("trade_count", 0),
                    "win_count": 0, "loss_count": 0,
                    "expectancy_r": cell.get("expectancy_r", 0.0),
                    "max_drawdown_r": cell.get("max_drawdown_r", 0.0),
                    "sample_quality_score": 0.0,
                    "profit_factor": 0.0,
                    "coverage_status": "full",
                }}],
            }
        for i in range(len(cells)):
            for j in range(i + 1, len(cells)):
                comparisons.append(compare_experiments(_wrap(cells[i]), _wrap(cells[j])))
    return {
        "comparison_id": "backtest_comparison",
        "experiment_ids": experiment_ids,
        "pair_count": len(comparisons),
        "comparisons": comparisons,
    }


def _step_render_reports(results: list[dict], scorecard: dict) -> dict:
    """Render markdown, HTML, and JSON reports."""
    # Merge scorecard info into results for report rendering
    merged = []
    scorecard_map = {c["cell_id"]: c for c in scorecard["cells"]}
    for r in results:
        sc = scorecard_map.get(r["cell_id"], {})
        merged.append({
            "experiment_id": r["cell_id"],
            "symbol": r["symbol"],
            "timeframe": r["timeframe"],
            "param_label": r["param_label"],
            "metrics": r["metrics"],
            "scorecard": {
                "grade": sc.get("grade", "N/A"),
                "reason_codes": sc.get("reason_codes", []),
                "blockers": sc.get("blockers", []),
            },
        })

    return {
        "report_md": render_report_markdown(merged),
        "report_html": render_report_html(merged),
        "report_json": render_report_json(merged),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run historical OHLCV backtest research lab"
    )
    parser.add_argument("--fixture-dir", required=True, help="Directory containing OHLCV CSV fixtures")
    parser.add_argument("--output-dir", required=True, help="Directory to write all pipeline artifacts")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT", help="Comma-separated symbols")
    parser.add_argument("--timeframes", default="5m,15m", help="Comma-separated timeframes")
    parser.add_argument("--split-mode", default="walk_forward", help="Walk-forward split mode")
    parser.add_argument("--param-grid", default="conservative,balanced,aggressive", help="Comma-separated param grid presets")
    parser.add_argument("--chunk-size", type=int, default=500, help="Chunk size for CSV reader")
    args = parser.parse_args(argv)

    fixture_dir = Path(args.fixture_dir)
    output_dir = Path(args.output_dir)
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    timeframes = [t.strip() for t in args.timeframes.split(",") if t.strip()]
    param_grid = [p.strip() for p in args.param_grid.split(",") if p.strip()]

    if not fixture_dir.exists():
        print(f"ERROR: fixture dir not found: {fixture_dir}", file=sys.stderr)
        return 1

    if not symbols:
        print("ERROR: no symbols specified", file=sys.stderr)
        return 1

    if not timeframes:
        print("ERROR: no timeframes specified", file=sys.stderr)
        return 1

    if not param_grid:
        print("ERROR: no param grid specified", file=sys.stderr)
        return 1

    # Validate param grid names
    valid_presets = {"conservative", "balanced", "aggressive"}
    for pg in param_grid:
        if pg not in valid_presets:
            print(f"ERROR: invalid param grid preset '{pg}', valid: {sorted(valid_presets)}", file=sys.stderr)
            return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Data quality audit
    print("Step 1: Data quality audit...")
    quality_report, all_clean = _step_data_quality(fixture_dir, symbols, timeframes, args.chunk_size)
    print(f"  datasets: {quality_report['dataset_count']}, all_clean: {all_clean}")

    # Step 2: Matrix generation
    print("Step 2: Matrix generation...")
    matrix = _step_matrix_generation(symbols, timeframes, args.split_mode, param_grid)
    print(f"  cells: {matrix['cell_count']}")

    # Step 3: Matrix evaluation
    print("Step 3: Matrix evaluation...")
    results = _step_matrix_evaluation(matrix, fixture_dir, args.chunk_size)
    print(f"  evaluated: {len(results)}")

    # Step 4: Scorecard
    print("Step 4: Scorecard...")
    scorecard = _step_scorecard(results)
    print(f"  PASS={scorecard['pass_count']} WATCH={scorecard['watch_count']} REJECT={scorecard['reject_count']}")

    # Step 5: Comparison
    print("Step 5: Comparison...")
    comparison = _step_comparison(scorecard)

    # Step 6: Report rendering
    print("Step 6: Report rendering...")
    reports = _step_render_reports(results, scorecard)

    # Step 7: Write artifacts
    print("Step 7: Writing artifacts...")
    artifacts = {
        "data_quality_report.json": json.dumps(quality_report, indent=2, sort_keys=True),
        "matrix.json": json.dumps(matrix, indent=2, sort_keys=True),
        "results.json": json.dumps(results, indent=2, sort_keys=True),
        "scorecard.json": json.dumps(scorecard, indent=2, sort_keys=True),
        "comparison.json": json.dumps(comparison, indent=2, sort_keys=True),
        "report.md": reports["report_md"],
        "report.html": reports["report_html"],
        "report.json": json.dumps(reports["report_json"], indent=2, sort_keys=True),
    }

    for name, content in artifacts.items():
        (output_dir / name).write_text(content)

    # Step 8: Build manifest
    print("Step 8: Building manifest...")
    from core.offline_backtest_bundle_builder import compute_sha256

    manifest_artifacts = []
    for name in sorted(artifacts):
        fpath = output_dir / name
        manifest_artifacts.append({
            "name": name,
            "sha256": compute_sha256(fpath),
            "size_bytes": fpath.stat().st_size,
        })
    manifest = build_manifest(manifest_artifacts)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))

    # Verify safety
    assert manifest["release_hold"] == "HOLD"
    assert manifest["no_live"] is True
    assert manifest["no_submit"] is True
    assert manifest["no_exchange"] is True

    print(f"\nPipeline complete. Artifacts in {output_dir}")
    print(f"  Total artifacts: {manifest['artifact_count']}")

    # Return 0 only if pipeline completed
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
