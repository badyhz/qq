import csv
import math
from pathlib import Path
from typing import Any, Iterable, Union


def load_trade_rows(csv_path: Union[str, Path]) -> list[dict]:
    path = Path(csv_path)
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize_trade_stats(trades_or_path: Union[str, Path, Iterable[dict]]) -> dict:
    if isinstance(trades_or_path, (str, Path)):
        trades = load_trade_rows(trades_or_path)
    else:
        trades = list(trades_or_path)

    total_trades = len(trades)
    closed_trades = []
    for trade in trades:
        if _is_closed_trade(trade):
            closed_trades.append(trade)

    net_pnls = [_resolve_net_pnl(trade) for trade in closed_trades]
    equity_curve = _build_equity_curve(net_pnls)
    peak_equity, max_drawdown, max_drawdown_pct = _compute_drawdowns(equity_curve)
    winning_pnls = [pnl for pnl in net_pnls if pnl > 0]
    losing_pnls = [pnl for pnl in net_pnls if pnl < 0]
    fee_total = sum(_resolve_fee_total(trade) for trade in closed_trades)
    avg_fee_per_trade = (fee_total / len(closed_trades)) if closed_trades else 0.0

    closed_count = len(closed_trades)
    win_count = len(winning_pnls)
    loss_count = len(losing_pnls)
    gross_profit = sum(winning_pnls)
    gross_loss = sum(losing_pnls)
    net_profit = sum(net_pnls)
    win_rate = (win_count / closed_count) if closed_count else 0.0
    average_pnl = (net_profit / closed_count) if closed_count else 0.0
    average_win = (gross_profit / win_count) if win_count else 0.0
    average_loss = (gross_loss / loss_count) if loss_count else 0.0

    if gross_loss < 0:
        profit_factor = gross_profit / abs(gross_loss)
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    expectancy = (win_rate * average_win) + ((1.0 - win_rate) * average_loss)
    expectancy_long = _compute_expectancy_by_side(closed_trades, "LONG")
    expectancy_short = _compute_expectancy_by_side(closed_trades, "SHORT")
    avg_holding_seconds = _compute_avg_holding_seconds(closed_trades)
    pnl_std = _compute_pnl_std(net_pnls)
    max_win = max(net_pnls) if net_pnls else 0.0
    max_loss = min(net_pnls) if net_pnls else 0.0
    max_consecutive_wins, max_consecutive_losses = _compute_streaks(net_pnls)

    return {
        "total_trades": total_trades,
        "closed_trades": closed_count,
        "win_trades": win_count,
        "loss_trades": loss_count,
        "win_rate": win_rate,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_profit": net_profit,
        "average_pnl": average_pnl,
        "average_win": average_win,
        "average_loss": average_loss,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "max_win": max_win,
        "max_loss": max_loss,
        "max_consecutive_wins": max_consecutive_wins,
        "max_consecutive_losses": max_consecutive_losses,
        "equity_curve": equity_curve,
        "peak_equity": peak_equity,
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown_pct,
        "fee_total": fee_total,
        "avg_fee_per_trade": avg_fee_per_trade,
        "expectancy_long": expectancy_long,
        "expectancy_short": expectancy_short,
        "avg_holding_seconds": avg_holding_seconds,
        "pnl_std": pnl_std,
    }


def _compute_streaks(net_pnls: list[float]) -> tuple[int, int]:
    current_wins = 0
    current_losses = 0
    max_wins = 0
    max_losses = 0

    for pnl in net_pnls:
        if pnl > 0:
            current_wins += 1
            current_losses = 0
        elif pnl < 0:
            current_losses += 1
            current_wins = 0
        else:
            current_wins = 0
            current_losses = 0

        max_wins = max(max_wins, current_wins)
        max_losses = max(max_losses, current_losses)

    return max_wins, max_losses


def _is_closed_trade(trade: dict) -> bool:
    status = str(trade.get("status", "")).strip().upper()
    if status:
        return status == "CLOSED"
    close_time = str(trade.get("close_time") or trade.get("exit_time") or "").strip()
    return bool(close_time)


def _resolve_net_pnl(trade: dict) -> float:
    if trade.get("net_pnl", "") not in ("", None):
        return _to_float(trade.get("net_pnl", 0.0))
    return _to_float(trade.get("pnl", 0.0))


def _resolve_fee_total(trade: dict) -> float:
    if trade.get("total_cost", "") not in ("", None):
        return _to_float(trade.get("total_cost", 0.0))
    if trade.get("fees_total", "") not in ("", None):
        return _to_float(trade.get("fees_total", 0.0))
    return _to_float(trade.get("fee_open", 0.0)) + _to_float(trade.get("fee_close", 0.0))


def _build_equity_curve(net_pnls: list[float]) -> list[float]:
    curve = []
    equity = 0.0
    for pnl in net_pnls:
        equity += pnl
        curve.append(equity)
    return curve


def _compute_drawdowns(equity_curve: list[float]) -> tuple[float, float, float]:
    if not equity_curve:
        return 0.0, 0.0, 0.0

    peak_equity = 0.0
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    for equity in equity_curve:
        peak_equity = max(peak_equity, equity)
        drawdown = peak_equity - equity
        max_drawdown = max(max_drawdown, drawdown)
        if peak_equity > 0:
            max_drawdown_pct = max(max_drawdown_pct, drawdown / peak_equity)
    return peak_equity, max_drawdown, max_drawdown_pct


def _compute_expectancy_by_side(trades: list[dict], side: str) -> float:
    side_trades = []
    expected_side = str(side).upper()
    for trade in trades:
        if str(trade.get("side", "")).strip().upper() == expected_side:
            side_trades.append(trade)
    if not side_trades:
        return 0.0

    net_pnls = [_resolve_net_pnl(trade) for trade in side_trades]
    winning_pnls = [pnl for pnl in net_pnls if pnl > 0]
    losing_pnls = [pnl for pnl in net_pnls if pnl < 0]
    trade_count = len(net_pnls)
    if trade_count == 0:
        return 0.0

    win_rate = len(winning_pnls) / trade_count
    average_win = (sum(winning_pnls) / len(winning_pnls)) if winning_pnls else 0.0
    average_loss = (sum(losing_pnls) / len(losing_pnls)) if losing_pnls else 0.0
    return (win_rate * average_win) + ((1.0 - win_rate) * average_loss)


def _compute_avg_holding_seconds(trades: list[dict]) -> float:
    holding_seconds = []
    for trade in trades:
        raw_value = trade.get("holding_seconds", "")
        if raw_value in ("", None):
            continue
        holding_seconds.append(_to_float(raw_value, default=0.0))
    if not holding_seconds:
        return 0.0
    return sum(holding_seconds) / len(holding_seconds)


def _compute_pnl_std(net_pnls: list[float]) -> float:
    count = len(net_pnls)
    if count == 0:
        return 0.0
    mean_value = sum(net_pnls) / count
    variance = sum((pnl - mean_value) ** 2 for pnl in net_pnls) / count
    return math.sqrt(variance)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
