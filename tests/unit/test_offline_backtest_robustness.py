"""Tests for core/offline_backtest_robustness.py — 15+ tests."""
from __future__ import annotations

import pytest

from core.offline_backtest_robustness import (
    RobustnessReport,
    check_fee_sensitivity,
    check_min_trade_threshold,
    check_slippage_sensitivity,
    check_split_stability,
)


def _run_with_trades(trades: list[dict], **extra) -> dict:
    r = {"trades": trades, "trade_count": len(trades)}
    r.update(extra)
    return r


def _trade(net_pnl: float = 10.0, entry_price: float = 100.0) -> dict:
    return {"net_pnl": net_pnl, "entry_price": entry_price}


class TestRobustnessReport:
    def test_frozen(self):
        rr = RobustnessReport(
            check_name="test", passes=(), fails=(), is_robust=True, detail=""
        )
        with pytest.raises(AttributeError):
            rr.is_robust = False

    def test_empty_check_name_raises(self):
        with pytest.raises(ValueError, match="check_name"):
            RobustnessReport(
                check_name="", passes=(), fails=(), is_robust=True, detail=""
            )

    def test_passes_must_be_tuple(self):
        with pytest.raises(ValueError, match="passes"):
            RobustnessReport(
                check_name="x", passes=["bad"], fails=(), is_robust=True, detail=""
            )

    def test_fails_must_be_tuple(self):
        with pytest.raises(ValueError, match="fails"):
            RobustnessReport(
                check_name="x", passes=(), fails=["bad"], is_robust=True, detail=""
            )


class TestFeeSensitivity:
    def test_robust_low_fees(self):
        run = _run_with_trades([_trade(50.0)])
        rr = check_fee_sensitivity([run], [1.0, 5.0, 10.0])
        assert rr.is_robust is True
        assert len(rr.passes) == 3

    def test_fails_high_fees(self):
        run = _run_with_trades([_trade(1.0, entry_price=1000.0)])
        rr = check_fee_sensitivity([run], [1.0, 50.0])
        assert rr.is_robust is False
        assert len(rr.fails) > 0

    def test_empty_trades(self):
        run = _run_with_trades([])
        rr = check_fee_sensitivity([run], [5.0])
        assert rr.check_name == "fee_sensitivity"

    def test_mixed_pass_fail(self):
        # net_pnl=1.0, entry=100.0; at 50bps fee=0.5 => net=0.5 pass; at 200bps fee=2.0 => net=-1.0 fail
        run = _run_with_trades([_trade(1.0, entry_price=100.0)])
        rr = check_fee_sensitivity([run], [50.0, 200.0])
        assert len(rr.passes) >= 1
        assert len(rr.fails) >= 1


class TestSlippageSensitivity:
    def test_robust_low_slippage(self):
        run = _run_with_trades([_trade(50.0)])
        rr = check_slippage_sensitivity([run], [1.0, 5.0])
        assert rr.is_robust is True

    def test_fails_high_slippage(self):
        run = _run_with_trades([_trade(0.1, entry_price=1000.0)])
        rr = check_slippage_sensitivity([run], [100.0])
        assert rr.is_robust is False

    def test_check_name(self):
        rr = check_slippage_sensitivity([], [1.0])
        assert rr.check_name == "slippage_sensitivity"


class TestMinTradeThreshold:
    def test_all_pass(self):
        run = _run_with_trades([_trade()] * 20)
        rr = check_min_trade_threshold([run], [5, 10, 15])
        assert rr.is_robust is True

    def test_fails_high_threshold(self):
        run = _run_with_trades([_trade()] * 5)
        rr = check_min_trade_threshold([run], [10])
        assert rr.is_robust is False
        assert "10" in rr.fails

    def test_boundary(self):
        run = _run_with_trades([_trade()] * 10)
        rr = check_min_trade_threshold([run], [10])
        assert rr.is_robust is True


class TestSplitStability:
    def test_all_positive(self):
        runs = [
            {"split_id": "S1", "expectancy_r": 0.5},
            {"split_id": "S2", "expectancy_r": 0.3},
        ]
        rr = check_split_stability(runs)
        assert rr.is_robust is True
        assert len(rr.passes) == 2

    def test_some_negative(self):
        runs = [
            {"split_id": "S1", "expectancy_r": 0.5},
            {"split_id": "S2", "expectancy_r": -0.1},
        ]
        rr = check_split_stability(runs)
        assert rr.is_robust is False
        assert "S1" in rr.passes
        assert "S2" in rr.fails

    def test_all_negative(self):
        runs = [
            {"split_id": "S1", "expectancy_r": -1.0},
            {"split_id": "S2", "expectancy_r": -0.5},
        ]
        rr = check_split_stability(runs)
        assert rr.is_robust is False
        assert len(rr.fails) == 2

    def test_empty_runs(self):
        rr = check_split_stability([])
        assert rr.is_robust is True
        assert len(rr.passes) == 0
