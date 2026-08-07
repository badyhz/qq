#!/usr/bin/env python3
"""Prepare verified Binance public history for INDICATOR_COMPOSITE_V1.

This command downloads only public USD-M futures monthly kline archives from
Binance Data Vision, verifies every ZIP against its sibling SHA-256 CHECKSUM,
normalizes the data into gitignored ``data/`` CSVs, and can optionally run the
existing offline composite backtest.

No account endpoints, API keys, private requests, Testnet, Live or orders.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import sys
from typing import Callable

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.binance_public_ohlcv_archive import (
    ArchiveDownloadError,
    download_range_to_csv,
)
from scripts.run_indicator_composite_backtest import run_from_csv


DEFAULT_SYMBOLS = (
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SUIUSDT",
    "1000PEPEUSDT",
    "XRPUSDT",
    "ARBUSDT",
    "DOGEUSDT",
)

SAFETY_FLAGS = [
    "PUBLIC_MARKET_DATA_ONLY",
    "CHECKSUM_VERIFIED_ARCHIVES",
    "NO_API_KEY",
    "NO_ACCOUNT",
    "NO_PRIVATE_ENDPOINT",
    "NO_ORDER",
    "NO_TESTNET",
    "NO_LIVE",
]

DownloadFunc = Callable[..., dict]
BacktestFunc = Callable[..., dict]


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def _safe_symbol(value: str) -> str:
    symbol = value.strip().upper()
    if not symbol or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in symbol):
        raise ValueError(f"invalid symbol: {value!r}")
    return symbol


def _history_paths(
    output_dir: Path,
    symbol: str,
    lower_timeframe: str,
    higher_timeframe: str,
) -> tuple[Path, Path]:
    symbol_dir = output_dir / symbol
    return (
        symbol_dir / f"{symbol}_{lower_timeframe}.csv",
        symbol_dir / f"{symbol}_{higher_timeframe}.csv",
    )


def prepare_symbol_history(
    *,
    symbol: str,
    lower_timeframe: str,
    higher_timeframe: str,
    start: date,
    end: date,
    output_dir: Path,
    run_backtest: bool = False,
    cooldown_bars: int = 0,
    fee_pct: float = 0.001,
    slippage_pct: float = 0.0005,
    max_hold_bars: int = 100,
    download_func: DownloadFunc = download_range_to_csv,
    backtest_func: BacktestFunc = run_from_csv,
) -> dict:
    """Prepare one symbol's LTF+HTF dataset and optionally run research."""
    symbol = _safe_symbol(symbol)
    if end < start:
        raise ValueError("end must be >= start")
    lower_path, higher_path = _history_paths(
        output_dir, symbol, lower_timeframe, higher_timeframe
    )

    lower = download_func(
        symbol=symbol,
        interval=lower_timeframe,
        start=start,
        end=end,
        output_path=lower_path,
    )
    higher = download_func(
        symbol=symbol,
        interval=higher_timeframe,
        start=start,
        end=end,
        output_path=higher_path,
    )

    result = {
        "symbol": symbol,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "lower_timeframe": lower_timeframe,
        "higher_timeframe": higher_timeframe,
        "lower_history": lower,
        "higher_history": higher,
        "backtest": None,
        "safety_flags": list(SAFETY_FLAGS),
    }

    if run_backtest:
        result["backtest"] = backtest_func(
            lower_csv=lower_path,
            higher_csv=higher_path,
            symbol=symbol,
            lower_timeframe=lower_timeframe,
            higher_timeframe=higher_timeframe,
            cooldown_bars=cooldown_bars,
            fee_pct=fee_pct,
            slippage_pct=slippage_pct,
            max_hold_bars=max_hold_bars,
            require_clean=True,
        )
    return result


def prepare_history_batch(
    *,
    symbols: tuple[str, ...],
    lower_timeframe: str,
    higher_timeframe: str,
    start: date,
    end: date,
    output_dir: Path,
    run_backtest: bool = False,
    cooldown_bars: int = 0,
    fee_pct: float = 0.001,
    slippage_pct: float = 0.0005,
    max_hold_bars: int = 100,
    download_func: DownloadFunc = download_range_to_csv,
    backtest_func: BacktestFunc = run_from_csv,
) -> dict:
    """Serially prepare a research batch to keep public-CDN load modest."""
    if not symbols:
        raise ValueError("at least one symbol is required")

    results = []
    for symbol in symbols:
        results.append(prepare_symbol_history(
            symbol=symbol,
            lower_timeframe=lower_timeframe,
            higher_timeframe=higher_timeframe,
            start=start,
            end=end,
            output_dir=output_dir,
            run_backtest=run_backtest,
            cooldown_bars=cooldown_bars,
            fee_pct=fee_pct,
            slippage_pct=slippage_pct,
            max_hold_bars=max_hold_bars,
            download_func=download_func,
            backtest_func=backtest_func,
        ))

    return {
        "strategy_id": "indicator_composite_v1",
        "symbols": [entry["symbol"] for entry in results],
        "symbol_count": len(results),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "lower_timeframe": lower_timeframe,
        "higher_timeframe": higher_timeframe,
        "run_backtest": run_backtest,
        "results": results,
        "safety_flags": list(SAFETY_FLAGS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download verified Binance public history for composite research"
    )
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_SYMBOLS),
        help="Comma-separated USD-M symbols",
    )
    parser.add_argument("--lower-timeframe", default="15m")
    parser.add_argument("--higher-timeframe", default="1h")
    parser.add_argument("--start", type=_parse_date, required=True)
    parser.add_argument("--end", type=_parse_date, required=True)
    parser.add_argument(
        "--output-dir",
        default=str(_REPO_ROOT / "data" / "indicator_composite_history"),
    )
    parser.add_argument("--run-backtest", action="store_true")
    parser.add_argument("--cooldown-bars", type=int, default=0)
    parser.add_argument("--fee-pct", type=float, default=0.001)
    parser.add_argument("--slippage-pct", type=float, default=0.0005)
    parser.add_argument("--max-hold-bars", type=int, default=100)
    parser.add_argument("--manifest", default="")
    args = parser.parse_args(argv)

    symbols = tuple(_safe_symbol(value) for value in args.symbols.split(",") if value.strip())
    try:
        result = prepare_history_batch(
            symbols=symbols,
            lower_timeframe=args.lower_timeframe,
            higher_timeframe=args.higher_timeframe,
            start=args.start,
            end=args.end,
            output_dir=Path(args.output_dir),
            run_backtest=args.run_backtest,
            cooldown_bars=args.cooldown_bars,
            fee_pct=args.fee_pct,
            slippage_pct=args.slippage_pct,
            max_hold_bars=args.max_hold_bars,
        )
    except (ArchiveDownloadError, FileNotFoundError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    manifest = (
        Path(args.manifest)
        if args.manifest
        else Path(args.output_dir) / "history_manifest.json"
    )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(payload, encoding="utf-8")
    print(str(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
