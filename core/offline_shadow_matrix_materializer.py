from dataclasses import asdict

from core.offline_shadow_experiment_plan import OfflineShadowExperimentPlan


def materialize_replay_matrix(
    plan: OfflineShadowExperimentPlan, fixture_dir: str
) -> dict:
    """Materialize a replay matrix from an experiment plan and fixture directory.

    Pure function — deterministic, no I/O, no timestamps.

    Returns dict with:
      - plan_id
      - fixture_dir
      - safety_policy (dict)
      - runs: list of run entry dicts
    """
    safety_flags = {
        "no_live": plan.safety_policy.no_live,
        "no_submit": plan.safety_policy.no_submit,
        "no_exchange": plan.safety_policy.no_exchange,
        "release_hold": plan.safety_policy.release_hold,
    }

    runs: list[dict] = []
    for exp in plan.experiments:
        sym = exp.symbol.symbol
        tf = exp.timeframe.label

        run_entry = {
            "run_id": f"run_{exp.experiment_id}",
            "experiment_id": exp.experiment_id,
            "symbol": sym,
            "base_asset": exp.symbol.base_asset,
            "quote_asset": exp.symbol.quote_asset,
            "exchange": exp.symbol.exchange,
            "timeframe": tf,
            "timeframe_minutes": exp.timeframe.minutes,
            "window_id": exp.window.window_id,
            "window_type": exp.window.window_type,
            "window_start_index": exp.window.start_index,
            "window_end_index": exp.window.end_index,
            "param_id": exp.parameter_set.param_id,
            "param_label": exp.parameter_set.label,
            "entry_threshold": exp.parameter_set.entry_threshold,
            "exit_threshold": exp.parameter_set.exit_threshold,
            "stop_loss_r": exp.parameter_set.stop_loss_r,
            "take_profit_r": exp.parameter_set.take_profit_r,
            "max_hold_bars": exp.parameter_set.max_hold_bars,
            "min_sample_quality": exp.parameter_set.min_sample_quality,
            "fixture_bars": f"bars_{sym}_{tf}.json",
            "fixture_signals": f"signals_{sym}_{tf}.json",
            "fixture_outcomes": f"outcomes_{sym}_{tf}.json",
            "safety": safety_flags,
        }
        runs.append(run_entry)

    return {
        "plan_id": plan.plan_id,
        "fixture_dir": fixture_dir,
        "safety_policy": safety_flags,
        "run_count": len(runs),
        "runs": runs,
    }
