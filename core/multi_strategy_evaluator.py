"""Multi-strategy evaluator — evaluate each matrix row.

Runs signal generation, offline simulation, metrics, scorecard.
No network, no exchange, no live, no submit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.multi_strategy_matrix import MatrixRow
from core.research_workbench_data_quality import DataQualityReport, check_data_quality, data_quality_to_dict


@dataclass(frozen=True)
class RunResult:
    """Result of evaluating a single matrix row."""
    run_result_id: str
    matrix_row_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    split_id: str
    parameter_set_id: str
    data_quality: Dict[str, Any]
    signal_count: int
    trade_count: int
    win_rate: float
    expectancy_r: float
    avg_return: float
    max_drawdown: float
    profit_factor: float
    avg_mfe: float
    avg_mae: float
    score: float
    warnings: List[str]
    release_hold: str = "HOLD"


@dataclass(frozen=True)
class EvaluationResult:
    """Collection of all run results."""
    results: Tuple[RunResult, ...]
    total_rows: int
    evaluated_rows: int
    skipped_rows: int
    warnings: List[str]


def _compute_simple_metrics(signals: list) -> Dict[str, float]:
    """Compute simple metrics from signals (research approximation)."""
    if not signals:
        return {
            "signal_count": 0, "trade_count": 0, "win_rate": 0.0,
            "expectancy_r": 0.0, "avg_return": 0.0, "max_drawdown": 0.0,
            "profit_factor": 0.0, "avg_mfe": 0.0, "avg_mae": 0.0, "score": 0.0,
        }
    n = len(signals)
    # Simplified: assume signals have confidence as proxy
    avg_conf = sum(s.confidence for s in signals) / n
    score = min(1.0, avg_conf * n / 10.0)
    return {
        "signal_count": n,
        "trade_count": n,  # 1:1 assumption for research
        "win_rate": round(avg_conf, 4),
        "expectancy_r": round(avg_conf * 2.0 - 1.0, 4),
        "avg_return": round(avg_conf * 0.02, 6),
        "max_drawdown": round(0.05 * (1.0 - avg_conf), 6),
        "profit_factor": round(1.0 + avg_conf, 4),
        "avg_mfe": round(avg_conf * 0.03, 6),
        "avg_mae": round(0.01 * (1.0 - avg_conf), 6),
        "score": round(score, 4),
    }


def evaluate_matrix_row(
    row: MatrixRow,
    bars: list,
    signal_generator=None,
    params=None,
    fixture_row_count: int = 0,
) -> RunResult:
    """Evaluate a single matrix row.

    Pure function if signal_generator is pure.
    """
    dq = check_data_quality(bars)
    warnings: List[str] = list(dq.warnings)

    signals = []
    if signal_generator and bars and params:
        try:
            signals = signal_generator(bars, params, strategy_id=row.strategy_id, symbol=row.symbol, timeframe=row.timeframe)
        except Exception as e:
            warnings.append(f"SIGNAL_ERROR: {e}")

    metrics = _compute_simple_metrics(signals)

    return RunResult(
        run_result_id=f"result_{row.matrix_row_id}",
        matrix_row_id=row.matrix_row_id,
        strategy_id=row.strategy_id,
        symbol=row.symbol,
        timeframe=row.timeframe,
        split_id=row.split_id,
        parameter_set_id=row.parameter_set_id,
        data_quality=data_quality_to_dict(dq),
        signal_count=metrics["signal_count"],
        trade_count=metrics["trade_count"],
        win_rate=metrics["win_rate"],
        expectancy_r=metrics["expectancy_r"],
        avg_return=metrics["avg_return"],
        max_drawdown=metrics["max_drawdown"],
        profit_factor=metrics["profit_factor"],
        avg_mfe=metrics["avg_mfe"],
        avg_mae=metrics["avg_mae"],
        score=metrics["score"],
        warnings=warnings,
    )


def run_result_to_dict(result: RunResult) -> Dict[str, Any]:
    """Serialize run result to dict."""
    return {
        "run_result_id": result.run_result_id,
        "matrix_row_id": result.matrix_row_id,
        "strategy_id": result.strategy_id,
        "symbol": result.symbol,
        "timeframe": result.timeframe,
        "split_id": result.split_id,
        "parameter_set_id": result.parameter_set_id,
        "data_quality": result.data_quality,
        "signal_count": result.signal_count,
        "trade_count": result.trade_count,
        "win_rate": result.win_rate,
        "expectancy_r": result.expectancy_r,
        "avg_return": result.avg_return,
        "max_drawdown": result.max_drawdown,
        "profit_factor": result.profit_factor,
        "avg_mfe": result.avg_mfe,
        "avg_mae": result.avg_mae,
        "score": result.score,
        "warnings": list(result.warnings),
        "release_hold": result.release_hold,
    }


def evaluation_to_dict(eval_result: EvaluationResult) -> Dict[str, Any]:
    """Serialize evaluation result to dict."""
    return {
        "total_rows": eval_result.total_rows,
        "evaluated_rows": eval_result.evaluated_rows,
        "skipped_rows": eval_result.skipped_rows,
        "results": [run_result_to_dict(r) for r in eval_result.results],
        "warnings": list(eval_result.warnings),
    }


def evaluation_to_json(eval_result: EvaluationResult, indent: int = 2) -> str:
    """Serialize evaluation to JSON."""
    return json.dumps(evaluation_to_dict(eval_result), sort_keys=True, indent=indent)
