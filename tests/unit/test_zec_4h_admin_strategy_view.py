from __future__ import annotations

from scripts.zec_4h_admin_strategy_view import HTML, repair_admin_snapshot


def test_strategy_history_hides_unmatched_account_fills_and_separates_times():
    payload = {
        "strategy": {"strategy_id": "zec_4h_live_v1", "symbol": "ZECUSDT"},
        "history": [
            {
                "time": "2026-09-04T13:55:11+00:00",
                "side": "BUY",
                "price": 992.54,
                "qty": 0.342,
                "notional": 339.4487,
                "fee": 0.169724,
                "fee_asset": "USDT",
                "realized_pnl": -0.4822,
                "order_id": "805401820466",
                "action": "",
                "exit_reason": "",
            },
            {
                "time": "2026-09-06T20:00:03+00:00",
                "side": "BUY",
                "price": 1005.0,
                "qty": 0.025,
                "notional": 25.125,
                "fee": 0.012,
                "fee_asset": "USDT",
                "realized_pnl": 0.0,
                "order_id": "strategy-1",
                "action": "OPEN",
                "exit_reason": "",
            },
        ],
    }
    records = [
        {
            "strategy_id": "zec_4h_live_v1",
            "symbol": "ZECUSDT",
            "signal_key": "zec_4h_live_v1:ZECUSDT:4h:20260906T200000Z:OPEN",
            "bar_close_time": "2026-09-06T20:00:00+00:00",
            "action": "OPEN",
            "status": "FILLED",
            "reason": "BUY_FALSE_TO_TRUE",
            "filled_qty": 0.025,
            "average_fill_price": 1005.0,
            "exchange_order_id": "strategy-1",
            "recorded_at": "2026-09-06T20:00:04+00:00",
        },
        {
            "strategy_id": "zec_4h_live_v1",
            "symbol": "ZECUSDT",
            "signal_key": "zec_4h_live_v1:ZECUSDT:4h:20260902T200000Z:OPEN",
            "bar_close_time": "2026-09-02T20:00:00+00:00",
            "action": "OPEN",
            "status": "MISSED_STALE_ENTRY",
            "reason": "STALE_RISK_INCREASE_BLOCKED",
            "filled_qty": 0.0,
            "average_fill_price": 0.0,
            "exchange_order_id": "",
            "recorded_at": "2026-09-03T13:10:46.648+00:00",
        },
    ]

    fixed = repair_admin_snapshot(payload, records)

    assert len(fixed["history"]) == 1
    row = fixed["history"][0]
    assert row["order_id"] == "strategy-1"
    assert row["strategy_owned"] is True
    assert row["signal_bar_close_time"] == "2026-09-06T20:00:00+00:00"
    assert row["fill_time"] == "2026-09-06T20:00:03+00:00"
    assert row["recorded_at"] == "2026-09-06T20:00:04+00:00"
    assert row["signal_time_cn"] == "2026-09-07 04:00:00"
    assert row["fill_time_cn"] == "2026-09-07 04:00:03"
    assert "SMA27" in row["signal_reason_cn"]
    assert "DIF" in row["signal_reason_cn"]

    stale = next(item for item in fixed["recent_events"] if item["status"] == "MISSED_STALE_ENTRY")
    assert stale["signal_time_cn"] == "2026-09-03 04:00:00"
    assert stale["record_time_cn"] == "2026-09-03 21:10:46"
    assert stale["filled_qty"] == 0.0
    assert "禁止补开仓" in stale["reason_cn"]


def test_strategy_history_is_scoped_by_symbol_and_strategy():
    payload = {
        "strategy": {"strategy_id": "zec_4h_live_v1", "symbol": "ZECUSDT"},
        "history": [{"time": "2026-09-01T00:00:01+00:00", "order_id": "same-id"}],
    }
    records = [
        {
            "strategy_id": "zec_4h_live_v1",
            "symbol": "BTCUSDT",
            "signal_key": "btc-open",
            "bar_close_time": "2026-09-01T00:00:00+00:00",
            "action": "OPEN",
            "status": "FILLED",
            "reason": "BUY_FALSE_TO_TRUE",
            "filled_qty": 1.0,
            "exchange_order_id": "same-id",
            "recorded_at": "2026-09-01T00:00:02+00:00",
        }
    ]
    fixed = repair_admin_snapshot(payload, records)
    assert fixed["history"] == []


def test_admin_html_names_strategy_history_and_three_clock_semantics():
    assert "策略成交记录（仅本策略订单）" in HTML
    assert "信号K线时间（北京时间）" in HTML
    assert "实际成交时间（北京时间）" in HTML
    assert "记录/回放时间（北京时间）" in HTML
    assert "程序处理时间，不代表买卖信号发生时间" in HTML
    assert "暂无已确认的本策略成交" in HTML
    assert "fetch('api/snapshot'" in HTML
    assert "fetch('api/control'" in HTML
    assert "fetch('/api/snapshot'" not in HTML
    assert "fetch('/api/control'" not in HTML
