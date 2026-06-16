"""Parameter sweep engine — local multi-parameter backtest, no network."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Tuple
import itertools

from core.paper_trading.order_plan import OrderSide
from core.paper_trading.risk_sizing import RiskSizingConfig
from core.paper_trading.exit_rules import ExitRuleConfig
from core.paper_trading.replay_engine import (
    ReplayBar, ReplayConfig, load_bars_from_fixture, run_replay,
)
from core.paper_trading.performance_metrics import PerformanceMetrics, compute_metrics


@dataclass(frozen=True)
class ParameterSet:
    """A single parameter combination."""
    min_rr_ratio: float = 1.5
    max_risk_per_trade_pct: float = 1.0
    max_position_pct: float = 10.0
    trailing_stop_pct: float = 1.5
    take_profit_pct: float = 6.0
    stop_loss_pct: float = 2.0
    time_stop_bars: int = 50

    def label(self) -> str:
        return (
            f"rr={self.min_rr_ratio}_risk={self.max_risk_per_trade_pct}"
            f"_pos={self.max_position_pct}_trail={self.trailing_stop_pct}"
            f"_tp={self.take_profit_pct}_sl={self.stop_loss_pct}"
            f"_time={self.time_stop_bars}"
        )


@dataclass(frozen=True)
class SweepResult:
    """Result for a single parameter set across fixtures."""
    params: ParameterSet
    metrics: PerformanceMetrics
    score: float
    fixtures_run: int
    fixtures_ok: int
    fixtures_error: int


@dataclass
class SweepConfig:
    """Configuration for parameter sweep."""
    fixtures: List[str] = field(default_factory=list)
    param_sets: List[ParameterSet] = field(default_factory=list)
    signal_fn: Optional[Callable] = None
    score_fn: Optional[Callable[[PerformanceMetrics], float]] = None


def default_score(metrics: PerformanceMetrics) -> float:
    """Default scoring function: higher is better."""
    if metrics.total_trades == 0:
        return -100.0
    score = 0.0
    # Win rate contribution (0-30)
    score += metrics.win_rate * 30
    # Profit factor contribution (0-25, capped at 5)
    pf = min(metrics.profit_factor, 5.0) if metrics.profit_factor != float("inf") else 5.0
    score += (pf / 5.0) * 25
    # Expectancy contribution (0-20)
    if metrics.expectancy > 0:
        score += min(metrics.expectancy / 200, 1.0) * 20
    else:
        score += max(metrics.expectancy / 100, -1.0) * 10
    # Drawdown penalty (0 to -15)
    if metrics.max_drawdown > 0:
        dd_penalty = min(metrics.max_drawdown / 1000, 1.0) * 15
        score -= dd_penalty
    # Trade count bonus (5-10 for good sample size)
    if metrics.total_trades >= 10:
        score += 10
    elif metrics.total_trades >= 5:
        score += 5
    # Consecutive loss penalty
    if metrics.max_consecutive_losses >= 5:
        score -= 10
    elif metrics.max_consecutive_losses >= 3:
        score -= 5
    return round(score, 2)


def generate_default_param_sets() -> List[ParameterSet]:
    """Generate a default grid of parameter combinations."""
    rr_ratios = [1.0, 1.5, 2.0]
    risk_pcts = [0.5, 1.0, 2.0]
    tp_pcts = [4.0, 6.0, 8.0]
    sl_pcts = [1.0, 2.0, 3.0]
    trail_pcts = [1.0, 1.5, 2.0]
    time_stops = [30, 50]

    # Use a reasonable subset to avoid explosion
    param_sets = []
    for rr, risk, tp, sl, trail, time_s in itertools.product(
        rr_ratios, risk_pcts, tp_pcts, sl_pcts, trail_pcts, time_stops
    ):
        # Filter invalid combos
        if tp <= sl:
            continue
        param_sets.append(ParameterSet(
            min_rr_ratio=rr,
            max_risk_per_trade_pct=risk,
            max_position_pct=10.0,
            trailing_stop_pct=trail,
            take_profit_pct=tp,
            stop_loss_pct=sl,
            time_stop_bars=time_s,
        ))
    return param_sets


def _make_signal_fn():
    """Default MACD rebound signal function."""
    def signal(bars, i):
        if i < 10:
            return None
        recent_high = max(b.high for b in bars[max(0, i - 10):i])
        current = bars[i].close
        drop_pct = (recent_high - current) / recent_high * 100
        if drop_pct >= 3.0 and bars[i].close > bars[i].open:
            return {
                "symbol": "BTCUSDT", "side": "BUY",
                "entry_price": current,
                "stop_loss": current * 0.98,
                "take_profit": current * 1.06,
                "invalidation_price": current * 0.97,
                "signal_source": "macd_rebound_sweep",
            }
        return None
    return signal


def run_sweep(config: SweepConfig) -> List[SweepResult]:
    """Run parameter sweep across all fixtures and parameter sets."""
    if not config.param_sets:
        raise ValueError("No parameter sets provided")
    if not config.fixtures:
        raise ValueError("No fixtures provided")

    signal_fn = config.signal_fn or _make_signal_fn()
    score_fn = config.score_fn or default_score

    results = []
    for params in config.param_sets:
        all_metrics = []
        fixtures_ok = 0
        fixtures_error = 0

        for fixture_path in config.fixtures:
            try:
                bars = load_bars_from_fixture(fixture_path)
                if not bars:
                    continue

                replay_config = ReplayConfig(
                    risk_config=RiskSizingConfig(
                        max_risk_per_trade_pct=params.max_risk_per_trade_pct,
                        max_position_pct=params.max_position_pct,
                        min_rr_ratio=params.min_rr_ratio,
                        max_margin_cap=50000,
                        equity=100000,
                    ),
                    exit_config=ExitRuleConfig(
                        stop_loss_pct=params.stop_loss_pct,
                        take_profit_pct=params.take_profit_pct,
                        trailing_stop_pct=params.trailing_stop_pct,
                        time_stop_bars=params.time_stop_bars,
                    ),
                    auto_approve=True,
                )

                replay_result = run_replay(bars, signal_fn, replay_config)
                metrics = compute_metrics(replay_result.ledger)
                all_metrics.append(metrics)
                fixtures_ok += 1
            except Exception:
                fixtures_error += 1

        # Aggregate metrics across fixtures
        if all_metrics:
            agg = _aggregate_metrics(all_metrics)
            score = score_fn(agg)
        else:
            agg = PerformanceMetrics(
                total_trades=0, winners=0, losers=0, breakevens=0,
                win_rate=0, total_pnl=0, avg_pnl_per_trade=0,
                avg_win=0, avg_loss=0, profit_factor=0,
                max_drawdown=0, max_consecutive_losses=0,
                avg_rr_actual=0, expectancy=0,
            )
            score = -100.0

        results.append(SweepResult(
            params=params,
            metrics=agg,
            score=score,
            fixtures_run=len(config.fixtures),
            fixtures_ok=fixtures_ok,
            fixtures_error=fixtures_error,
        ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results


def _aggregate_metrics(metrics_list: List[PerformanceMetrics]) -> PerformanceMetrics:
    """Aggregate metrics from multiple fixtures."""
    total_trades = sum(m.total_trades for m in metrics_list)
    winners = sum(m.winners for m in metrics_list)
    losers = sum(m.losers for m in metrics_list)
    breakevens = sum(m.breakevens for m in metrics_list)
    total_pnl = sum(m.total_pnl for m in metrics_list)
    max_dd = max(m.max_drawdown for m in metrics_list)
    max_consec = max(m.max_consecutive_losses for m in metrics_list)

    win_rate = winners / total_trades if total_trades > 0 else 0.0
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0

    win_pnls = [m.avg_win * m.winners for m in metrics_list if m.winners > 0]
    loss_pnls = [m.avg_loss * m.losers for m in metrics_list if m.losers > 0]
    avg_win = sum(win_pnls) / winners if winners > 0 else 0.0
    avg_loss = sum(loss_pnls) / losers if losers > 0 else 0.0

    gross_profit = sum(m.avg_win * m.winners for m in metrics_list)
    gross_loss = abs(sum(m.avg_loss * m.losers for m in metrics_list))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    rr_vals = [m.avg_rr_actual for m in metrics_list if m.avg_rr_actual != 0]
    avg_rr = sum(rr_vals) / len(rr_vals) if rr_vals else 0.0

    expectancy = avg_win * win_rate + avg_loss * (1 - win_rate)

    return PerformanceMetrics(
        total_trades=total_trades,
        winners=winners,
        losers=losers,
        breakevens=breakevens,
        win_rate=win_rate,
        total_pnl=total_pnl,
        avg_pnl_per_trade=avg_pnl,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        max_drawdown=max_dd,
        max_consecutive_losses=max_consec,
        avg_rr_actual=avg_rr,
        expectancy=expectancy,
    )
