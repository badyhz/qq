from core.offline_shadow_experiment import OfflineShadowExperiment
from core.offline_shadow_experiment_plan import OfflineShadowExperimentPlan
from core.offline_shadow_parameter_set import OfflineShadowParameterSet
from core.offline_shadow_run_config import OfflineShadowRunConfig
from core.offline_shadow_safety_policy import OfflineShadowSafetyPolicy
from core.offline_shadow_symbol import OfflineShadowSymbol
from core.offline_shadow_timeframe import OfflineShadowTimeframe
from core.offline_shadow_window import OfflineShadowWindow

# Canonical parameter grids
PARAM_GRIDS: dict[str, dict] = {
    "conservative": dict(
        label="conservative",
        entry_threshold=0.75,
        exit_threshold=0.30,
        stop_loss_r=1.5,
        take_profit_r=3.0,
        max_hold_bars=20,
        min_sample_quality=0.85,
    ),
    "balanced": dict(
        label="balanced",
        entry_threshold=0.60,
        exit_threshold=0.25,
        stop_loss_r=2.0,
        take_profit_r=2.5,
        max_hold_bars=15,
        min_sample_quality=0.70,
    ),
    "aggressive": dict(
        label="aggressive",
        entry_threshold=0.45,
        exit_threshold=0.20,
        stop_loss_r=2.5,
        take_profit_r=2.0,
        max_hold_bars=10,
        min_sample_quality=0.55,
    ),
}

# Canonical window definitions
WINDOW_DEFS: dict[str, dict] = {
    "train": dict(window_type="train", start_index=0, end_index=100),
    "validation": dict(window_type="validation", start_index=100, end_index=150),
    "test": dict(window_type="test", start_index=150, end_index=200),
}

# Canonical timeframe definitions
TIMEFRAME_DEFS: dict[str, int] = {
    "5m": 5,
    "15m": 15,
}


def generate_experiment_plan(run_config: OfflineShadowRunConfig) -> OfflineShadowExperimentPlan:
    """Generate a deterministic experiment plan from a run config.

    Pure function — no I/O, no timestamps, no randomness.
    """
    safety_policy = OfflineShadowSafetyPolicy(
        no_live=True,
        no_submit=True,
        no_exchange=True,
        release_hold="HOLD",
    )

    experiments: list[OfflineShadowExperiment] = []
    idx = 0

    for symbol_str in run_config.symbols:
        symbol = OfflineShadowSymbol(
            symbol=symbol_str,
            base_asset=symbol_str[:3],
            quote_asset=symbol_str[3:],
            exchange="binance",
        )

        for tf_label in run_config.timeframes:
            timeframe = OfflineShadowTimeframe(
                label=tf_label,
                minutes=TIMEFRAME_DEFS[tf_label],
            )

            for window_name in run_config.windows:
                wdef = WINDOW_DEFS[window_name]
                window = OfflineShadowWindow(
                    window_id=f"w_{window_name}",
                    window_type=wdef["window_type"],
                    start_index=wdef["start_index"],
                    end_index=wdef["end_index"],
                )

                for param_name in run_config.param_grid:
                    pdef = PARAM_GRIDS[param_name]
                    param_set = OfflineShadowParameterSet(
                        param_id=f"p_{param_name}",
                        **pdef,
                    )

                    experiment_id = f"exp_{idx:04d}"
                    exp = OfflineShadowExperiment(
                        experiment_id=experiment_id,
                        symbol=symbol,
                        timeframe=timeframe,
                        window=window,
                        parameter_set=param_set,
                        safety_policy=safety_policy,
                    )
                    experiments.append(exp)
                    idx += 1

    return OfflineShadowExperimentPlan(
        plan_id=run_config.config_id,
        experiments=tuple(experiments),
        run_config=run_config,
        safety_policy=safety_policy,
    )
