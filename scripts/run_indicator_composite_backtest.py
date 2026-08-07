#!/usr/bin/env python3
"""Run INDICATOR_COMPOSITE_V1 historical research from local OHLCV CSVs.

Offline only. No network, account, secret, order, Testnet or Live access.

The default Bottom Treasure source is the explicitly-versioned
``bottom_treasure_recovered_v0`` formula. It exists to make the research chain
runnable while the later final SMMA-based AiCoin formula is recovered exactly.
Results therefore identify the formula version and must not be mixed with a
future final-formula cohort.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.historical_ohlcv_chunked_reader import (
    deduplicate_bars,
    read_ohlcv_chunks,
    summarize_dataset,
)
from core.historical_ohlcv_schema import OHLCVColumnMapping
from core.indicator_composite_backtest import (
    CompositeBacktestConfig,
    run_indicator_composite_backtest,
)
from core.offline_backtest_trade_simulator import TradeSimulationParams
from core.paper_trading.aicoin_indicator_ports import (
    BOTTOM_TREASURE_RECOVERED_VERSION,
)
from core.paper_trading.data_source import MarketBar
from core.paper_trading.higher_timeframe_trend import align_higher_timeframe_trends
from core.paper_trading.indicator_composite_adapter import (
    build_recovered_v0_composite_states,
)


COLUMN_MAPPING = OHLCVColumnMapping(
    timestamp_col="timestamp",
    open_col="open",
    high_col="high",
    low_col="low",
    close_col="close",
    volume_col="volume",
)

INTERVAL_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
}

SAFETY_FLAGS = [
    "OFFLINE_BACKTEST_ONLY",
    "NO_NETWORK",
    "NO_SECRET",
    "NO_ACCOUNT",
    "NO_ORDER",
    "NO_TESTNET",
    "NO_LIVE",
]


def _interval_seconds(timeframe: str) -> int:
    try:
        return INTERVAL_SECONDS[timeframe.lower()]
    except KeyError as exc:
        raise ValueError(f"unsupported timeframe: {timeframe}") from exc


def _load_historical(path: Path, symbol: str, timeframe: str, chunk_size: int):
    bars = []
    for chunk in read_ohlcv_chunks(
        path,
        COLUMN_MAPPING,
        chunk_size=chunk_size,
        symbol=symbol,
        timeframe=timeframe,
    ):
        bars.extend(chunk)
    return sorted(deduplicate_bars(bars), key=lambda bar: bar.timestamp)


def _market_bars(historical_bars) -> list[MarketBar]:
    return [
        MarketBar(
            timestamp=float(bar.timestamp),
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=float(bar.volume),
            symbol=str(bar.symbol),
            timeframe=str(bar.timeframe),
        )
        for bar in historical_bars
    ]


def _quality(path: Path, symbol: str, timeframe: str, chunk_size: int) -> dict:
    report = summarize_dataset(
        csv_path=path,
        column_mapping=COLUMN_MAPPING,
        chunk_size=chunk_size,
        symbol=symbol,
        timeframe=timeframe,
        expected_interval_seconds=_interval_seconds(timeframe),
    )
    return {
        "symbol": report.symbol,
        "timeframe": report.timeframe,
        "total_rows": report.total_rows,
        "valid_rows": report.valid_rows,
        "duplicate_count": report.duplicate_count,
        "gap_count": report.gap_count,
        "invalid_ohlcv_count": report.invalid_ohlcv_count,
        "is_clean": report.is_clean,
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def run_from_csv(
    *,
    lower_csv: Path,
    higher_csv: Path,
    symbol: str,
    lower_timeframe: str,
    higher_timeframe: str,
    chunk_size: int = 500,
    cooldown_bars: int = 0,
    fee_pct: float = 0.001,
    slippage_pct: float = 0.0005,
    max_hold_bars: int = 100,
    require_clean: bool = True,
) -> dict:
    """Run the complete offline research chain on two local CSV datasets."""
    if not lower_csv.is_file():
        raise FileNotFoundError(f"lower CSV not found: {lower_csv}")
    if not higher_csv.is_file():
        raise FileNotFoundError(f"higher CSV not found: {higher_csv}")
    if _interval_seconds(higher_timeframe) <= _interval_seconds(lower_timeframe):
        raise ValueError("higher_timeframe must be strictly larger than lower_timeframe")

    lower_quality = _quality(lower_csv, symbol, lower_timeframe, chunk_size)
    higher_quality = _quality(higher_csv, symbol, higher_timeframe, chunk_size)
    if require_clean and (not lower_quality["is_clean"] or not higher_quality["is_clean"]):
        raise ValueError("historical data quality gate failed; use only clean datasets")

    lower_hist = _load_historical(lower_csv, symbol, lower_timeframe, chunk_size)
    higher_hist = _load_historical(higher_csv, symbol, higher_timeframe, chunk_size)
    if not lower_hist:
        raise ValueError("lower timeframe dataset contains no valid bars")
    if not higher_hist:
        raise ValueError("higher timeframe dataset contains no valid bars")

    trends = align_higher_timeframe_trends(lower_hist, higher_hist)
    lower_market = _market_bars(lower_hist)
    states = build_recovered_v0_composite_states(lower_market, trends)
    backtest = run_indicator_composite_backtest(
        lower_market,
        states,
        CompositeBacktestConfig(
            cooldown_bars=cooldown_bars,
            simulation=TradeSimulationParams(
                slippage_pct=slippage_pct,
                fee_pct=fee_pct,
                max_hold_bars=max_hold_bars,
            ),
        ),
    )

    return _json_safe({
        "strategy_id": "indicator_composite_v1",
        "research_formula_version": BOTTOM_TREASURE_RECOVERED_VERSION,
        "symbol": symbol,
        "lower_timeframe": lower_timeframe,
        "higher_timeframe": higher_timeframe,
        "lower_bar_count": len(lower_hist),
        "higher_bar_count": len(higher_hist),
        "quality": {
            "lower": lower_quality,
            "higher": higher_quality,
        },
        "backtest": backtest,
        "safety_flags": SAFETY_FLAGS,
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run INDICATOR_COMPOSITE_V1 offline historical backtest"
    )
    parser.add_argument("--lower-csv", required=True)
    parser.add_argument("--higher-csv", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--lower-timeframe", default="15m")
    parser.add_argument("--higher-timeframe", default="1h")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--cooldown-bars", type=int, default=0)
    parser.add_argument("--fee-pct", type=float, default=0.001)
    parser.add_argument("--slippage-pct", type=float, default=0.0005)
    parser.add_argument("--max-hold-bars", type=int, default=100)
    parser.add_argument("--allow-data-quality-issues", action="store_true")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)

    try:
        result = run_from_csv(
            lower_csv=Path(args.lower_csv),
            higher_csv=Path(args.higher_csv),
            symbol=args.symbol,
            lower_timeframe=args.lower_timeframe,
            higher_timeframe=args.higher_timeframe,
            chunk_size=args.chunk_size,
            cooldown_bars=args.cooldown_bars,
            fee_pct=args.fee_pct,
            slippage_pct=args.slippage_pct,
            max_hold_bars=args.max_hold_bars,
            require_clean=not args.allow_data_quality_issues,
        )
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        print(str(output))
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
