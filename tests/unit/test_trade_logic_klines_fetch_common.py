from __future__ import annotations

import pytest

from scripts.trade_logic_klines_fetch_common import (
    BINANCE_KLINES_URL,
    build_kline_request_params,
    normalize_interval,
    normalize_kline_rows,
    normalize_symbol,
)


def test_binance_kline_url_and_params() -> None:
    assert BINANCE_KLINES_URL == "https://fapi.binance.com/fapi/v1/klines"
    params = build_kline_request_params(
        symbol="btcusdt",
        interval="5m",
        start_ms=1000,
        end_ms=2000,
        limit=500,
    )
    assert params == {
        "symbol": "BTCUSDT",
        "interval": "5m",
        "startTime": 1000,
        "endTime": 2000,
        "limit": 500,
    }


def test_symbol_and_interval_normalization() -> None:
    assert normalize_symbol(" ethusdt ") == "ETHUSDT"
    assert normalize_interval(" 15M ", ["1m", "5m", "15m", "1h"]) == "15m"
    with pytest.raises(ValueError):
        normalize_interval("2m", ["1m", "5m", "15m", "1h"])


def test_normalize_response_rows_fixture() -> None:
    payload = [
        [
            "1710000000000",
            "100.0",
            "101.0",
            "99.0",
            "100.5",
            "123.4",
            "1710000299999",
            "0",
            "0",
            "0",
            "0",
            "0",
        ],
        ["bad_ts", "1", "1", "1", "1", "1"],
        {"not": "a list"},
    ]
    rows = normalize_kline_rows(payload)
    assert len(rows) == 1
    assert rows[0][0] == 1710000000000
    assert rows[0][4] == "100.5"
