#!/usr/bin/env python3
"""Verification script for Historical OHLCV Offline Backtest Lab.

Runs all checks and prints PASS/FAIL per check.
Exit 0 only if all checks pass.
"""
from __future__ import annotations

import csv
import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "historical_ohlcv"
SHADOW_FIXTURE_DIR = ROOT / "tests" / "fixtures" / "offline_shadow_research"

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print("=" * 60)
    print("Historical OHLCV Offline Backtest Lab — Verification")
    print("=" * 60)

    # ── 1. Module imports ──────────────────────────────────────────
    print("\n1. Module Imports")
    modules = [
        "core.historical_ohlcv_schema",
        "core.historical_ohlcv_chunked_reader",
        "core.walk_forward_split_engine",
        "core.offline_breakout_signal_engine",
        "core.offline_backtest_trade_simulator",
        "core.offline_backtest_metrics_engine",
        "core.offline_shadow_metric_engine",
        "core.offline_shadow_scorecard",
        "core.offline_shadow_comparison",
        "core.offline_shadow_report_renderer",
        "core.offline_shadow_bundle_builder",
        "core.offline_shadow_parameter_set",
        "core.offline_backtest_orchestrator",
    ]
    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
            check(f"import {mod_name}", True)
        except Exception as e:
            check(f"import {mod_name}", False, str(e))

    # ── 2. Fixture integrity ───────────────────────────────────────
    print("\n2. Fixture Integrity")
    for name in ["BTCUSDT_5m.csv", "ETHUSDT_5m.csv"]:
        path = FIXTURE_DIR / name
        exists = path.exists()
        if exists:
            try:
                with open(path) as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    rows = sum(1 for _ in reader)
                check(f"fixture {name}", rows >= 50, f"{rows} rows")
            except Exception as e:
                check(f"fixture {name}", False, str(e))
        else:
            check(f"fixture {name}", False, "file not found")

    for name in ["bars_BTCUSDT_5m.json", "outcomes_BTCUSDT_5m.json"]:
        path = SHADOW_FIXTURE_DIR / name
        check(f"shadow fixture {name}", path.exists())

    # ── 3. Walk-forward split ──────────────────────────────────────
    print("\n3. Walk-Forward Split")
    bars = _load_csv(FIXTURE_DIR / "BTCUSDT_5m.csv")
    try:
        from core.walk_forward_split_engine import split_rolling, split_expanding, SplitType
        splits = split_rolling(bars, train_pct=0.6, test_pct=0.2, n_splits=2)
        check("rolling split", len(splits) > 0 and len(splits) % 2 == 0,
              f"{len(splits)} splits")
    except Exception as e:
        check("rolling split", False, str(e))

    try:
        splits = split_expanding(bars, train_pct=0.5, test_pct=0.2, n_splits=2)
        train_splits = [s for s in splits if s.split_type == SplitType.TRAIN]
        all_start_zero = all(ts.start_index == 0 for ts in train_splits)
        check("expanding split", all_start_zero)
    except Exception as e:
        check("expanding split", False, str(e))

    # ── 4. Signal engine ───────────────────────────────────────────
    print("\n4. Signal Engine")
    try:
        from core.offline_breakout_signal_engine import scan_breakout_signals, BreakoutSignalParams
        signals = scan_breakout_signals(bars, BreakoutSignalParams(
            lookback=10, breakout_threshold=0.003,
            volume_multiplier=1.2, min_bars_required=15,
        ))
        check("signal scan", True, f"{len(signals)} signals")
    except Exception as e:
        check("signal scan", False, str(e))

    # ── 5. Trade simulation ────────────────────────────────────────
    print("\n5. Trade Simulation")
    try:
        from core.offline_backtest_trade_simulator import simulate_trade
        if signals:
            sig = signals[0]
            outcome = simulate_trade(
                signal={
                    "signal_id": sig.signal_id,
                    "entry_bar_index": sig.bar_index,
                    "entry_price": sig.entry_price,
                    "stop_price": sig.stop_price,
                    "tp_price": sig.tp_price,
                },
                bars=bars,
            )
            check("trade simulation", True, f"exit={outcome.exit_reason}")
        else:
            check("trade simulation", True, "no signals (skip)")
    except Exception as e:
        check("trade simulation", False, str(e))

    # ── 6. Metrics ─────────────────────────────────────────────────
    print("\n6. Metrics Computation")
    try:
        from core.offline_backtest_metrics_engine import compute_run_metrics
        metrics = compute_run_metrics([])
        check("empty metrics", metrics["trade_count"] == 0)
    except Exception as e:
        check("empty metrics", False, str(e))

    # ── 7. Scorecard ───────────────────────────────────────────────
    print("\n7. Scorecard Grading")
    try:
        from core.offline_shadow_scorecard import grade_run
        result = grade_run({
            "candidate_count": 10, "sample_quality_score": 0.5,
            "max_drawdown_r": -2.0, "expectancy_r": 0.5,
        })
        check("grade_run PASS", result["grade"] == "PASS")
    except Exception as e:
        check("grade_run PASS", False, str(e))

    # ── 8. Bundle builder ──────────────────────────────────────────
    print("\n8. Bundle Builder")
    try:
        from core.offline_shadow_bundle_builder import build_bundle
        bundle = build_bundle(
            plan_data={}, matrix_data={}, results_data=[],
            scorecard_data={}, report_markdown="", report_html="",
            report_json={},
        )
        manifest = json.loads(bundle["manifest.json"])
        check("bundle safety flags",
              manifest["release_hold"] == "HOLD"
              and manifest["no_live"] is True
              and manifest["no_submit"] is True)
    except Exception as e:
        check("bundle safety flags", False, str(e))

    # ── 9. Pipeline end-to-end ─────────────────────────────────────
    print("\n9. Pipeline End-to-End")
    try:
        from core.offline_backtest_orchestrator import run_backtest_on_bars
        result = run_backtest_on_bars(bars)
        check("pipeline e2e",
              all(k in result for k in ["signals", "trades", "metrics", "scorecard"]),
              f"signals={result['signal_count']}, trades={result['trade_count']}")
    except Exception as e:
        check("pipeline e2e", False, str(e))

    # ── 10. Unit tests ─────────────────────────────────────────────
    print("\n10. Unit Tests")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest",
             str(ROOT / "tests" / "unit" / "test_historical_backtest_acceptance.py"),
             "-v", "--tb=short", "-q"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        check("acceptance tests", proc.returncode == 0,
              f"exit={proc.returncode}")
    except Exception as e:
        check("acceptance tests", False, str(e))

    # ── Summary ────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"Results: {passed} passed, {failed} failed, {len(RESULTS)} total")
    print("=" * 60)

    if failed > 0:
        print("\nFAILED checks:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  - {name}: {detail}")
        return 1

    print("\nAll checks PASSED.")
    return 0


def _load_csv(csv_path: Path) -> list[dict]:
    bars = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append({
                "timestamp": float(row["timestamp"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            })
    return bars


if __name__ == "__main__":
    sys.exit(main())
