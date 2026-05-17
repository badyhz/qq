from __future__ import annotations

import json
from pathlib import Path

from scripts import evaluate_shadow_order_outcomes as mod


def _write_plan(path: Path) -> None:
    row = {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "entry_timestamp": "2026-05-17T00:00:00Z",
        "entry_timestamp_ms": 1715904000000,
        "entry_price": 100.0,
        "stop_loss": 90.0,
        "take_profit": 110.0,
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def test_no_network_fetch_by_default(tmp_path: Path, monkeypatch) -> None:
    plan = tmp_path / "plans.jsonl"
    out = tmp_path / "out.csv"
    _write_plan(plan)

    def _fail_fetch(**_: object) -> dict[str, object]:
        raise AssertionError("network fetch should not be called without execute_fetch")

    monkeypatch.setattr(mod, "fetch_binance_spot_klines_public_since", _fail_fetch)

    result = mod.evaluate_shadow_order_outcomes(
        shadow_order_plan_path=str(plan),
        output_csv=str(out),
        market_data_source="binance_public",
        horizon_bars=[30],
        timeframe="5m",
        debug=False,
        execute_fetch=False,
    )

    assert result["network_enabled"] is False
    assert result["execute_fetch"] is False
    assert result["summary"]["failed_orders"] >= 1


def test_execute_fetch_calls_fetch_fn(tmp_path: Path, monkeypatch) -> None:
    plan = tmp_path / "plans.jsonl"
    out = tmp_path / "out.csv"
    _write_plan(plan)

    called = {"n": 0}

    def _fake_fetch(**_: object) -> dict[str, object]:
        called["n"] += 1
        return {"success": False, "error": "offline_test", "klines": []}

    monkeypatch.setattr(mod, "fetch_binance_spot_klines_public_since", _fake_fetch)

    result = mod.evaluate_shadow_order_outcomes(
        shadow_order_plan_path=str(plan),
        output_csv=str(out),
        market_data_source="binance_public",
        horizon_bars=[30],
        timeframe="5m",
        debug=False,
        execute_fetch=True,
    )

    assert called["n"] == 1
    assert result["network_enabled"] is True
