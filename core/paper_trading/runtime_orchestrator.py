"""Paper runtime orchestrator — runs full paper pipeline locally, no network."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from core.paper_trading.runtime_config import RuntimeConfig
from core.paper_trading.strategy_registry import StrategyRegistry, create_default_registry
from core.paper_trading.risk_sizing import RiskSizingConfig
from core.paper_trading.exit_rules import ExitRuleConfig
from core.paper_trading.replay_engine import ReplayConfig, load_bars_from_fixture, run_replay
from core.paper_trading.performance_metrics import PerformanceMetrics, compute_metrics
from core.paper_trading.strategy_scorecard import Scorecard, score_strategy
from core.paper_trading.local_alert_bridge import LocalAlertBridge, AlertLevel
from core.paper_trading.portfolio_risk import PortfolioRiskConfig


@dataclass(frozen=True)
class RuntimeResult:
    status: str
    strategy_name: str
    fixtures_run: int
    fixtures_failed: int
    total_signals: int
    total_plans: int
    total_rejected: int
    total_trades: int
    total_pnl: float
    win_rate: float
    score: float
    rating: str
    alerts_written: int
    safety_flags: List[str]
    metrics: Optional[PerformanceMetrics] = None
    scorecard: Optional[Scorecard] = None
    alerts: Optional[List] = None


def run_paper_runtime(
    config: RuntimeConfig,
    registry: Optional[StrategyRegistry] = None,
) -> RuntimeResult:
    """Run the full paper trading runtime pipeline."""
    if registry is None:
        registry = create_default_registry()

    if not registry.has(config.strategy_name):
        return RuntimeResult(
            status="ERROR", strategy_name=config.strategy_name,
            fixtures_run=0, fixtures_failed=0, total_signals=0,
            total_plans=0, total_rejected=0, total_trades=0,
            total_pnl=0, win_rate=0, score=-100, rating="REJECT",
            alerts_written=0,
            safety_flags=["NO_REAL_ORDER", "NO_REAL_HTTP", "NO_SECRET_READ", "PAPER_ONLY"],
        )

    signal_fn = registry.get_signal_fn(config.strategy_name)
    alerts = LocalAlertBridge()

    total_signals = 0
    total_plans = 0
    total_rejected = 0
    total_trades = 0
    total_pnl = 0.0
    fixtures_run = 0
    fixtures_failed = 0
    all_metrics: List[PerformanceMetrics] = []

    for fixture_path in config.fixture_paths:
        try:
            bars = load_bars_from_fixture(fixture_path)
            if not bars:
                fixtures_failed += 1
                if config.enable_local_alerts:
                    alerts.warning("fixture", f"Empty fixture: {fixture_path}", "orchestrator")
                continue

            replay_config = ReplayConfig(
                risk_config=RiskSizingConfig(
                    max_risk_per_trade_pct=config.max_risk_per_trade_pct,
                    max_position_pct=config.max_position_pct,
                    min_rr_ratio=config.min_rr_ratio,
                    max_margin_cap=config.max_total_exposure,
                    equity=100000,
                ),
                exit_config=ExitRuleConfig(),
                portfolio_config=PortfolioRiskConfig(
                    max_open_plans=config.max_open_plans,
                    max_total_exposure=config.max_total_exposure,
                    max_daily_loss=config.max_daily_loss,
                ),
                auto_approve=True,
                use_portfolio_risk=True,
            )

            result = run_replay(bars, signal_fn, replay_config)
            total_signals += result.signals_generated
            total_plans += result.plans_created
            total_rejected += (result.plans_created - result.plans_approved + result.plans_portfolio_rejected)
            total_trades += result.trades_executed

            m = compute_metrics(result.ledger)
            all_metrics.append(m)
            total_pnl += m.total_pnl
            fixtures_run += 1

            if config.enable_local_alerts and m.max_consecutive_losses >= 3:
                alerts.critical("risk", f"Consecutive losses: {m.max_consecutive_losses}", "orchestrator")

        except Exception as e:
            fixtures_failed += 1
            if config.enable_local_alerts:
                alerts.warning("fixture", f"Error: {fixture_path}: {str(e)[:50]}", "orchestrator")

    # Aggregate
    if all_metrics:
        agg = _aggregate(all_metrics)
        sc = score_strategy(agg)
    else:
        agg = PerformanceMetrics(
            total_trades=0, winners=0, losers=0, breakevens=0,
            win_rate=0, total_pnl=0, avg_pnl_per_trade=0,
            avg_win=0, avg_loss=0, profit_factor=0,
            max_drawdown=0, max_consecutive_losses=0,
            avg_rr_actual=0, expectancy=0,
        )
        sc = score_strategy(agg)

    return RuntimeResult(
        status="OK" if fixtures_run > 0 else "NO_FIXTURES",
        strategy_name=config.strategy_name,
        fixtures_run=fixtures_run,
        fixtures_failed=fixtures_failed,
        total_signals=total_signals,
        total_plans=total_plans,
        total_rejected=total_rejected,
        total_trades=total_trades,
        total_pnl=round(total_pnl, 2),
        win_rate=round(agg.win_rate, 4),
        score=sc.final_score,
        rating=sc.rating.value,
        alerts_written=alerts.count,
        safety_flags=["NO_REAL_ORDER", "NO_REAL_HTTP", "NO_SECRET_READ", "NO_TESTNET", "NO_LIVE", "PAPER_ONLY"],
        metrics=agg,
        scorecard=sc,
        alerts=alerts.peek(),
    )


def _aggregate(metrics_list: List[PerformanceMetrics]) -> PerformanceMetrics:
    total_trades = sum(m.total_trades for m in metrics_list)
    winners = sum(m.winners for m in metrics_list)
    losers = sum(m.losers for m in metrics_list)
    breakevens = sum(m.breakevens for m in metrics_list)
    total_pnl = sum(m.total_pnl for m in metrics_list)
    max_dd = max(m.max_drawdown for m in metrics_list) if metrics_list else 0
    max_consec = max(m.max_consecutive_losses for m in metrics_list) if metrics_list else 0
    win_rate = winners / total_trades if total_trades > 0 else 0
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
    win_pnls = [m.avg_win * m.winners for m in metrics_list if m.winners > 0]
    loss_pnls = [m.avg_loss * m.losers for m in metrics_list if m.losers > 0]
    avg_win = sum(win_pnls) / winners if winners > 0 else 0
    avg_loss = sum(loss_pnls) / losers if losers > 0 else 0
    gross_profit = sum(m.avg_win * m.winners for m in metrics_list)
    gross_loss = abs(sum(m.avg_loss * m.losers for m in metrics_list))
    pf = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0)
    rr_vals = [m.avg_rr_actual for m in metrics_list if m.avg_rr_actual != 0]
    avg_rr = sum(rr_vals) / len(rr_vals) if rr_vals else 0
    expectancy = avg_win * win_rate + avg_loss * (1 - win_rate)
    return PerformanceMetrics(
        total_trades=total_trades, winners=winners, losers=losers, breakevens=breakevens,
        win_rate=win_rate, total_pnl=total_pnl, avg_pnl_per_trade=avg_pnl,
        avg_win=avg_win, avg_loss=avg_loss, profit_factor=pf,
        max_drawdown=max_dd, max_consecutive_losses=max_consec,
        avg_rr_actual=avg_rr, expectancy=expectancy,
    )
