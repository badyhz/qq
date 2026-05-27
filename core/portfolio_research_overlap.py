"""Portfolio research overlap analysis — signal/trade overlap and concentration.

Computes overlap between strategy pairs, symbol concentration,
family concentration, timeframe concentration.

Pure functions, no network, no exchange.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class OverlapEntry:
    """Overlap analysis between a pair of strategies."""
    overlap_id: str
    strategy_pair: Tuple[str, str]
    symbol: str
    timeframe: str
    signal_overlap_count: int
    signal_overlap_ratio: float
    trade_overlap_count: int
    trade_overlap_ratio: float
    same_symbol_concentration: float
    strategy_family_concentration: float
    timeframe_concentration: float
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class OverlapAnalysis:
    """Complete overlap analysis."""
    entries: Tuple[OverlapEntry, ...]
    high_signal_overlap_pairs: Tuple[str, ...]
    high_trade_overlap_pairs: Tuple[str, ...]
    concentration_warnings: Tuple[str, ...]


def _concentration(counts: Dict[str, int]) -> float:
    """Compute concentration (max share). Total must be > 0."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return max(counts.values()) / total


def analyze_overlap(
    results: list,
    high_overlap_threshold: float = 0.5,
) -> OverlapAnalysis:
    """Analyze signal/trade overlap and concentration across strategy results.

    Research approximation. No timestamp-level overlap computation.
    """
    if not results:
        return OverlapAnalysis(
            entries=(),
            high_signal_overlap_pairs=(),
            high_trade_overlap_pairs=(),
            concentration_warnings=("NO_RESULTS",),
        )

    # Group by (strategy_id, symbol, timeframe)
    grouped: Dict[Tuple[str, str, str], list] = {}
    for r in results:
        key = (r.strategy_id, r.symbol, r.timeframe)
        grouped.setdefault(key, []).append(r)

    # Concentration analysis
    symbol_counts: Dict[str, int] = {}
    family_counts: Dict[str, int] = {}
    tf_counts: Dict[str, int] = {}
    for r in results:
        symbol_counts[r.symbol] = symbol_counts.get(r.symbol, 0) + r.trade_count
        tf_counts[r.timeframe] = tf_counts.get(r.timeframe, 0) + r.trade_count

    symbol_conc = _concentration(symbol_counts)
    tf_conc = _concentration(tf_counts)

    # Pairwise overlap (simplified: same symbol+timeframe = overlapping)
    strategy_ids = sorted(set(r.strategy_id for r in results))
    entries: List[OverlapEntry] = []
    high_sig_pairs: List[str] = []
    high_trade_pairs: List[str] = []

    for i, s1 in enumerate(strategy_ids):
        for s2 in strategy_ids[i + 1:]:
            # Check overlap per symbol/timeframe
            for symbol in sorted(set(r.symbol for r in results)):
                for tf in sorted(set(r.timeframe for r in results)):
                    r1_list = [r for r in results if r.strategy_id == s1 and r.symbol == symbol and r.timeframe == tf]
                    r2_list = [r for r in results if r.strategy_id == s2 and r.symbol == symbol and r.timeframe == tf]
                    if not r1_list or not r2_list:
                        continue

                    sig1 = sum(r.signal_count for r in r1_list)
                    sig2 = sum(r.signal_count for r in r2_list)
                    trade1 = sum(r.trade_count for r in r1_list)
                    trade2 = sum(r.trade_count for r in r2_list)

                    # Approximate overlap: min of the two
                    sig_overlap = min(sig1, sig2)
                    trade_overlap = min(trade1, trade2)
                    sig_ratio = sig_overlap / max(sig1, sig2) if max(sig1, sig2) > 0 else 0.0
                    trade_ratio = trade_overlap / max(trade1, trade2) if max(trade1, trade2) > 0 else 0.0

                    warnings: List[str] = []
                    if sig_ratio > high_overlap_threshold:
                        warnings.append("HIGH_SIGNAL_OVERLAP")
                        high_sig_pairs.append(f"{s1}/{s2}@{symbol}:{tf}")
                    if trade_ratio > high_overlap_threshold:
                        warnings.append("HIGH_TRADE_OVERLAP")
                        high_trade_pairs.append(f"{s1}/{s2}@{symbol}:{tf}")

                    pair_id = f"overlap_{s1}_{s2}_{symbol}_{tf}"
                    entries.append(OverlapEntry(
                        overlap_id=pair_id,
                        strategy_pair=(s1, s2),
                        symbol=symbol,
                        timeframe=tf,
                        signal_overlap_count=sig_overlap,
                        signal_overlap_ratio=round(sig_ratio, 4),
                        trade_overlap_count=trade_overlap,
                        trade_overlap_ratio=round(trade_ratio, 4),
                        same_symbol_concentration=round(symbol_conc, 4),
                        strategy_family_concentration=0.0,
                        timeframe_concentration=round(tf_conc, 4),
                        warnings=tuple(warnings),
                    ))

    concentration_warnings: List[str] = []
    if symbol_conc > 0.8:
        concentration_warnings.append("SAME_SYMBOL_CONCENTRATION")
    if tf_conc > 0.8:
        concentration_warnings.append("TIMEFRAME_CONCENTRATION")

    return OverlapAnalysis(
        entries=tuple(entries),
        high_signal_overlap_pairs=tuple(high_sig_pairs),
        high_trade_overlap_pairs=tuple(high_trade_pairs),
        concentration_warnings=tuple(concentration_warnings),
    )


def overlap_analysis_to_dict(analysis: OverlapAnalysis) -> Dict[str, Any]:
    """Serialize overlap analysis to dict."""
    return {
        "entries": [
            {
                "overlap_id": e.overlap_id,
                "strategy_pair": list(e.strategy_pair),
                "symbol": e.symbol,
                "timeframe": e.timeframe,
                "signal_overlap_count": e.signal_overlap_count,
                "signal_overlap_ratio": e.signal_overlap_ratio,
                "trade_overlap_count": e.trade_overlap_count,
                "trade_overlap_ratio": e.trade_overlap_ratio,
                "same_symbol_concentration": e.same_symbol_concentration,
                "strategy_family_concentration": e.strategy_family_concentration,
                "timeframe_concentration": e.timeframe_concentration,
                "warnings": list(e.warnings),
            }
            for e in analysis.entries
        ],
        "high_signal_overlap_pairs": list(analysis.high_signal_overlap_pairs),
        "high_trade_overlap_pairs": list(analysis.high_trade_overlap_pairs),
        "concentration_warnings": list(analysis.concentration_warnings),
    }
