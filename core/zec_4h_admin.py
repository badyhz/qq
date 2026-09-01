"""Read-only ZECUSDT 4H admin snapshot helpers.

This module intentionally has no trading write path.  It reads the existing
strategy state/ledger and authenticated PAPI account data through the same
adapter used by the live executor, always with ``live_enabled=False``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import time
from typing import Any, Iterable, Optional

from core.zec_4h_live import (
    FIXED_LEVERAGE,
    LIVE_CAPITAL_CAP_USDT,
    SIZING_BASE_USDT,
    STARTING_EQUITY,
    SYMBOL,
    TAKE_PROFIT_MODE,
    TARGET_INITIAL_NOTIONAL_USDT,
    LiveAction,
    LiveExecutionLedger,
    StrategyState,
    build_live_scorecard,
    load_strategy_state,
)
from core.zec_4h_live_execution import (
    BinanceUsdMExecutionAdapter,
    fixed_leverage_allowed,
    position_quantity,
    run_live_preflight,
    strategy_equity_from_evidence,
)
from core.zec_control import (
    DEFAULT_AUDIT_PATH,
    DEFAULT_CONFIG_PATH,
    RuntimeConfig,
    STRATEGY_REGISTRY,
    assert_safe_configuration_change,
    load_runtime_config,
    timeframe_seconds,
    update_runtime_config,
    validate_exchange_symbol,
)


DEFAULT_RUNTIME_DIR = Path("/var/lib/quant-shadow/zec-4h-small-live")
DEFAULT_STATE_PATH = DEFAULT_RUNTIME_DIR / "state.json"
DEFAULT_LEDGER_PATH = DEFAULT_RUNTIME_DIR / "execution_ledger.jsonl"
DEFAULT_SCORECARD_PATH = DEFAULT_RUNTIME_DIR / "scorecard.json"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value if value not in (None, "") else default)
    except (TypeError, ValueError):
        return float(default)


def _bool_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _iso_from_epoch_ms(value: Any) -> str:
    epoch_ms = int(_number(value))
    if epoch_ms <= 0:
        return ""
    return datetime.fromtimestamp(epoch_ms / 1000.0, timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    unkeyed: list[dict[str, Any]] = []
    for row in records:
        item = dict(row)
        key = str(item.get("signal_key", ""))
        if key:
            latest[key] = item
        else:
            unkeyed.append(item)
    rows = [*unkeyed, *latest.values()]
    return sorted(rows, key=lambda row: str(row.get("recorded_at", "")))


def build_closed_trade_sessions(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build completed strategy sessions from the append-only live ledger."""
    rows = _latest_records(records)
    sessions: list[dict[str, Any]] = []
    active: Optional[dict[str, Any]] = None

    for row in rows:
        action = str(row.get("action", ""))
        status = str(row.get("status", ""))
        filled_qty = _number(row.get("filled_qty"))
        executed = filled_qty > 0 and status == "FILLED"

        if executed and action == LiveAction.OPEN.value:
            if active is not None:
                # Corrupt/overlapping evidence should not be silently merged.
                active = None
            entry = _number(row.get("average_fill_price") or row.get("signal_price"))
            stop = _number(row.get("entry_low"))
            risk_usdt = max(entry - stop, 0.0) * filled_qty if entry > stop > 0 else 0.0
            active = {
                "open_time": str(row.get("recorded_at") or row.get("bar_close_time") or ""),
                "close_time": "",
                "entry_price": entry,
                "exit_price": 0.0,
                "initial_stop_price": stop,
                "initial_qty": filled_qty,
                "gross_pnl": 0.0,
                "fees": 0.0,
                "funding": 0.0,
                "net_pnl": 0.0,
                "risk_usdt": risk_usdt,
                "r_multiple": None,
                "exit_reason": "",
                "exit_action": "",
                "exit_order_id": "",
            }

        if active is None:
            continue

        if executed:
            active["gross_pnl"] += _number(row.get("realized_pnl"))
            active["fees"] += _number(row.get("fee"))
        if status == "ACCOUNT_INCOME":
            active["funding"] += _number(row.get("funding"))

        if executed and action in {
            LiveAction.STOP_CLOSE.value,
            LiveAction.TAKE_PROFIT_CLOSE.value,
            LiveAction.HARD_STOP_CLOSE.value,
        }:
            active["close_time"] = str(row.get("recorded_at") or row.get("bar_close_time") or "")
            active["exit_price"] = _number(row.get("average_fill_price") or row.get("signal_price"))
            active["exit_reason"] = str(row.get("reason", ""))
            active["exit_action"] = action
            active["exit_order_id"] = str(row.get("exchange_order_id", ""))
            active["net_pnl"] = (
                _number(active["gross_pnl"])
                - _number(active["fees"])
                + _number(active["funding"])
            )
            risk_usdt = _number(active["risk_usdt"])
            active["r_multiple"] = active["net_pnl"] / risk_usdt if risk_usdt > 0 else None
            sessions.append(active)
            active = None

    return sessions


def aggregate_exchange_fills(
    fills: Iterable[dict[str, Any]],
    records: Iterable[dict[str, Any]],
    sessions: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate possibly multi-fill PAPI user trades into one row per order."""
    latest = _latest_records(records)
    ledger_by_order = {
        str(row.get("exchange_order_id", "")): row
        for row in latest
        if str(row.get("exchange_order_id", ""))
    }
    session_by_exit_order = {
        str(row.get("exit_order_id", "")): row
        for row in sessions
        if str(row.get("exit_order_id", ""))
    }

    grouped: dict[str, dict[str, Any]] = {}
    for fill in fills:
        order_id = str(fill.get("orderId", fill.get("order_id", "")) or "")
        fallback = f"{fill.get('time','')}:{fill.get('side','')}:{fill.get('price','')}"
        key = order_id or fallback
        qty = abs(_number(fill.get("qty", fill.get("quantity", 0.0))))
        price = _number(fill.get("price"))
        quote = _number(fill.get("quoteQty"))
        if quote <= 0 and qty > 0 and price > 0:
            quote = qty * price
        row = grouped.setdefault(
            key,
            {
                "time_ms": int(_number(fill.get("time"))),
                "time": _iso_from_epoch_ms(fill.get("time")),
                "side": str(fill.get("side", "")).upper(),
                "position_side": str(fill.get("positionSide", "")).upper(),
                "price_qty_sum": 0.0,
                "qty": 0.0,
                "notional": 0.0,
                "fee": 0.0,
                "fee_asset": str(fill.get("commissionAsset", "")),
                "realized_pnl": 0.0,
                "order_id": order_id,
                "action": "",
                "exit_reason": "",
                "r_multiple": None,
            },
        )
        row["time_ms"] = max(row["time_ms"], int(_number(fill.get("time"))))
        row["time"] = _iso_from_epoch_ms(row["time_ms"])
        row["price_qty_sum"] += price * qty
        row["qty"] += qty
        row["notional"] += quote
        row["fee"] += _number(fill.get("commission"))
        row["realized_pnl"] += _number(fill.get("realizedPnl"))

    result: list[dict[str, Any]] = []
    for row in grouped.values():
        qty = _number(row["qty"])
        row["price"] = row.pop("price_qty_sum") / qty if qty > 0 else 0.0
        evidence = ledger_by_order.get(str(row["order_id"]), {})
        row["action"] = str(evidence.get("action", ""))
        row["exit_reason"] = str(evidence.get("reason", ""))
        session = session_by_exit_order.get(str(row["order_id"]))
        if session is not None:
            row["r_multiple"] = session.get("r_multiple")
        result.append(row)
    return sorted(result, key=lambda row: int(row.get("time_ms", 0)), reverse=True)


def _window_net_pnl(sessions: Iterable[dict[str, Any]], days: int, now: datetime) -> float:
    cutoff = now - timedelta(days=days)
    total = 0.0
    for row in sessions:
        closed_at = _parse_iso(row.get("close_time"))
        if closed_at is not None and closed_at >= cutoff:
            total += _number(row.get("net_pnl"))
    return total


def build_pnl_stats(
    *,
    sessions: list[dict[str, Any]],
    strategy_equity: float,
    unrealized_pnl: float,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    nets = [_number(row.get("net_pnl")) for row in sessions]
    wins = [value for value in nets if value > 0]
    losses = [value for value in nets if value < 0]
    total_strategy_pnl = float(strategy_equity) - STARTING_EQUITY
    realized_net = total_strategy_pnl - float(unrealized_pnl)
    gross_wins = sum(wins)
    gross_losses = abs(sum(losses))
    return {
        "strategy_equity": float(strategy_equity),
        "starting_equity": STARTING_EQUITY,
        "realized_net_pnl": realized_net,
        "unrealized_pnl": float(unrealized_pnl),
        "total_pnl": total_strategy_pnl,
        "closed_trades": len(sessions),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / len(sessions)) if sessions else None,
        "avg_win": (sum(wins) / len(wins)) if wins else None,
        "avg_loss": (sum(losses) / len(losses)) if losses else None,
        "profit_factor": (gross_wins / gross_losses) if gross_losses > 0 else None,
        "max_win": max(nets) if nets else None,
        "max_loss": min(nets) if nets else None,
        "pnl_7d": _window_net_pnl(sessions, 7, now),
        "pnl_30d": _window_net_pnl(sessions, 30, now),
        "sample_status": "OK" if len(sessions) >= 20 else "INSUFFICIENT_SAMPLE",
    }


def normalize_position(position: dict[str, Any], state: StrategyState) -> dict[str, Any]:
    qty = _number(position.get("positionAmt", position.get("quantity", 0.0)))
    entry = _number(position.get("entryPrice"))
    mark = _number(position.get("markPrice"))
    unrealized = _number(position.get("unRealizedProfit", position.get("unrealizedProfit", 0.0)))
    notional = abs(_number(position.get("notional")))
    if notional <= 0 and abs(qty) > 0 and mark > 0:
        notional = abs(qty) * mark
    margin_estimate = notional / FIXED_LEVERAGE if FIXED_LEVERAGE > 0 else 0.0
    roe = (unrealized / margin_estimate * 100.0) if margin_estimate > 0 else None
    stop = _number(state.stop_guard_price if state.stop_guard_active else state.entry_low)
    take_profit = _number(state.take_profit_price if state.take_profit_active else 0.0)
    return {
        "symbol": SYMBOL,
        "position_side": str(position.get("positionSide", "LONG" if qty > 0 else "BOTH")),
        "qty": qty,
        "entry_price": entry,
        "mark_price": mark,
        "notional": notional,
        "unrealized_pnl": unrealized,
        "roe_pct_estimate": roe,
        "liquidation_price": _number(position.get("liquidationPrice")),
        "stop_loss": stop if stop > 0 else None,
        "take_profit": take_profit if take_profit > 0 else None,
        "distance_to_sl_pct": ((mark - stop) / mark * 100.0) if mark > 0 and stop > 0 else None,
        "distance_to_tp_pct": ((take_profit - mark) / mark * 100.0) if mark > 0 and take_profit > 0 else None,
    }


def _signal_summary(state: StrategyState) -> dict[str, Any]:
    last_close = _parse_iso(state.last_processed_bar_close_time)
    next_close = (
        last_close + timedelta(seconds=timeframe_seconds(state.timeframe))
        if last_close is not None else None
    )
    return {
        "phase": state.phase,
        "last_signal": state.last_signal,
        "last_processed_bar_close_time": state.last_processed_bar_close_time,
        "next_expected_bar_close_time": next_close.isoformat(timespec="seconds") if next_close else "",
        "pending_action": state.pending_action,
        "recovery_status": state.recovery_status,
        "warmup_complete": state.warmup_complete,
    }


def _recent_events(records: Iterable[dict[str, Any]], limit: int = 25) -> list[dict[str, Any]]:
    rows = list(reversed(_latest_records(records)))[: max(1, int(limit))]
    keys = (
        "recorded_at",
        "bar_close_time",
        "action",
        "status",
        "reason",
        "filled_qty",
        "average_fill_price",
        "fee",
        "realized_pnl",
        "funding",
        "exchange_order_id",
    )
    return [{key: row.get(key) for key in keys} for row in rows]


def collect_control_snapshot(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    state_path: Path = DEFAULT_STATE_PATH,
    adapter: Optional[BinanceUsdMExecutionAdapter] = None,
) -> dict[str, Any]:
    config = load_runtime_config(
        config_path,
        create=True,
        initial_strategy_enabled=_bool_env("ZEC_4H_LIVE_ENABLED"),
    )
    state = load_strategy_state(state_path)
    available_symbols = [config.symbol]
    if adapter is not None:
        exchange_info = adapter.get_exchange_info()
        available_symbols = sorted({
            str(item.get("symbol", "")).upper()
            for item in exchange_info.get("symbols", [])
            if isinstance(item, dict)
            and str(item.get("status", "")).upper() == "TRADING"
            and str(item.get("quoteAsset", "")).upper() == "USDT"
            and str(item.get("contractType", "PERPETUAL")).upper() == "PERPETUAL"
        })
        if config.symbol not in available_symbols:
            available_symbols.append(config.symbol)
    return {
        "schema_version": config.schema_version,
        "revision": config.revision,
        "strategy_enabled": config.strategy_enabled,
        "strategy_id": config.strategy_id,
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "sizing_base_usdt": config.sizing_base_usdt,
        "capital_cap_usdt": config.capital_cap_usdt,
        "leverage": config.leverage,
        "target_initial_notional_usdt": config.sizing_base_usdt * config.leverage,
        "updated_at": config.updated_at,
        "last_processed_bar_close_time": state.last_processed_bar_close_time,
        "pending_action": state.pending_action,
        "recovery_status": state.recovery_status,
        "registry": [
            {
                "strategy_id": strategy_id,
                "name": definition["display_name"],
                "direction": definition["direction"],
                "allowed_timeframes": list(definition["allowed_timeframes"]),
            }
            for strategy_id, definition in STRATEGY_REGISTRY.items()
        ],
        "available_symbols": available_symbols,
        "mutable_fields": ["strategy_id", "symbol", "timeframe", "sizing_base_usdt"],
        "immutable_fields": ["capital_cap_usdt", "leverage"],
    }


def apply_control_change(
    changes: dict[str, Any],
    *,
    expected_revision: int,
    actor: str,
    adapter: BinanceUsdMExecutionAdapter,
    config_path: Path = DEFAULT_CONFIG_PATH,
    audit_path: Path = DEFAULT_AUDIT_PATH,
    state_path: Path = DEFAULT_STATE_PATH,
) -> RuntimeConfig:
    """Apply one settings/toggle request after read-only exchange guards."""
    current = load_runtime_config(config_path, create=True)
    # Emergency strategy disable is entirely local and must remain available
    # during an exchange/API outage. It never submits or cancels an order.
    if changes == {"strategy_enabled": False}:
        return update_runtime_config(
            config_path,
            expected_revision=expected_revision,
            changes=changes,
            audit_path=audit_path,
            actor=actor,
        )
    candidate_payload = current.to_dict()
    candidate_payload.update(changes)
    candidate_payload["revision"] = current.revision
    candidate = RuntimeConfig.from_dict(candidate_payload)
    validate_exchange_symbol(candidate, adapter.get_exchange_info())
    if not fixed_leverage_allowed(
        adapter.get_leverage_brackets(symbol=candidate.symbol),
        symbol=candidate.symbol,
        leverage=candidate.leverage,
        sizing_base_usdt=candidate.sizing_base_usdt,
    ):
        raise RuntimeError("FIXED_50X_NOT_ALLOWED_FOR_CONFIGURED_SYMBOL")
    state = load_strategy_state(state_path)
    position = adapter.get_position(symbol=current.symbol)
    open_orders = adapter.get_open_orders(symbol=current.symbol)
    candidate_position = position
    if candidate.symbol != current.symbol:
        candidate_position = adapter.get_position(symbol=candidate.symbol)
        open_orders = [
            *open_orders,
            *adapter.get_open_orders(symbol=candidate.symbol),
        ]
    guarded_qty = max(
        abs(position_quantity(position)),
        abs(position_quantity(candidate_position)),
    )
    assert_safe_configuration_change(
        current,
        candidate,
        position_qty=guarded_qty,
        open_order_count=len(open_orders),
        pending_action=state.pending_action,
        recovery_status=state.recovery_status,
    )
    if changes == {"strategy_enabled": True} and (
        guarded_qty > 0
        or open_orders
        or state.pending_action
        or state.recovery_status
    ):
        raise UnsafeConfigurationChange("ENABLE_REQUIRES_FLAT_QUIESCENT_ENGINE")
    if any(key in changes for key in {"strategy_id", "symbol", "timeframe", "sizing_base_usdt"}) and current.strategy_enabled:
        raise RuntimeError("STRATEGY_MUST_BE_DISABLED_FOR_SETTINGS_CHANGE")
    normalized = dict(changes)
    if normalized.get("strategy_enabled") is True:
        normalized["risk_increase_after_bar_close_time"] = str(
            state.last_processed_bar_close_time or ""
        )
    return update_runtime_config(
        config_path,
        expected_revision=expected_revision,
        changes=normalized,
        audit_path=audit_path,
        actor=actor,
    )


def collect_admin_snapshot(
    *,
    adapter: Optional[BinanceUsdMExecutionAdapter] = None,
    state_path: Path = DEFAULT_STATE_PATH,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Return one safe, read-only payload for the admin UI."""
    generated = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    config = load_runtime_config(config_path, create=False)
    state = load_strategy_state(Path(state_path))
    records = LiveExecutionLedger(Path(ledger_path)).read()
    sessions = build_closed_trade_sessions(records)

    api_key_present = bool(os.environ.get("ZEC_4H_BINANCE_API_KEY", "").strip())
    api_secret_present = bool(os.environ.get("ZEC_4H_BINANCE_API_SECRET", "").strip())
    if adapter is None and api_key_present and api_secret_present:
        adapter = BinanceUsdMExecutionAdapter(
            api_key=os.environ.get("ZEC_4H_BINANCE_API_KEY", ""),
            api_secret=os.environ.get("ZEC_4H_BINANCE_API_SECRET", ""),
            live_enabled=False,
        )

    payload: dict[str, Any] = {
        "generated_at": generated.isoformat(timespec="seconds"),
        "strategy": {
            "strategy_id": config.strategy_id,
            "symbol": config.symbol,
            "timeframe": config.timeframe,
            "direction": "LONG_ONLY",
            "account_mode": "PORTFOLIO_MARGIN",
            "api_mode": "PAPI",
            "capital_pool_usdt": config.capital_cap_usdt,
            "sizing_base_usdt": config.sizing_base_usdt,
            "leverage": config.leverage,
            "target_initial_notional_usdt": config.sizing_base_usdt * config.leverage,
            "take_profit_mode": TAKE_PROFIT_MODE,
        },
        "runtime": {
            "engine_running": (
                DEFAULT_SCORECARD_PATH.exists()
                and time.time() - DEFAULT_SCORECARD_PATH.stat().st_mtime <= 180
            ),
            "live_enabled": _bool_env("ZEC_4H_LIVE_ENABLED"),
            "real_order": _bool_env("ZEC_4H_LIVE_ENABLED")
            and os.environ.get("ZEC_4H_LIVE_ACTIVATION", "") == "zec_4h_live_v1",
            "preflight_enabled": _bool_env("ZEC_4H_PREFLIGHT_ENABLED"),
            "strategy_enabled": config.strategy_enabled,
            "config_revision": config.revision,
            "credential_key_present": api_key_present,
            "credential_secret_present": api_secret_present,
        },
        "signal": _signal_summary(state),
        "position": normalize_position({}, state),
        "open_orders": [],
        "history": [],
        "closed_sessions": list(reversed(sessions)),
        "pnl": build_pnl_stats(
            sessions=sessions,
            strategy_equity=STARTING_EQUITY,
            unrealized_pnl=0.0,
            now=generated,
        ),
        "health": {
            "api_authentication": False,
            "portfolio_margin_access": False,
            "trading_permission": False,
            "withdraw_permission": "UNKNOWN",
            "ip_restricted": False,
            "zecusdt_50x_allowed": False,
            "account_leverage": None,
            "position_mode": "UNKNOWN",
            "preflight_pass": False,
            "error": "CREDENTIALS_UNAVAILABLE" if adapter is None else "",
        },
        "recent_events": _recent_events(records),
    }

    if adapter is None:
        return payload

    try:
        position = adapter.get_position(symbol=config.symbol)
        open_orders = adapter.get_open_orders(symbol=config.symbol)
        fills = adapter.get_fills(symbol=config.symbol)
        equity = strategy_equity_from_evidence(records, position)
        preflight = run_live_preflight(
            adapter,
            withdrawal_disabled_verified=_bool_env("ZEC_4H_WITHDRAWAL_DISABLED_VERIFIED"),
        )
        normalized_position = normalize_position(position, state)
        scorecard = build_live_scorecard(
            records,
            current_equity=equity,
            current_position=position,
            current_open_orders=open_orders,
            strategy_state=state,
            runtime_config=config,
        )
        payload["position"] = normalized_position
        payload["open_orders"] = open_orders
        payload["history"] = aggregate_exchange_fills(fills, records, sessions)
        payload["pnl"] = build_pnl_stats(
            sessions=sessions,
            strategy_equity=equity,
            unrealized_pnl=_number(normalized_position.get("unrealized_pnl")),
            now=generated,
        )
        payload["scorecard"] = {
            key: scorecard.get(key)
            for key in (
                "current_equity",
                "net_profit",
                "closed_trades",
                "win_rate",
                "net_profit_factor",
                "maximum_drawdown",
                "actual_fees",
                "actual_funding",
                "generated_at",
            )
        }
        payload["health"] = {
            "api_authentication": preflight.get("api_authentication") is True,
            "portfolio_margin_access": preflight.get("portfolio_margin_access") is True,
            "trading_permission": preflight.get("trading_permission") is True,
            "withdraw_permission": preflight.get("withdraw_permission", "UNKNOWN"),
            "ip_restricted": preflight.get("ip_restricted") is True,
            "zecusdt_50x_allowed": preflight.get("zecusdt_50x_allowed") is True,
            "account_leverage": preflight.get("account_leverage"),
            "position_mode": preflight.get("position_mode", "UNKNOWN"),
            "available_balance": preflight.get("available_balance"),
            "clock_skew_ms": preflight.get("clock_skew_ms"),
            "preflight_pass": preflight.get("preflight_pass") is True,
            "error": preflight.get("error", ""),
        }
    except Exception as exc:
        # Never serialize exception text: remote bodies can contain account data.
        payload["health"]["error"] = exc.__class__.__name__
        payload["health"]["preflight_pass"] = False

    return payload
