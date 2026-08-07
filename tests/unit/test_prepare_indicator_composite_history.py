from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts.prepare_indicator_composite_history import (
    DEFAULT_SYMBOLS,
    SAFETY_FLAGS,
    prepare_history_batch,
    prepare_symbol_history,
)


def _fake_download(**kwargs) -> dict:
    output = Path(kwargs["output_path"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "timestamp,open,high,low,close,volume\n"
        "1785456000,100,101,99,100,1000\n",
        encoding="utf-8",
    )
    return {
        "symbol": kwargs["symbol"],
        "interval": kwargs["interval"],
        "row_count": 1,
        "output_path": str(output),
        "checksum_verified": True,
        "private_api_used": False,
        "orders_enabled": False,
    }


def _fake_backtest(**kwargs) -> dict:
    return {
        "strategy_id": "indicator_composite_v1",
        "symbol": kwargs["symbol"],
        "backtest": {
            "trade_count": 3,
            "metrics": {"profit_factor": 1.2, "expectancy_r": 0.1},
            "orders_enabled": False,
        },
    }


def test_default_batch_matches_current_eight_symbol_universe():
    assert DEFAULT_SYMBOLS == (
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
        "SUIUSDT",
        "1000PEPEUSDT",
        "XRPUSDT",
        "ARBUSDT",
        "DOGEUSDT",
    )


def test_prepare_one_symbol_downloads_both_timeframes_and_runs_backtest(tmp_path: Path):
    result = prepare_symbol_history(
        symbol="btcusdt",
        lower_timeframe="15m",
        higher_timeframe="1h",
        start=date(2026, 7, 1),
        end=date(2026, 7, 31),
        output_dir=tmp_path,
        run_backtest=True,
        download_func=_fake_download,
        backtest_func=_fake_backtest,
    )

    assert result["symbol"] == "BTCUSDT"
    assert result["lower_history"]["interval"] == "15m"
    assert result["higher_history"]["interval"] == "1h"
    assert result["lower_history"]["checksum_verified"] is True
    assert result["backtest"]["backtest"]["orders_enabled"] is False
    assert result["safety_flags"] == SAFETY_FLAGS
    assert (tmp_path / "BTCUSDT" / "BTCUSDT_15m.csv").is_file()
    assert (tmp_path / "BTCUSDT" / "BTCUSDT_1h.csv").is_file()


def test_batch_is_serial_and_keeps_symbol_results_isolated(tmp_path: Path):
    calls: list[tuple[str, str]] = []

    def download(**kwargs):
        calls.append((kwargs["symbol"], kwargs["interval"]))
        return _fake_download(**kwargs)

    result = prepare_history_batch(
        symbols=("BTCUSDT", "ETHUSDT"),
        lower_timeframe="15m",
        higher_timeframe="1h",
        start=date(2026, 7, 1),
        end=date(2026, 7, 31),
        output_dir=tmp_path,
        run_backtest=False,
        download_func=download,
        backtest_func=_fake_backtest,
    )

    assert result["symbol_count"] == 2
    assert result["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert calls == [
        ("BTCUSDT", "15m"),
        ("BTCUSDT", "1h"),
        ("ETHUSDT", "15m"),
        ("ETHUSDT", "1h"),
    ]
    assert all(entry["backtest"] is None for entry in result["results"])


def test_invalid_symbol_fails_before_download(tmp_path: Path):
    with pytest.raises(ValueError, match="invalid symbol"):
        prepare_symbol_history(
            symbol="BTC/USDT",
            lower_timeframe="15m",
            higher_timeframe="1h",
            start=date(2026, 7, 1),
            end=date(2026, 7, 31),
            output_dir=tmp_path,
            download_func=_fake_download,
        )


def test_reverse_date_range_fails_before_download(tmp_path: Path):
    with pytest.raises(ValueError, match="end must be >= start"):
        prepare_symbol_history(
            symbol="BTCUSDT",
            lower_timeframe="15m",
            higher_timeframe="1h",
            start=date(2026, 8, 1),
            end=date(2026, 7, 31),
            output_dir=tmp_path,
            download_func=_fake_download,
        )
