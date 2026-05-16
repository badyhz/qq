#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
from typing import Any, Optional

from core.execution import ExecutionEngine
from core.order_manager import OrderManager
from core.signal_engine import run_walk_forward_observation
from core.signal_outcome import summarize_outcomes_by_horizon
from scripts.right_breakout_observation_common import normalize_observation_config
from scripts.run_right_breakout_scan_dry import (
    _NoopExchange,
    _build_mock_connector,
    _build_mock_market_data,
    _build_public_connector,
    _normalize_min_score,
)


def _parse_csv_ints(text: str) -> list[int]:
    rows: list[int] = []
    for item in str(text or "").split(","):
        raw = item.strip()
        if raw == "":
            continue
        try:
            rows.append(int(float(raw)))
        except ValueError:
            continue
    return rows


def _fetch_klines_by_symbol(
    *,
    symbols: list[str],
    timeframe: str,
    limit: int,
    market_data_source: str,
    connector: Any,
    lookback: int,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    warnings: list[str] = []
    if market_data_source == "mock":
        data = _build_mock_market_data(
            symbols=symbols,
            timeframe=timeframe,
            bars=max(int(limit), lookback + 8, 40),
            lookback=max(5, int(lookback)),
        )
        return {key: list(value)[-int(limit):] for key, value in data.items()}, warnings

    rows: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols:
        result = connector.fetch_public_klines(
            symbol=symbol,
            interval=timeframe,
            limit=max(1, int(limit)),
            market_type="spot",
        )
        if not isinstance(result, dict) or not bool(result.get("success", False)):
            warnings.append(f"public_kline_fetch_failed:{symbol}")
            rows[symbol] = []
            continue
        rows[symbol] = list(result.get("klines", []))
    return rows, warnings


def run_right_breakout_observation_bundle(
    *,
    symbols: list[str],
    market_data_source: str = "mock",
    timeframe: str = "5m",
    limit: int = 120,
    scan_cutoff_bars: int = 30,
    horizons: Optional[list[int]] = None,
    min_score: float = 60.0,
    volume_multiplier: float = 1.2,
    lookback: int = 20,
    walk_forward: bool = False,
    min_history_bars: int = 60,
    max_signals_per_symbol: int = 20,
    connector: Any = None,
    klines_by_symbol: Optional[dict[str, list[dict[str, Any]]]] = None,
) -> dict[str, Any]:
    normalized = normalize_observation_config(
        symbols=list(symbols or []),
        market_data_source=market_data_source,
        timeframe=timeframe,
        limit=limit,
        scan_cutoff_bars=scan_cutoff_bars,
        horizons=list(horizons or [5, 15, 30]),
        min_score=min_score,
        volume_multiplier=volume_multiplier,
        lookback=lookback,
        walk_forward=walk_forward,
        min_history_bars=min_history_bars,
        max_signals_per_symbol=max_signals_per_symbol,
    )
    resolved_symbols = list(normalized.get("symbols", []))
    resolved_source = str(normalized.get("source", "mock"))
    resolved_timeframe = str(normalized.get("timeframe", "5m"))
    resolved_limit = int(normalized.get("limit", 120))
    resolved_cutoff = int(normalized.get("scan_cutoff_bars", 30))
    resolved_horizons = list(normalized.get("horizons", [5, 15, 30]))

    logger = logging.getLogger("right-breakout-observation")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())

    resolved_connector = connector
    if resolved_connector is None:
        resolved_connector = _build_mock_connector() if resolved_source == "mock" else _build_public_connector()

    config = {
        "mode": "live",
        "symbol": resolved_symbols[0] if resolved_symbols else "BTCUSDT",
        "execution": {"enable_live_trading": False, "dry_run_fee_rate": 0.0004},
    }
    engine = ExecutionEngine(config, OrderManager(config), _NoopExchange(), logger, broker_connector=resolved_connector)
    if isinstance(klines_by_symbol, dict):
        full_klines_by_symbol = {str(k): list(v) for k, v in klines_by_symbol.items()}
        fetch_warnings: list[str] = []
    else:
        full_klines_by_symbol, fetch_warnings = _fetch_klines_by_symbol(
            symbols=resolved_symbols,
            timeframe=resolved_timeframe,
            limit=resolved_limit,
            market_data_source=resolved_source,
            connector=resolved_connector,
            lookback=lookback,
        )

    scan_klines_by_symbol: dict[str, list[dict[str, Any]]] = {}
    future_klines_by_symbol: dict[str, list[dict[str, Any]]] = {}
    warnings: list[str] = list(fetch_warnings)
    for symbol in resolved_symbols:
        rows = list(full_klines_by_symbol.get(symbol, []))
        if len(rows) <= resolved_cutoff:
            scan_klines_by_symbol[symbol] = rows[:]
            future_klines_by_symbol[symbol] = []
            warnings.append(f"insufficient_scan_cutoff_bars:{symbol}")
            continue
        scan_klines_by_symbol[symbol] = rows[:-resolved_cutoff]
        future_klines_by_symbol[symbol] = rows[-resolved_cutoff:]

    strategy_params = {
        "min_score": float(_normalize_min_score(min_score)),
        "volume_multiplier": float(volume_multiplier),
        "lookback": max(5, int(lookback)),
    }
    if bool(walk_forward):
        candidate_outcomes: list[dict[str, Any]] = []
        rejected_reason_counts: dict[str, int] = {}
        top_symbols: list[dict[str, Any]] = []
        total_windows = 0
        valid_count = 0
        rejected_count = 0
        rejected_outcomes_summary_rows: list[dict[str, Any]] = []
        for symbol in resolved_symbols:
            symbol_rows = list(full_klines_by_symbol.get(symbol, []))
            if len(symbol_rows) <= max(2, int(min_history_bars)):
                warnings.append(f"insufficient_bars_for_walk_forward:{symbol}")
                continue
            result = run_walk_forward_observation(
                symbol=symbol,
                candles=symbol_rows,
                timeframe=resolved_timeframe,
                strategy_params=strategy_params,
                horizons=resolved_horizons,
                min_history_bars=max(2, int(min_history_bars)),
                max_signals_per_symbol=max(1, int(max_signals_per_symbol)),
            )
            total_windows += int(result.get("total_evaluated_windows", 0))
            valid_count += int(result.get("valid_count", 0))
            rejected_count += int(result.get("rejected_count", 0))
            candidate_outcomes.extend(list(result.get("candidate_outcomes", [])))
            rejected_outcomes_summary_rows.append(
                {
                    "symbol": symbol,
                    "total_rejected_windows": int(
                        dict(result.get("rejected_outcomes_summary", {})).get("total_rejected_windows", 0)
                    ),
                    "rejection_reason_counts": dict(result.get("rejection_reason_counts", {})),
                }
            )
            top_symbols.append(
                {
                    "symbol": symbol,
                    "valid_count": int(result.get("valid_count", 0)),
                    "rejected_count": int(result.get("rejected_count", 0)),
                }
            )
            for reason, count in dict(result.get("rejection_reason_counts", {})).items():
                key = str(reason).strip() or "rejected"
                rejected_reason_counts[key] = rejected_reason_counts.get(key, 0) + int(count)
            warnings.extend([str(item) for item in list(result.get("warnings", [])) if str(item)])

        summary_by_horizon = summarize_outcomes_by_horizon(
            outcomes=candidate_outcomes,
            horizons=resolved_horizons,
        )
        common_rejection_reasons = [
            {"reason": key, "count": value}
            for key, value in sorted(rejected_reason_counts.items(), key=lambda row: (-row[1], row[0]))
        ]
        top_symbols_by_valid_count = sorted(top_symbols, key=lambda row: int(row.get("valid_count", 0)), reverse=True)
        next_actions = ["continue_observation"] if valid_count > 0 else ["wait_for_setup", "inspect_params"]
        return {
            "scan_id": f"walk-forward-{resolved_timeframe}",
            "observation_id": f"walk-forward-{resolved_timeframe}-{len(candidate_outcomes)}",
            "market_data_source": resolved_source,
            "walk_forward": True,
            "min_history_bars": max(2, int(min_history_bars)),
            "max_signals_per_symbol": max(1, int(max_signals_per_symbol)),
            "total_evaluated_windows": total_windows,
            "valid_count": valid_count,
            "rejected_count": rejected_count,
            "candidate_outcomes_count": len(candidate_outcomes),
            "candidate_outcomes": candidate_outcomes,
            "rejected_outcomes_summary": {
                "total_rejected_windows": rejected_count,
                "rejection_reason_counts": rejected_reason_counts,
                "by_symbol": rejected_outcomes_summary_rows,
            },
            "common_rejection_reasons": common_rejection_reasons,
            "top_symbols_by_valid_count": top_symbols_by_valid_count,
            "summary_by_horizon": summary_by_horizon,
            "summary": {
                "total_candidates": len(candidate_outcomes),
                "next_actions": next_actions,
                "safe_to_live": False,
            },
            "next_actions": next_actions,
            "warnings": list(dict.fromkeys(warnings)),
            "safe_to_live": False,
        }

    scan = engine.run_multi_symbol_signal_scan(
        symbols=resolved_symbols,
        market_data_by_symbol=scan_klines_by_symbol,
        timeframe=resolved_timeframe,
        strategy_params=strategy_params,
        max_candidates=5,
        market_data_source="mock",
        limit=resolved_limit,
        connector=resolved_connector,
    )
    scan["market_data_source"] = resolved_source
    observation = engine.build_scan_observation_report(
        scan_report=scan,
        future_klines_by_symbol=future_klines_by_symbol,
        horizons=resolved_horizons,
    )
    rejected_positive = int(observation.get("summary", {}).get("rejected_positive_return_count", 0))
    result = {
        "scan_id": str(scan.get("scan_id", "")),
        "observation_id": str(observation.get("observation_id", "")),
        "market_data_source": resolved_source,
        "valid_count": int(scan.get("valid_count", len(list(scan.get("valid_signals", [])))),
        ),
        "rejected_count": int(scan.get("rejected_count", len(list(scan.get("rejected_signals", [])))),
        ),
        "candidate_outcomes": list(observation.get("candidate_outcomes", [])),
        "rejected_outcomes_summary": {
            "total_rejected_outcomes": len(list(observation.get("rejected_outcomes", []))),
            "positive_return_count": rejected_positive,
        },
        "summary": dict(observation.get("summary", {})),
        "next_actions": list(observation.get("summary", {}).get("next_actions", [])),
        "warnings": list(dict.fromkeys(list(scan.get("warnings", [])) + list(observation.get("warnings", [])) + warnings)),
        "safe_to_live": False,
        "total_evaluated_windows": len(scan_klines_by_symbol),
        "candidate_outcomes_count": len(list(observation.get("candidate_outcomes", []))),
        "common_rejection_reasons": list(observation.get("summary", {}).get("common_rejection_reasons", [])),
        "top_symbols_by_valid_count": [],
        "summary_by_horizon": summarize_outcomes_by_horizon(
            outcomes=list(observation.get("candidate_outcomes", [])),
            horizons=resolved_horizons,
        ),
    }
    if int(result.get("valid_count", 0)) == 0 and "wait_for_setup" not in result["next_actions"]:
        result["next_actions"] = ["wait_for_setup", "inspect_params"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run right-breakout scan + forward observation (dry-only).")
    parser.add_argument("--market-data-source", choices=["mock", "binance_public"], default="mock")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT")
    parser.add_argument("--timeframe", choices=["5m", "15m", "1h"], default="5m")
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--scan-cutoff-bars", type=int, default=30)
    parser.add_argument("--horizons", default="5,15,30")
    parser.add_argument("--min-score", type=float, default=60.0)
    parser.add_argument("--volume-multiplier", type=float, default=1.2)
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--min-history-bars", type=int, default=60)
    parser.add_argument("--max-signals-per-symbol", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    symbols = [item.strip().upper() for item in str(args.symbols or "").split(",") if item.strip()]
    horizons = _parse_csv_ints(str(args.horizons or ""))
    result = run_right_breakout_observation_bundle(
        symbols=symbols,
        market_data_source=str(args.market_data_source or "mock"),
        timeframe=str(args.timeframe or "5m"),
        limit=max(1, int(args.limit)),
        scan_cutoff_bars=max(1, int(args.scan_cutoff_bars)),
        horizons=horizons or [5, 15, 30],
        min_score=float(args.min_score),
        volume_multiplier=float(args.volume_multiplier),
        lookback=max(5, int(args.lookback)),
        walk_forward=bool(args.walk_forward),
        min_history_bars=max(2, int(args.min_history_bars)),
        max_signals_per_symbol=max(1, int(args.max_signals_per_symbol)),
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"scan_id={result.get('scan_id', '')} observation_id={result.get('observation_id', '')} "
            f"valid_count={result.get('valid_count', 0)} rejected_count={result.get('rejected_count', 0)}"
        )
        print(f"next_actions={','.join(list(result.get('next_actions', [])))}")
        for warning in list(result.get("warnings", [])):
            print(f"- WARN: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
