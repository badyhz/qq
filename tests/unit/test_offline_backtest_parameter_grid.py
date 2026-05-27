"""Tests for offline backtest parameter grid. 20+ tests."""

import pytest

from core.offline_backtest_parameter_grid import (
    PARAM_PRESETS,
    BacktestParameterSet,
    build_param_grid,
    validate_param_set,
)


class TestBacktestParameterSet:
    def test_frozen_cannot_mutate(self):
        p = BacktestParameterSet(
            param_id="p1", label="test", lookback_bars=20,
            breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=2.0,
            max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
            min_body_pct=0.4, cooldown_bars=5,
        )
        with pytest.raises(AttributeError):
            p.param_id = "p2"  # type: ignore

    def test_valid_construction(self):
        p = BacktestParameterSet(
            param_id="p1", label="test", lookback_bars=20,
            breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=2.0,
            max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
            min_body_pct=0.4, cooldown_bars=5,
        )
        assert p.param_id == "p1"
        assert p.lookback_bars == 20

    def test_rejects_lookback_zero(self):
        with pytest.raises(ValueError, match="lookback_bars"):
            BacktestParameterSet(
                param_id="p1", label="bad", lookback_bars=0,
                breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=2.0,
                max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
                min_body_pct=0.4, cooldown_bars=5,
            )

    def test_rejects_negative_breakout_buffer(self):
        with pytest.raises(ValueError, match="breakout_buffer_pct"):
            BacktestParameterSet(
                param_id="p1", label="bad", lookback_bars=20,
                breakout_buffer_pct=-0.001, stop_loss_r=1.0, take_profit_r=2.0,
                max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
                min_body_pct=0.4, cooldown_bars=5,
            )

    def test_rejects_zero_stop_loss(self):
        with pytest.raises(ValueError, match="stop_loss_r"):
            BacktestParameterSet(
                param_id="p1", label="bad", lookback_bars=20,
                breakout_buffer_pct=0.003, stop_loss_r=0.0, take_profit_r=2.0,
                max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
                min_body_pct=0.4, cooldown_bars=5,
            )

    def test_rejects_zero_take_profit(self):
        with pytest.raises(ValueError, match="take_profit_r"):
            BacktestParameterSet(
                param_id="p1", label="bad", lookback_bars=20,
                breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=0.0,
                max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
                min_body_pct=0.4, cooldown_bars=5,
            )

    def test_rejects_max_hold_zero(self):
        with pytest.raises(ValueError, match="max_hold_bars"):
            BacktestParameterSet(
                param_id="p1", label="bad", lookback_bars=20,
                breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=2.0,
                max_hold_bars=0, fee_bps=10.0, slippage_bps=5.0,
                min_body_pct=0.4, cooldown_bars=5,
            )

    def test_rejects_negative_fee(self):
        with pytest.raises(ValueError, match="fee_bps"):
            BacktestParameterSet(
                param_id="p1", label="bad", lookback_bars=20,
                breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=2.0,
                max_hold_bars=80, fee_bps=-1.0, slippage_bps=5.0,
                min_body_pct=0.4, cooldown_bars=5,
            )

    def test_rejects_negative_slippage(self):
        with pytest.raises(ValueError, match="slippage_bps"):
            BacktestParameterSet(
                param_id="p1", label="bad", lookback_bars=20,
                breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=2.0,
                max_hold_bars=80, fee_bps=10.0, slippage_bps=-5.0,
                min_body_pct=0.4, cooldown_bars=5,
            )

    def test_rejects_body_pct_over_one(self):
        with pytest.raises(ValueError, match="min_body_pct"):
            BacktestParameterSet(
                param_id="p1", label="bad", lookback_bars=20,
                breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=2.0,
                max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
                min_body_pct=1.5, cooldown_bars=5,
            )

    def test_rejects_negative_cooldown(self):
        with pytest.raises(ValueError, match="cooldown_bars"):
            BacktestParameterSet(
                param_id="p1", label="bad", lookback_bars=20,
                breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=2.0,
                max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
                min_body_pct=0.4, cooldown_bars=-1,
            )

    def test_zero_breakout_buffer_valid(self):
        p = BacktestParameterSet(
            param_id="p1", label="zero_buf", lookback_bars=20,
            breakout_buffer_pct=0.0, stop_loss_r=1.0, take_profit_r=2.0,
            max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
            min_body_pct=0.4, cooldown_bars=5,
        )
        assert p.breakout_buffer_pct == 0.0

    def test_zero_cooldown_valid(self):
        p = BacktestParameterSet(
            param_id="p1", label="zero_cd", lookback_bars=20,
            breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=2.0,
            max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
            min_body_pct=0.4, cooldown_bars=0,
        )
        assert p.cooldown_bars == 0


class TestValidateParamSet:
    def test_valid_returns_empty(self):
        p = BacktestParameterSet(
            param_id="p1", label="ok", lookback_bars=20,
            breakout_buffer_pct=0.003, stop_loss_r=1.0, take_profit_r=2.0,
            max_hold_bars=80, fee_bps=10.0, slippage_bps=5.0,
            min_body_pct=0.4, cooldown_bars=5,
        )
        assert validate_param_set(p) == []

    def test_catches_multiple_errors(self):
        # Use a mock-like object to test validate_param_set directly
        class Bad:
            lookback_bars = 0
            breakout_buffer_pct = -1
            stop_loss_r = 0
            take_profit_r = 0
            max_hold_bars = 0
            fee_bps = -1
            slippage_bps = -1
            min_body_pct = 2.0
            cooldown_bars = -1

        errors = validate_param_set(Bad())
        assert len(errors) >= 5


class TestParamPresets:
    def test_all_presets_exist(self):
        expected = {"conservative", "balanced", "aggressive", "wide_stop", "tight_stop"}
        assert set(PARAM_PRESETS.keys()) == expected

    def test_preset_values_numeric(self):
        for name, preset in PARAM_PRESETS.items():
            for key in ["lookback_bars", "breakout_buffer_pct", "stop_loss_r",
                        "take_profit_r", "max_hold_bars", "fee_bps",
                        "slippage_bps", "min_body_pct", "cooldown_bars"]:
                assert key in preset, f"{name} missing {key}"
                assert isinstance(preset[key], (int, float)), f"{name}.{key} not numeric"

    def test_preset_stop_loss_positive(self):
        for name, preset in PARAM_PRESETS.items():
            assert preset["stop_loss_r"] > 0, f"{name} stop_loss_r <= 0"

    def test_preset_take_profit_positive(self):
        for name, preset in PARAM_PRESETS.items():
            assert preset["take_profit_r"] > 0, f"{name} take_profit_r <= 0"


class TestBuildParamGrid:
    def test_single_preset(self):
        grid = build_param_grid(("balanced",))
        assert len(grid) == 1
        assert grid[0].label == "balanced"

    def test_all_presets(self):
        grid = build_param_grid(list(PARAM_PRESETS.keys()))
        assert len(grid) == 5

    def test_preserves_order(self):
        grid = build_param_grid(("aggressive", "conservative"))
        assert grid[0].label == "aggressive"
        assert grid[1].label == "conservative"

    def test_param_id_format(self):
        grid = build_param_grid(("balanced",))
        assert grid[0].param_id == "preset_balanced"

    def test_unknown_preset_raises(self):
        with pytest.raises(KeyError, match="Unknown preset"):
            build_param_grid(("nonexistent",))

    def test_returns_tuple(self):
        grid = build_param_grid(("balanced",))
        assert isinstance(grid, tuple)
