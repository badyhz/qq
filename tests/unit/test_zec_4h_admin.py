from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import base64
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from core.zec_4h_admin import (
    apply_control_change,
    aggregate_exchange_fills,
    build_closed_trade_sessions,
    build_pnl_stats,
    collect_admin_snapshot,
)
from core.zec_4h_live import StrategyState, save_strategy_state
from core.zec_control import RuntimeConfig, load_runtime_config, write_runtime_config
from scripts.run_zec_4h_admin import HTML
import scripts.run_zec_4h_admin as admin_runner


def _record(
    *,
    signal_key: str,
    action: str,
    status: str = "FILLED",
    qty: float = 0.25,
    price: float = 100.0,
    entry_low: float | None = None,
    fee: float = 0.01,
    realized_pnl: float = 0.0,
    order_id: str = "",
    recorded_at: str,
    reason: str = "",
):
    return {
        "strategy_id": "zec_4h_live_v1",
        "signal_key": signal_key,
        "bar_close_time": recorded_at,
        "action": action,
        "status": status,
        "requested_qty": qty,
        "filled_qty": qty if status == "FILLED" else 0.0,
        "average_fill_price": price,
        "signal_price": price,
        "entry_low": entry_low,
        "fee": fee if status == "FILLED" else 0.0,
        "funding": 0.0,
        "realized_pnl": realized_pnl,
        "exchange_order_id": order_id,
        "reason": reason,
        "recorded_at": recorded_at,
    }


def test_closed_trade_sessions_and_simple_pnl():
    records = [
        _record(signal_key="open", action="OPEN", price=100, entry_low=98, fee=0.01, order_id="1", recorded_at="2026-08-01T00:00:00+00:00"),
        {"strategy_id": "zec_4h_live_v1", "signal_key": "funding", "bar_close_time": "2026-08-01T04:00:00+00:00", "action": "FUNDING_PAYMENT", "status": "ACCOUNT_INCOME", "filled_qty": 0.0, "funding": -0.002, "recorded_at": "2026-08-01T04:00:00+00:00"},
        _record(signal_key="close", action="TAKE_PROFIT_CLOSE", qty=0.25, price=104, fee=0.01, realized_pnl=1.0, order_id="2", recorded_at="2026-08-02T00:00:00+00:00", reason="CLOSED_BAR_AT_OR_ABOVE_FIXED_2R"),
    ]
    sessions = build_closed_trade_sessions(records)
    assert len(sessions) == 1
    assert sessions[0]["net_pnl"] == pytest.approx(0.978)
    assert sessions[0]["r_multiple"] == pytest.approx(0.978 / 0.5)
    stats = build_pnl_stats(sessions=sessions, strategy_equity=50.978, unrealized_pnl=0.0, now=datetime(2026, 8, 3, tzinfo=timezone.utc))
    assert stats["closed_trades"] == 1
    assert stats["win_rate"] == pytest.approx(1.0)
    assert stats["total_pnl"] == pytest.approx(0.978)
    assert stats["pnl_7d"] == pytest.approx(0.978)
    assert stats["sample_status"] == "INSUFFICIENT_SAMPLE"


def test_exchange_fills_are_aggregated_by_order_and_annotated():
    records = [_record(signal_key="close", action="STOP_CLOSE", qty=0.25, price=99, fee=0.02, realized_pnl=-0.25, order_id="88", recorded_at="2026-08-02T00:00:00+00:00", reason="CLOSED_BAR_BELOW_ENTRY_LOW")]
    fills = [
        {"orderId": 88, "time": 1785628800000, "side": "SELL", "positionSide": "LONG", "price": "99", "qty": "0.10", "quoteQty": "9.9", "commission": "0.001", "commissionAsset": "USDT", "realizedPnl": "-0.1"},
        {"orderId": 88, "time": 1785628801000, "side": "SELL", "positionSide": "LONG", "price": "98", "qty": "0.15", "quoteQty": "14.7", "commission": "0.002", "commissionAsset": "USDT", "realizedPnl": "-0.15"},
    ]
    history = aggregate_exchange_fills(fills, records, [])
    assert len(history) == 1
    assert history[0]["qty"] == pytest.approx(0.25)
    assert history[0]["price"] == pytest.approx((99 * 0.1 + 98 * 0.15) / 0.25)
    assert history[0]["fee"] == pytest.approx(0.003)
    assert history[0]["realized_pnl"] == pytest.approx(-0.25)
    assert history[0]["action"] == "STOP_CLOSE"
    assert history[0]["exit_reason"] == "CLOSED_BAR_BELOW_ENTRY_LOW"


def test_dashboard_snapshot_request_is_relative_for_subpath_proxying():
    assert "fetch('api/snapshot'" in HTML
    assert "fetch('/api/snapshot'" not in HTML


class FakeReadOnlyAdapter:
    def __init__(self):
        self.write_calls = 0

    def get_exchange_info(self):
        return {"symbols": [{"symbol": "ZECUSDT", "status": "TRADING", "quoteAsset": "USDT", "contractType": "PERPETUAL", "pricePrecision": 2, "quantityPrecision": 3, "filters": [{"filterType": "PRICE_FILTER", "tickSize": "0.01"}, {"filterType": "MARKET_LOT_SIZE", "stepSize": "0.001", "minQty": "0.001"}, {"filterType": "MIN_NOTIONAL", "notional": "5"}]}]}

    def get_server_time(self): return {"serverTime": int(datetime.now(timezone.utc).timestamp() * 1000)}
    def get_account(self): return {"assets": [{"asset": "USDT", "crossWalletBalance": "50", "crossUnPnl": "0"}]}
    def get_balance(self): return [{"asset": "USDT", "availableBalance": "50"}]
    def get_position(self, symbol="ZECUSDT"): return {"symbol": symbol, "positionAmt": "0", "positionSide": "LONG", "entryPrice": "0", "markPrice": "101.5", "unRealizedProfit": "0"}
    def get_open_orders(self, symbol="ZECUSDT"): return []
    def get_symbol_config(self, symbol="ZECUSDT"): return {"symbol": symbol, "leverage": 50}
    def get_leverage_brackets(self, symbol="ZECUSDT"): return [{"symbol": symbol, "brackets": [{"initialLeverage": 50, "notionalFloor": 0, "notionalCap": 10000}]}]
    def get_position_mode(self): return {"dualSidePosition": True}
    def get_api_restrictions(self): return {"enablePortfolioMarginTrading": True, "enableWithdrawals": False, "ipRestrict": True}
    def get_fills(self, symbol="ZECUSDT", order_id=""): return []
    def set_leverage(self, *args, **kwargs): self.write_calls += 1; raise AssertionError("read-only admin must not write")
    def submit_market_order(self, *args, **kwargs): self.write_calls += 1; raise AssertionError("read-only admin must not write")
    def cancel_order(self, *args, **kwargs): self.write_calls += 1; raise AssertionError("read-only admin must not write")


def test_collect_snapshot_is_read_only_and_uses_existing_strategy_contract(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ZEC_4H_WITHDRAWAL_DISABLED_VERIFIED", "true")
    monkeypatch.setenv("ZEC_4H_LIVE_ENABLED", "false")
    adapter = FakeReadOnlyAdapter()
    payload = collect_admin_snapshot(adapter=adapter, state_path=tmp_path / "state.json", ledger_path=tmp_path / "ledger.jsonl")
    assert adapter.write_calls == 0
    assert payload["strategy"]["capital_pool_usdt"] == pytest.approx(50)
    assert payload["strategy"]["sizing_base_usdt"] == pytest.approx(0.5)
    assert payload["strategy"]["leverage"] == 50
    assert payload["strategy"]["target_initial_notional_usdt"] == pytest.approx(25)
    assert payload["runtime"]["live_enabled"] is False
    assert payload["runtime"]["real_order"] is False
    assert payload["health"]["api_authentication"] is True
    assert payload["health"]["portfolio_margin_access"] is True
    assert payload["health"]["trading_permission"] is True
    assert payload["health"]["withdraw_permission"] == "OFF"
    assert payload["health"]["ip_restricted"] is True
    assert payload["health"]["zecusdt_50x_allowed"] is True
    assert payload["health"]["position_mode"] == "HEDGE"
    assert payload["health"]["preflight_pass"] is True


def test_control_http_is_same_origin_json_only_and_has_no_order_endpoint(monkeypatch):
    monkeypatch.setenv("ZEC_4H_ADMIN_USER", "admin")
    monkeypatch.setenv("ZEC_4H_ADMIN_PASSWORD", "password")
    current = {
        "revision": 1, "strategy_enabled": False, "strategy_id": "zec_4h_live_v1",
        "symbol": "ZECUSDT", "timeframe": "4h", "sizing_base_usdt": 0.5,
    }
    calls = []
    monkeypatch.setattr(admin_runner, "collect_control_snapshot", lambda: dict(current))
    monkeypatch.setattr(admin_runner.AdminHandler, "_control_adapter", staticmethod(lambda: object()))
    monkeypatch.setattr(
        admin_runner,
        "apply_control_change",
        lambda changes, **kwargs: calls.append((dict(changes), dict(kwargs))),
    )
    server = admin_runner.ThreadingHTTPServer(("127.0.0.1", 0), admin_runner.AdminHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"127.0.0.1:{server.server_port}"
    auth = "Basic " + base64.b64encode(b"admin:password").decode()

    def request(path, *, body=None, origin=True):
        headers = {"Authorization": auth}
        if body is not None:
            headers["Content-Type"] = "application/json"
            if origin:
                headers["Origin"] = f"http://{host}"
        return urlopen(Request(f"http://{host}{path}", data=body, headers=headers), timeout=2)

    try:
        assert json.loads(request("/api/control").read())["revision"] == 1
        payload = json.dumps({
            "expected_revision": 1,
            "strategy_id": "zec_4h_live_v1",
            "symbol": "BTCUSDT",
            "timeframe": "4h",
            "sizing_base_usdt": 0.5,
        }).encode()
        assert request("/api/control/settings", body=payload).status == 200
        assert calls[0][0]["symbol"] == "BTCUSDT"
        with pytest.raises(HTTPError) as no_origin:
            request("/api/control/strategy/enable", body=b'{"expected_revision":1}', origin=False)
        assert no_origin.value.code == 403
        with pytest.raises(HTTPError) as no_order:
            request("/api/order", body=b"{}")
        assert no_order.value.code == 405
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_emergency_disable_never_depends_on_exchange_and_enable_sets_boundary(tmp_path: Path):
    config_path = tmp_path / "control" / "runtime.json"
    audit_path = tmp_path / "control" / "audit.jsonl"
    state_path = tmp_path / "live" / "state.json"
    write_runtime_config(config_path, RuntimeConfig(strategy_enabled=True))

    class NoExchangeCalls:
        def __getattr__(self, name):
            raise AssertionError(f"disable must not call exchange: {name}")

    disabled = apply_control_change(
        {"strategy_enabled": False},
        expected_revision=1,
        actor="admin",
        adapter=NoExchangeCalls(),
        config_path=config_path,
        audit_path=audit_path,
        state_path=state_path,
    )
    assert disabled.strategy_enabled is False

    boundary = "2026-09-01T04:00:00+00:00"
    save_strategy_state(state_path, StrategyState(last_processed_bar_close_time=boundary))
    enabled = apply_control_change(
        {"strategy_enabled": True},
        expected_revision=disabled.revision,
        actor="admin",
        adapter=FakeReadOnlyAdapter(),
        config_path=config_path,
        audit_path=audit_path,
        state_path=state_path,
    )
    assert enabled.strategy_enabled is True
    assert enabled.risk_increase_after_bar_close_time == boundary
    assert load_runtime_config(config_path).revision == 3
