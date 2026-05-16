from __future__ import annotations

from scripts.public_kline_backfill_common import (
    build_kline_request_windows,
    normalize_kline_backfill_config,
    render_backfill_plan_markdown,
    summarize_backfill_plan,
)


def test_normalize_kline_backfill_config() -> None:
    cfg = normalize_kline_backfill_config(
        max_symbols=0,
        max_bars=0,
        market="FUTURES",
        dry_run=True,
        write_cache=False,
        public_only=True,
        min_written_bars=-1,
        fail_if_empty=True,
    )
    assert cfg["max_symbols"] == 1
    assert cfg["max_bars"] == 1
    assert cfg["market"] == "futures"
    assert cfg["min_written_bars"] == 0
    assert cfg["fail_if_empty"] is True


def test_build_kline_request_windows() -> None:
    plan_rows = [
        {"symbol": "BTCUSDT", "timeframe": "5m", "required_bars": "900", "cache_status": "MISSING"},
        {"symbol": "ETHUSDT", "timeframe": "15m", "required_bars": "3000", "cache_status": "PARTIAL"},
        {"symbol": "XRPUSDT", "timeframe": "5m", "required_bars": "50", "cache_status": "OK"},
    ]
    windows = build_kline_request_windows(plan_rows=plan_rows, max_symbols=5, max_bars=1500)
    assert len(windows) == 2
    assert windows[0]["symbol"] == "BTCUSDT"
    assert windows[0]["requested_bars"] == 900
    assert windows[1]["requested_bars"] == 1500


def test_summarize_and_render_backfill_plan() -> None:
    windows = [
        {"symbol": "BTCUSDT", "timeframe": "5m", "requested_bars": 500},
        {"symbol": "ETHUSDT", "timeframe": "15m", "requested_bars": 700},
    ]
    summary = summarize_backfill_plan(plan_rows_total=4, windows=windows)
    assert summary["plan_rows_total"] == 4
    assert summary["selected_rows"] == 2
    assert summary["symbols_count"] == 2
    assert summary["requested_bars_total"] == 1200
    md = render_backfill_plan_markdown(summary)
    assert "# Public Kline Backfill Plan" in md
    assert "## Summary" in md
    assert "- selected_rows: 2" in md
