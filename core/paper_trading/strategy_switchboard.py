"""Strategy switchboard — runs enabled strategies and produces unified output.

No orders, no secrets, no real Feishu send.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from core.paper_trading.strategy_config import StrategyLibrary, StrategyConfig, DataApiConfig
from core.paper_trading.strategy_registry import analyze_for_strategy, SignalCandidate, StrategyRunResult
from core.paper_trading.data_source import DataSourceConfig, MarketBar
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter
from core.paper_trading.market_data_quality import validate_bars


@dataclass(frozen=True)
class StrategyJob:
    """One strategy × one symbol × one timeframe."""
    strategy_id: str
    strategy_type: str
    symbol: str
    timeframe: str
    data_api: str


@dataclass(frozen=True)
class SwitchboardResult:
    """Result of running all enabled strategies."""
    date: str
    mode: str
    total_jobs: int
    success_count: int
    fail_count: int
    candidate_count: int
    candidates: list[SignalCandidate]
    job_results: list[StrategyRunResult]
    enabled_strategies: list[str]
    disabled_strategies: list[str]
    errors: list[dict[str, str]]


def build_jobs(library: StrategyLibrary) -> list[StrategyJob]:
    """Build list of jobs from enabled strategies."""
    jobs = []
    for strat_id, strat in library.enabled_strategies.items():
        for sym in strat.symbols:
            for tf in strat.timeframes:
                jobs.append(StrategyJob(
                    strategy_id=strat_id,
                    strategy_type=strat.strategy_type,
                    symbol=sym,
                    timeframe=tf,
                    data_api=strat.data_api,
                ))
    return jobs


def run_switchboard(
    library: StrategyLibrary,
    adapter: BinancePublicKlineAdapter,
    date_str: str,
    mode: str = "real_public_http",
    limit: int = 120,
) -> SwitchboardResult:
    """Run all enabled strategies and collect results."""
    jobs = build_jobs(library)
    results: list[StrategyRunResult] = []
    candidates: list[SignalCandidate] = []
    errors: list[dict[str, str]] = []
    success_count = 0
    fail_count = 0

    total = len(jobs)
    print(f"\nRunning {total} strategy jobs...")

    for i, job in enumerate(jobs):
        print(f"  [{i+1}/{total}] {job.strategy_id} {job.symbol} {job.timeframe}...", end=" ")

        try:
            bars = adapter.get_bars(job.symbol, timeframe=job.timeframe, limit=limit)
        except Exception as e:
            errors.append({"job": f"{job.strategy_id}/{job.symbol}/{job.timeframe}", "error": str(e)})
            results.append(StrategyRunResult(
                strategy_id=job.strategy_id, strategy_type=job.strategy_type,
                symbol=job.symbol, timeframe=job.timeframe,
                success=False, candidate=None, error=str(e),
            ))
            fail_count += 1
            print(f"ERROR: {e}")
            continue

        if not bars:
            errors.append({"job": f"{job.strategy_id}/{job.symbol}/{job.timeframe}", "error": "empty bars"})
            results.append(StrategyRunResult(
                strategy_id=job.strategy_id, strategy_type=job.strategy_type,
                symbol=job.symbol, timeframe=job.timeframe,
                success=False, candidate=None, error="empty bars",
            ))
            fail_count += 1
            print("EMPTY")
            continue

        qr = validate_bars(bars)
        if not qr.ok:
            errors.append({"job": f"{job.strategy_id}/{job.symbol}/{job.timeframe}", "error": f"quality: {qr.issues[:3]}"})
            results.append(StrategyRunResult(
                strategy_id=job.strategy_id, strategy_type=job.strategy_type,
                symbol=job.symbol, timeframe=job.timeframe,
                success=False, candidate=None, error="quality fail",
            ))
            fail_count += 1
            print("QUALITY_FAIL")
            continue

        run_result = analyze_for_strategy(job.strategy_id, job.strategy_type, bars)
        results.append(run_result)

        if run_result.success:
            success_count += 1
            if run_result.candidate:
                candidates.append(run_result.candidate)
                print(f"OK → {run_result.candidate.watch_state} ({run_result.candidate.direction})")
            else:
                print(f"OK → no match")
        else:
            fail_count += 1
            print(f"FAIL: {run_result.error}")

        time.sleep(0.3)

    enabled_ids = list(library.enabled_strategies.keys())
    disabled_ids = list(library.disabled_strategies.keys())

    return SwitchboardResult(
        date=date_str,
        mode=mode,
        total_jobs=total,
        success_count=success_count,
        fail_count=fail_count,
        candidate_count=len(candidates),
        candidates=candidates,
        job_results=results,
        enabled_strategies=enabled_ids,
        disabled_strategies=disabled_ids,
        errors=errors,
    )


def run_switchboard_offline(
    library: StrategyLibrary,
    date_str: str,
) -> SwitchboardResult:
    """Run switchboard in offline sample mode (mock data)."""
    jobs = build_jobs(library)
    candidates: list[SignalCandidate] = []
    results: list[StrategyRunResult] = []

    # Generate mock candidates for enabled strategies
    watch_states = ["LONG_READY", "LONG_WATCH", "NEAR_TURN_UP", "SHORT_WATCH", "WEAK_AVOID"]
    for i, job in enumerate(jobs):
        ws = watch_states[i % len(watch_states)]
        direction = "LONG_OBSERVE" if ws in ("LONG_READY", "LONG_WATCH", "NEAR_TURN_UP") else "SHORT_OBSERVE"

        candidate = SignalCandidate(
            strategy_id=job.strategy_id, strategy_type=job.strategy_type,
            symbol=job.symbol, timeframe=job.timeframe,
            watch_state=ws, setup_type="MOCK",
            direction=direction, priority="MEDIUM",
            last_close=60000.0 + i * 100,
            entry_observation=60000.0 + i * 100,
            invalidation_level=59000.0 + i * 100,
            take_profit_observation=62000.0 + i * 100,
            rr_ratio=2.0, risk_distance_pct=1.67, reward_distance_pct=3.33,
            turning_score=60, weakness_score=30, risk_score=40,
            macd_state="BULLISH_CROSS", rsi_state="NEUTRAL",
            trend_bias="BULLISH", volume_state="NORMAL",
            reasons=["offline mock"], risk_notes="mock",
        )
        candidates.append(candidate)
        results.append(StrategyRunResult(
            strategy_id=job.strategy_id, strategy_type=job.strategy_type,
            symbol=job.symbol, timeframe=job.timeframe,
            success=True, candidate=candidate, error=None,
        ))

    enabled_ids = list(library.enabled_strategies.keys())
    disabled_ids = list(library.disabled_strategies.keys())

    return SwitchboardResult(
        date=date_str,
        mode="offline_sample",
        total_jobs=len(jobs),
        success_count=len(jobs),
        fail_count=0,
        candidate_count=len(candidates),
        candidates=candidates,
        job_results=results,
        enabled_strategies=enabled_ids,
        disabled_strategies=disabled_ids,
        errors=[],
    )
