"""Parameter top-N stability — rank stability and dominance.

Pure functions. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class TopNStability:
    """Top-N stability metric."""
    strategy_id: str
    top_n: int
    stable_rank: bool
    rank_swaps: int
    dominant: bool
    dominance_score: float


def compute_topn_stability(
    strategy_id: str,
    rank_history: List[int],
    top_n: int = 5,
) -> TopNStability:
    """Compute top-N rank stability."""
    if not rank_history:
        return TopNStability(strategy_id, top_n, False, 0, False, 0.0)

    swaps = sum(1 for i in range(1, len(rank_history)) if rank_history[i] != rank_history[i - 1])
    in_top_n = all(r <= top_n for r in rank_history)
    avg_rank = sum(rank_history) / len(rank_history)
    dominance = max(0, 1.0 - avg_rank / max(top_n * 2, 1))

    return TopNStability(
        strategy_id=strategy_id,
        top_n=top_n,
        stable_rank=swaps <= len(rank_history) * 0.3,
        rank_swaps=swaps,
        dominant=in_top_n,
        dominance_score=dominance,
    )


def topn_to_dict(t: TopNStability) -> Dict:
    return {
        "strategy_id": t.strategy_id,
        "top_n": t.top_n,
        "stable_rank": t.stable_rank,
        "rank_swaps": t.rank_swaps,
        "dominant": t.dominant,
        "dominance_score": t.dominance_score,
    }
