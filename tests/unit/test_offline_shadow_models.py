import pytest

from core.offline_shadow_experiment import OfflineShadowExperiment
from core.offline_shadow_experiment_plan import OfflineShadowExperimentPlan
from core.offline_shadow_parameter_set import OfflineShadowParameterSet
from core.offline_shadow_run_config import OfflineShadowRunConfig
from core.offline_shadow_safety_policy import OfflineShadowSafetyPolicy
from core.offline_shadow_symbol import OfflineShadowSymbol
from core.offline_shadow_timeframe import OfflineShadowTimeframe
from core.offline_shadow_window import OfflineShadowWindow


# --- helpers ---

def _make_policy(**overrides):
    defaults = dict(no_live=True, no_submit=True, no_exchange=True, release_hold="HOLD")
    defaults.update(overrides)
    return OfflineShadowSafetyPolicy(**defaults)


def _make_symbol(**overrides):
    defaults = dict(symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", exchange="binance")
    defaults.update(overrides)
    return OfflineShadowSymbol(**defaults)


def _make_timeframe(**overrides):
    defaults = dict(label="5m", minutes=5)
    defaults.update(overrides)
    return OfflineShadowTimeframe(**defaults)


def _make_window(**overrides):
    defaults = dict(window_id="w_train", window_type="train", start_index=0, end_index=100)
    defaults.update(overrides)
    return OfflineShadowWindow(**defaults)


def _make_param_set(**overrides):
    defaults = dict(
        param_id="p_conservative",
        label="conservative",
        entry_threshold=0.7,
        exit_threshold=0.3,
        stop_loss_r=1.5,
        take_profit_r=3.0,
        max_hold_bars=20,
        min_sample_quality=0.8,
    )
    defaults.update(overrides)
    return OfflineShadowParameterSet(**defaults)


def _make_experiment(**overrides):
    defaults = dict(
        experiment_id="exp_001",
        symbol=_make_symbol(),
        timeframe=_make_timeframe(),
        window=_make_window(),
        parameter_set=_make_param_set(),
        safety_policy=_make_policy(),
    )
    defaults.update(overrides)
    return OfflineShadowExperiment(**defaults)


# --- safety policy ---

class TestSafetyPolicy:
    def test_valid_hold(self):
        p = _make_policy()
        assert p.release_hold == "HOLD"
        assert p.no_live is True

    def test_rejects_non_hold(self):
        with pytest.raises(ValueError, match="release_hold must be 'HOLD'"):
            _make_policy(release_hold="RELEASE")

    def test_immutability(self):
        p = _make_policy()
        with pytest.raises(AttributeError):
            p.no_live = False  # type: ignore[misc]

    def test_all_safety_flags_true(self):
        p = _make_policy()
        assert p.no_live is True
        assert p.no_submit is True
        assert p.no_exchange is True


# --- symbol ---

class TestSymbol:
    def test_creation(self):
        s = _make_symbol()
        assert s.symbol == "BTCUSDT"
        assert s.exchange == "binance"

    def test_immutability(self):
        s = _make_symbol()
        with pytest.raises(AttributeError):
            s.symbol = "ETHUSDT"  # type: ignore[misc]


# --- timeframe ---

class TestTimeframe:
    def test_creation(self):
        tf = _make_timeframe()
        assert tf.label == "5m"
        assert tf.minutes == 5

    def test_immutability(self):
        tf = _make_timeframe()
        with pytest.raises(AttributeError):
            tf.minutes = 15  # type: ignore[misc]


# --- window ---

class TestWindow:
    def test_creation(self):
        w = _make_window()
        assert w.window_type == "train"
        assert w.start_index == 0

    def test_immutability(self):
        w = _make_window()
        with pytest.raises(AttributeError):
            w.window_type = "test"  # type: ignore[misc]


# --- parameter set ---

class TestParameterSet:
    def test_creation(self):
        ps = _make_param_set()
        assert ps.param_id == "p_conservative"
        assert ps.entry_threshold == 0.7

    def test_immutability(self):
        ps = _make_param_set()
        with pytest.raises(AttributeError):
            ps.entry_threshold = 0.9  # type: ignore[misc]


# --- experiment ---

class TestExperiment:
    def test_creation(self):
        e = _make_experiment()
        assert e.experiment_id == "exp_001"
        assert e.safety_policy.release_hold == "HOLD"

    def test_immutability(self):
        e = _make_experiment()
        with pytest.raises(AttributeError):
            e.experiment_id = "other"  # type: ignore[misc]


# --- run config ---

class TestRunConfig:
    def test_creation(self):
        rc = OfflineShadowRunConfig(
            config_id="rc_001",
            symbols=("BTCUSDT",),
            timeframes=("5m",),
            windows=("train",),
            param_grid=("conservative",),
            fixture_dir="/tmp/fixtures",
            output_dir="/tmp/output",
        )
        assert rc.config_id == "rc_001"
        assert len(rc.symbols) == 1

    def test_immutability(self):
        rc = OfflineShadowRunConfig(
            config_id="rc_001",
            symbols=("BTCUSDT",),
            timeframes=("5m",),
            windows=("train",),
            param_grid=("conservative",),
            fixture_dir="/tmp/fixtures",
            output_dir="/tmp/output",
        )
        with pytest.raises(AttributeError):
            rc.config_id = "other"  # type: ignore[misc]


# --- experiment plan ---

class TestExperimentPlan:
    def test_creation(self):
        e1 = _make_experiment(experiment_id="exp_001")
        e2 = _make_experiment(experiment_id="exp_002")
        rc = OfflineShadowRunConfig(
            config_id="rc_001",
            symbols=("BTCUSDT",),
            timeframes=("5m",),
            windows=("train",),
            param_grid=("conservative",),
            fixture_dir="/tmp/fixtures",
            output_dir="/tmp/output",
        )
        policy = _make_policy()
        plan = OfflineShadowExperimentPlan(
            plan_id="plan_001",
            experiments=(e1, e2),
            run_config=rc,
            safety_policy=policy,
        )
        assert plan.plan_id == "plan_001"
        assert len(plan.experiments) == 2

    def test_immutability(self):
        e1 = _make_experiment(experiment_id="exp_001")
        rc = OfflineShadowRunConfig(
            config_id="rc_001",
            symbols=("BTCUSDT",),
            timeframes=("5m",),
            windows=("train",),
            param_grid=("conservative",),
            fixture_dir="/tmp/fixtures",
            output_dir="/tmp/output",
        )
        plan = OfflineShadowExperimentPlan(
            plan_id="plan_001",
            experiments=(e1,),
            run_config=rc,
            safety_policy=_make_policy(),
        )
        with pytest.raises(AttributeError):
            plan.plan_id = "other"  # type: ignore[misc]
