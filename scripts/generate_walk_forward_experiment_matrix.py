#!/usr/bin/env python3
"""Walk-forward experiment matrix CLI.

Reads fixture CSVs, generates walk-forward splits per symbol/timeframe,
outputs deterministic matrix JSON. Exit 0 on success.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.walk_forward_split_engine import (
    SplitType,
    split_expanding,
    split_rolling,
)


def _load_csv_bars(csv_path: Path) -> list:
    """Load bars from a CSV file."""
    bars = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append({
                "timestamp": row.get("timestamp", ""),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            })
    return bars


def _build_fixture_path(fixture_dir: Path, symbol: str, timeframe: str) -> Path:
    """Build path to a fixture CSV."""
    return fixture_dir / f"{symbol}_{timeframe}.csv"


def generate_matrix(
    fixture_dir: Path,
    symbols: list,
    timeframes: list,
    split_mode: str,
    train_pct: float = 0.6,
    test_pct: float = 0.2,
    n_splits: int = 3,
) -> dict:
    """Generate walk-forward matrix for all symbol/timeframe combos."""
    split_fn = split_rolling if split_mode == "rolling" else split_expanding

    entries = []
    for symbol in sorted(symbols):
        for timeframe in sorted(timeframes):
            csv_path = _build_fixture_path(fixture_dir, symbol, timeframe)
            if not csv_path.exists():
                continue
            bars = _load_csv_bars(csv_path)
            splits = split_fn(bars, train_pct=train_pct, test_pct=test_pct, n_splits=n_splits)
            split_dicts = []
            for s in splits:
                split_dicts.append({
                    "split_id": s.split_id,
                    "split_type": s.split_type.value,
                    "start_index": s.start_index,
                    "end_index": s.end_index,
                    "bar_count": s.bar_count,
                })
            entries.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "split_mode": split_mode,
                "bar_count": len(bars),
                "splits": split_dicts,
            })

    matrix = {
        "fixture_dir": str(fixture_dir),
        "symbols": sorted(symbols),
        "timeframes": sorted(timeframes),
        "split_mode": split_mode,
        "train_pct": train_pct,
        "test_pct": test_pct,
        "n_splits": n_splits,
        "entries": entries,
    }
    return matrix


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate walk-forward experiment matrix")
    parser.add_argument("--fixture-dir", required=True, help="Path to fixture directory")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--timeframes", required=True, help="Comma-separated timeframes")
    parser.add_argument("--split-mode", choices=["rolling", "expanding"], default="rolling")
    parser.add_argument("--train-pct", type=float, default=0.6)
    parser.add_argument("--test-pct", type=float, default=0.2)
    parser.add_argument("--n-splits", type=int, default=3)
    parser.add_argument("--output-json", required=True, help="Output JSON path")
    args = parser.parse_args()

    fixture_dir = Path(args.fixture_dir)
    if not fixture_dir.is_dir():
        print(f"ERROR: fixture dir not found: {fixture_dir}", file=sys.stderr)
        return 1

    symbols = [s.strip() for s in args.symbols.split(",")]
    timeframes = [t.strip() for t in args.timeframes.split(",")]

    matrix = generate_matrix(
        fixture_dir=fixture_dir,
        symbols=symbols,
        timeframes=timeframes,
        split_mode=args.split_mode,
        train_pct=args.train_pct,
        test_pct=args.test_pct,
        n_splits=args.n_splits,
    )

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2, sort_keys=False)

    return 0


if __name__ == "__main__":
    sys.exit(main())
