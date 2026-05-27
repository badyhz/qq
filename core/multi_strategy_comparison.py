"""Multi-strategy comparison — compare results and generate overlap/OOS summary.

Pure functions, no network, no exchange.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class StrategyComparisonResult:
    """Comparison of multiple strategy results."""
    comparison_id: str
    strategy_rankings: Tuple[Dict[str, Any], ...]
    family_summary: Dict[str, Any]
    timeframe_summary: Dict[str, Any]
    symbol_summary: Dict[str, Any]
    overlap_analysis: Dict[str, Any]
    out_of_sample_summary: Dict[str, Any]
    warnings: Tuple[str, ...]


def compare_strategies(
    results: list,
    overlap_analysis: Dict[str, Any] = None,
    oos_scores: list = None,
    comparison_id: str = "comparison_001",
) -> StrategyComparisonResult:
    """Compare strategy results and produce rankings.

    Pure function. Deterministic.
    """
    if not results:
        return StrategyComparisonResult(
            comparison_id=comparison_id,
            strategy_rankings=(),
            family_summary={},
            timeframe_summary={},
            symbol_summary={},
            overlap_analysis=overlap_analysis or {},
            out_of_sample_summary={},
            warnings=("NO_RESULTS",),
        )

    # Rank by score
    by_strategy: Dict[str, list] = {}
    for r in results:
        by_strategy.setdefault(r.strategy_id, []).append(r)

    rankings: List[Dict[str, Any]] = []
    for sid, rs in sorted(by_strategy.items()):
        avg_score = sum(r.score for r in rs) / len(rs)
        avg_expectancy = sum(r.expectancy_r for r in rs) / len(rs)
        total_trades = sum(r.trade_count for r in rs)
        rankings.append({
            "strategy_id": sid,
            "avg_score": round(avg_score, 6),
            "avg_expectancy_r": round(avg_expectancy, 6),
            "total_trades": total_trades,
            "run_count": len(rs),
        })
    rankings.sort(key=lambda x: x["avg_score"], reverse=True)

    # Family summary
    family: Dict[str, Dict] = {}
    for r in results:
        f = r.strategy_id  # Use strategy_id as family proxy
        if f not in family:
            family[f] = {"count": 0, "avg_score": 0.0, "total_trades": 0}
        family[f]["count"] += 1
        family[f]["avg_score"] += r.score
        family[f]["total_trades"] += r.trade_count
    for f in family:
        family[f]["avg_score"] = round(family[f]["avg_score"] / family[f]["count"], 6)

    # Timeframe summary
    tf_summary: Dict[str, Dict] = {}
    for r in results:
        if r.timeframe not in tf_summary:
            tf_summary[r.timeframe] = {"count": 0, "avg_score": 0.0}
        tf_summary[r.timeframe]["count"] += 1
        tf_summary[r.timeframe]["avg_score"] += r.score
    for tf in tf_summary:
        tf_summary[tf]["avg_score"] = round(tf_summary[tf]["avg_score"] / tf_summary[tf]["count"], 6)

    # Symbol summary
    sym_summary: Dict[str, Dict] = {}
    for r in results:
        if r.symbol not in sym_summary:
            sym_summary[r.symbol] = {"count": 0, "avg_score": 0.0}
        sym_summary[r.symbol]["count"] += 1
        sym_summary[r.symbol]["avg_score"] += r.score
    for s in sym_summary:
        sym_summary[s]["avg_score"] = round(sym_summary[s]["avg_score"] / sym_summary[s]["count"], 6)

    # OOS summary
    oos_summary: Dict[str, Any] = {}
    if oos_scores:
        overfit_count = sum(1 for s in oos_scores if s.overfit_flag)
        degradation_count = sum(1 for s in oos_scores if s.degradation_flag)
        oos_summary = {
            "total_scored": len(oos_scores),
            "overfit_count": overfit_count,
            "degradation_count": degradation_count,
        }

    warnings: List[str] = []
    if len(rankings) > 0 and rankings[0]["avg_score"] < 0.1:
        warnings.append("LOW_TOP_SCORE")

    return StrategyComparisonResult(
        comparison_id=comparison_id,
        strategy_rankings=tuple(rankings),
        family_summary=family,
        timeframe_summary=tf_summary,
        symbol_summary=sym_summary,
        overlap_analysis=overlap_analysis or {},
        out_of_sample_summary=oos_summary,
        warnings=tuple(warnings),
    )


def comparison_to_dict(comp: StrategyComparisonResult) -> Dict[str, Any]:
    """Serialize to dict."""
    return {
        "comparison_id": comp.comparison_id,
        "strategy_rankings": [dict(r) for r in comp.strategy_rankings],
        "family_summary": comp.family_summary,
        "timeframe_summary": comp.timeframe_summary,
        "symbol_summary": comp.symbol_summary,
        "overlap_analysis": comp.overlap_analysis,
        "out_of_sample_summary": comp.out_of_sample_summary,
        "warnings": list(comp.warnings),
    }


def comparison_to_json(comp: StrategyComparisonResult, indent: int = 2) -> str:
    """Serialize to JSON."""
    return json.dumps(comparison_to_dict(comp), sort_keys=True, indent=indent)
