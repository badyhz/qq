#!/usr/bin/env python3
"""Guarded runner for zec_4h_live_v1; disabled unless explicitly provisioned."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.paper_trading.data_source import DataSourceConfig, select_closed_bars
from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter
from core.zec_4h_live import (
    LiveExecutionLedger,
    StrategyDecision,
    StrategyState,
    Zec4hStrategy,
    build_live_scorecard,
    load_strategy_state,
    save_strategy_state,
)
from core.zec_4h_live_execution import (
    BinanceUsdMExecutionAdapter,
    LiveExecutionEngine,
    UNKNOWN_STATUS,
    account_equity,
    extract_symbol_rules,
    reconcile_startup,
    run_live_preflight,
    strategy_equity_from_evidence,
    usdt_available_balance,
    verify_dedicated_account_boundary,
)


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _assert_activation() -> None:
    if not _enabled("ZEC_4H_LIVE_ENABLED"):
        raise RuntimeError("ZEC_4H_LIVE_DISABLED")
    if os.environ.get("ZEC_4H_LIVE_ACTIVATION", "") != "zec_4h_live_v1":
        raise RuntimeError("ZEC_4H_LIVE_ACTIVATION_MISSING")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _adapter(*, live_enabled: bool) -> BinanceUsdMExecutionAdapter:
    api_key = os.environ.get("ZEC_4H_BINANCE_API_KEY", "")
    api_secret = os.environ.get("ZEC_4H_BINANCE_API_SECRET", "")
    if not api_key or not api_secret:
        raise RuntimeError("BINANCE_LIVE_CREDENTIALS_MISSING")
    return BinanceUsdMExecutionAdapter(
        api_key=api_key,
        api_secret=api_secret,
        live_enabled=live_enabled,
    )


def run_preflight_only() -> dict:
    if not _enabled("ZEC_4H_PREFLIGHT_ENABLED"):
        raise RuntimeError("ZEC_4H_PREFLIGHT_DISABLED")
    return run_live_preflight(
        _adapter(live_enabled=False),
        withdrawal_disabled_verified=_enabled("ZEC_4H_WITHDRAWAL_DISABLED_VERIFIED"),
    )


def _decision_from_record(row: dict) -> StrategyDecision:
    return StrategyDecision(
        action=str(row.get("action", "")),
        signal_key=str(row.get("signal_key", "")),
        client_order_id=str(row.get("client_order_id", "")),
        bar_close_time=str(row.get("bar_close_time", "")),
        signal_price=float(row.get("signal_price", 0.0) or 0.0),
        entry_low=(float(row["entry_low"]) if row.get("entry_low") is not None else None),
        reason=str(row.get("reason", "RECOVERED_FROM_LEDGER")),
    )


def _pending_record(ledger: LiveExecutionLedger) -> dict | None:
    latest: dict[str, dict] = {}
    for row in ledger.read():
        if row.get("signal_key"):
            latest[str(row["signal_key"])] = row
    pending = [
        row for row in latest.values()
        if row.get("status") in {"SIGNAL_CONFIRMED", "SUBMITTING", "NEW", "PARTIALLY_FILLED", UNKNOWN_STATUS}
    ]
    if len(pending) > 1:
        raise RuntimeError("MULTIPLE_PENDING_LIVE_ORDERS")
    return pending[0] if pending else None


def run_cycle(
    *,
    state_path: Path,
    ledger_path: Path,
    scorecard_path: Path,
) -> dict:
    _assert_activation()
    adapter = _adapter(live_enabled=True)
    ledger = LiveExecutionLedger(ledger_path)
    state = load_strategy_state(state_path)
    engine = LiveExecutionEngine(adapter, ledger)

    # Initial provisioning is strictly no-order and must prove the dedicated
    # account starts near 50 USDT.  Subsequent restarts recover from ledger.
    if not ledger.read():
        preflight = run_live_preflight(
            adapter,
            withdrawal_disabled_verified=_enabled("ZEC_4H_WITHDRAWAL_DISABLED_VERIFIED"),
        )
        if preflight.get("preflight_pass") is not True:
            raise RuntimeError("LIVE_PREFLIGHT_BLOCKED")

    recovery = reconcile_startup(state, ledger, adapter)
    if recovery.get("ok") is not True:
        raise RuntimeError(f"STARTUP_RECONCILIATION_BLOCKED:{recovery.get('reason')}")
    engine.sync_funding_income()
    equity = strategy_equity_from_evidence(ledger.read(), adapter.get_position())
    boundary = verify_dedicated_account_boundary(
        exchange_equity=account_equity(adapter.get_account()),
        strategy_equity=equity,
    )
    if boundary.get("ok") is not True:
        raise RuntimeError("DEDICATED_ACCOUNT_BOUNDARY_BLOCKED")

    pending = _pending_record(ledger)
    if pending is not None:
        recovered_decision = _decision_from_record(pending)
        if pending.get("status") == UNKNOWN_STATUS:
            result = engine.execute(
                recovered_decision,
                state,
                    strategy_equity=equity,
                    exchange_available_balance=usdt_available_balance(adapter.get_balance()),
                    mark_price=float(pending.get("signal_price", 0.0) or 0.0),
                symbol_rules=extract_symbol_rules(adapter.get_exchange_info()),
            )
        else:
            result = engine.reconcile_order(
                recovered_decision,
                state,
                strategy_equity=equity,
            )
        save_strategy_state(state_path, state)
    else:
        source = BinancePublicKlineAdapter(
            DataSourceConfig(mode="snapshot", symbol="ZECUSDT", timeframe="4h", network_enabled=True)
        )
        raw_bars = source.get_bars("ZECUSDT", "4h", limit=200)
        selected = select_closed_bars(raw_bars, datetime.now(timezone.utc))
        if len(selected.bars) < 28:
            raise RuntimeError("INSUFFICIENT_CANONICAL_CLOSED_BARS")
        strategy = Zec4hStrategy()
        if state.last_processed_bar_close_time is None:
            strategy.initialize_baseline(selected.bars, state)
            save_strategy_state(state_path, state)
            result = {"ok": True, "submitted": False, "reason": "BASELINE_INITIALIZED"}
        else:
            position = adapter.get_position()
            decision = strategy.evaluate(
                selected.bars,
                state,
                strategy_equity=equity,
                actual_position_qty=float(position.get("positionAmt", 0.0) or 0.0),
            )
            if decision.action:
                rules = extract_symbol_rules(adapter.get_exchange_info())
                result = engine.execute(
                    decision,
                    state,
                    strategy_equity=equity,
                    exchange_available_balance=usdt_available_balance(adapter.get_balance()),
                    mark_price=decision.signal_price,
                    symbol_rules=rules,
                )
            else:
                result = {"ok": True, "submitted": False, "reason": decision.reason}
            save_strategy_state(state_path, state)

    engine.sync_funding_income()
    position = adapter.get_position()
    open_orders = adapter.get_open_orders()
    current_strategy_equity = strategy_equity_from_evidence(ledger.read(), position)
    scorecard = build_live_scorecard(
        ledger.read(),
        current_equity=current_strategy_equity,
        current_position=position,
        current_open_orders=open_orders,
        strategy_state=state,
    )
    _write_json(scorecard_path, scorecard)
    return {"result": result, "scorecard": scorecard}


def main() -> int:
    parser = argparse.ArgumentParser(description="ZECUSDT 4H small-live runner (default disabled)")
    parser.add_argument("--state", type=Path, default=Path("/var/lib/quant-shadow/zec-4h-small-live/state.json"))
    parser.add_argument("--ledger", type=Path, default=Path("/var/lib/quant-shadow/zec-4h-small-live/execution_ledger.jsonl"))
    parser.add_argument("--scorecard", type=Path, default=Path("/var/lib/quant-shadow/zec-4h-small-live/scorecard.json"))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args()
    try:
        if args.preflight_only:
            payload = run_preflight_only()
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return 0 if payload.get("preflight_pass") is True else 2
        while True:
            payload = run_cycle(state_path=args.state, ledger_path=args.ledger, scorecard_path=args.scorecard)
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            if args.once:
                return 0
            time.sleep(max(30, args.poll_seconds))
    except Exception as exc:
        # Deliberately omit exception details that could contain a remote body.
        print(json.dumps({"result": "BLOCKED", "error": exc.__class__.__name__}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
