import pytest

from core.offline_shadow_plan_generator import generate_experiment_plan
from core.offline_shadow_run_config import OfflineShadowRunConfig


def _make_config(**overrides):
    defaults = dict(
        config_id="test_plan",
        symbols=("BTCUSDT", "ETHUSDT"),
        timeframes=("5m", "15m"),
        windows=("train", "validation", "test"),
        param_grid=("conservative", "balanced", "aggressive"),
        fixture_dir="/tmp/fixtures",
        output_dir="/tmp/output",
    )
    defaults.update(overrides)
    return OfflineShadowRunConfig(**defaults)


class TestExperimentCount:
    def test_full_grid_count(self):
        """2 symbols * 2 timeframes * 3 windows * 3 params = 36 experiments."""
        config = _make_config()
        plan = generate_experiment_plan(config)
        assert len(plan.experiments) == 36

    def test_single_combo(self):
        config = _make_config(
            symbols=("BTCUSDT",),
            timeframes=("5m",),
            windows=("train",),
            param_grid=("conservative",),
        )
        plan = generate_experiment_plan(config)
        assert len(plan.experiments) == 1


class TestDeterminism:
    def test_same_config_same_plan(self):
        config = _make_config()
        plan1 = generate_experiment_plan(config)
        plan2 = generate_experiment_plan(config)
        assert len(plan1.experiments) == len(plan2.experiments)
        for e1, e2 in zip(plan1.experiments, plan2.experiments):
            assert e1.experiment_id == e2.experiment_id
            assert e1.symbol == e2.symbol
            assert e1.timeframe == e2.timeframe
            assert e1.window == e2.window
            assert e1.parameter_set == e2.parameter_set

    def test_experiment_ids_sequential(self):
        config = _make_config(symbols=("BTCUSDT",), timeframes=("5m",),
                              windows=("train",), param_grid=("conservative", "balanced"))
        plan = generate_experiment_plan(config)
        ids = [e.experiment_id for e in plan.experiments]
        assert ids == ["exp_0000", "exp_0001"]


class TestCoverage:
    def test_all_symbols_represented(self):
        config = _make_config()
        plan = generate_experiment_plan(config)
        syms = {e.symbol.symbol for e in plan.experiments}
        assert syms == {"BTCUSDT", "ETHUSDT"}

    def test_all_timeframes_represented(self):
        config = _make_config()
        plan = generate_experiment_plan(config)
        tfs = {e.timeframe.label for e in plan.experiments}
        assert tfs == {"5m", "15m"}

    def test_all_windows_represented(self):
        config = _make_config()
        plan = generate_experiment_plan(config)
        ws = {e.window.window_type for e in plan.experiments}
        assert ws == {"train", "validation", "test"}

    def test_all_params_represented(self):
        config = _make_config()
        plan = generate_experiment_plan(config)
        ps = {e.parameter_set.label for e in plan.experiments}
        assert ps == {"conservative", "balanced", "aggressive"}


class TestSafetyPolicy:
    def test_all_experiments_hold(self):
        config = _make_config()
        plan = generate_experiment_plan(config)
        for exp in plan.experiments:
            assert exp.safety_policy.release_hold == "HOLD"
            assert exp.safety_policy.no_live is True
            assert exp.safety_policy.no_submit is True
            assert exp.safety_policy.no_exchange is True
        assert plan.safety_policy.release_hold == "HOLD"

    def test_plan_links_to_run_config(self):
        config = _make_config()
        plan = generate_experiment_plan(config)
        assert plan.run_config is config
        assert plan.plan_id == config.config_id
