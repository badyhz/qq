from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from core.paper_trading.aicoin_indicator_ports import (
    BOTTOM_TREASURE_RECOVERED_VERSION,
)
from scripts.run_indicator_composite_backtest import main, run_from_csv


def _write_csv(path: Path, *, count: int, interval: int, base: float = 100.0) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for index in range(count):
            close = base + index * 0.05
            writer.writerow([
                index * interval,
                close - 0.2,
                close + 0.8,
                close - 0.8,
                close,
                1000.0 + index,
            ])


def test_run_from_csv_executes_complete_offline_chain(tmp_path: Path):
    lower = tmp_path / "BTCUSDT_15m.csv"
    higher = tmp_path / "BTCUSDT_1h.csv"
    _write_csv(lower, count=160, interval=900)
    _write_csv(higher, count=50, interval=3600)

    result = run_from_csv(
        lower_csv=lower,
        higher_csv=higher,
        symbol="BTCUSDT",
        lower_timeframe="15m",
        higher_timeframe="1h",
        fee_pct=0.001,
        slippage_pct=0.0005,
    )

    assert result["strategy_id"] == "indicator_composite_v1"
    assert result["research_formula_version"] == BOTTOM_TREASURE_RECOVERED_VERSION
    assert result["lower_bar_count"] == 160
    assert result["higher_bar_count"] == 50
    assert result["quality"]["lower"]["is_clean"] is True
    assert result["quality"]["higher"]["is_clean"] is True
    assert result["backtest"]["execution_mode"] == "offline_backtest_only"
    assert result["backtest"]["orders_enabled"] is False
    assert result["backtest"]["dynamic_exit_overlay_applied"] is False
    assert "metrics" in result["backtest"]
    assert result["entry_ablation"]["variant_order"] == [
        "A_BOTTOM_ONLY",
        "B_BOTTOM_ACCELERATOR",
        "C_BOTTOM_ACCELERATOR_HTF",
    ]
    assert result["entry_ablation"]["same_bars"] is True
    assert result["entry_ablation"]["same_friction_config"] is True
    assert result["entry_ablation"]["orders_enabled"] is False
    full_variant = result["entry_ablation"]["variants"][2]["result"]
    assert result["backtest"] == full_variant


def test_runner_rejects_non_higher_timeframe(tmp_path: Path):
    lower = tmp_path / "lower.csv"
    higher = tmp_path / "higher.csv"
    _write_csv(lower, count=40, interval=3600)
    _write_csv(higher, count=40, interval=900)

    with pytest.raises(ValueError, match="strictly larger"):
        run_from_csv(
            lower_csv=lower,
            higher_csv=higher,
            symbol="BTCUSDT",
            lower_timeframe="1h",
            higher_timeframe="15m",
        )


def test_main_writes_json_output(tmp_path: Path):
    lower = tmp_path / "lower.csv"
    higher = tmp_path / "higher.csv"
    output = tmp_path / "result.json"
    _write_csv(lower, count=160, interval=900)
    _write_csv(higher, count=50, interval=3600)

    rc = main([
        "--lower-csv", str(lower),
        "--higher-csv", str(higher),
        "--symbol", "BTCUSDT",
        "--lower-timeframe", "15m",
        "--higher-timeframe", "1h",
        "--output", str(output),
    ])

    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["strategy_id"] == "indicator_composite_v1"
    assert payload["entry_ablation"]["experiment_id"] == (
        "indicator_composite_entry_ablation_v1"
    )
    assert payload["safety_flags"] == [
        "OFFLINE_BACKTEST_ONLY",
        "NO_NETWORK",
        "NO_SECRET",
        "NO_ACCOUNT",
        "NO_ORDER",
        "NO_TESTNET",
        "NO_LIVE",
    ]


def test_main_returns_one_for_missing_csv(tmp_path: Path):
    rc = main([
        "--lower-csv", str(tmp_path / "missing_lower.csv"),
        "--higher-csv", str(tmp_path / "missing_higher.csv"),
        "--symbol", "BTCUSDT",
    ])
    assert rc == 1
