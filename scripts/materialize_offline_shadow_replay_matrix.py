#!/usr/bin/env python3
"""CLI: Materialize replay matrix from an offline shadow experiment plan."""
import argparse
import json
import sys
from dataclasses import asdict

from core.offline_shadow_matrix_materializer import materialize_replay_matrix


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize offline shadow replay matrix"
    )
    parser.add_argument("--plan-json", required=True, help="Path to plan JSON")
    parser.add_argument("--fixture-dir", required=True, help="Path to fixture directory")
    parser.add_argument("--output-json", required=True, help="Path to output JSON")
    args = parser.parse_args()

    with open(args.plan_json) as f:
        plan_dict = json.load(f)

    # Reconstruct plan from JSON — import models
    from core.offline_shadow_experiment import OfflineShadowExperiment
    from core.offline_shadow_experiment_plan import OfflineShadowExperimentPlan
    from core.offline_shadow_parameter_set import OfflineShadowParameterSet
    from core.offline_shadow_run_config import OfflineShadowRunConfig
    from core.offline_shadow_safety_policy import OfflineShadowSafetyPolicy
    from core.offline_shadow_symbol import OfflineShadowSymbol
    from core.offline_shadow_timeframe import OfflineShadowTimeframe
    from core.offline_shadow_window import OfflineShadowWindow

    sp_dict = plan_dict["safety_policy"]
    safety_policy = OfflineShadowSafetyPolicy(**sp_dict)

    rc_dict = plan_dict["run_config"]
    run_config = OfflineShadowRunConfig(
        config_id=rc_dict["config_id"],
        symbols=tuple(rc_dict["symbols"]),
        timeframes=tuple(rc_dict["timeframes"]),
        windows=tuple(rc_dict["windows"]),
        param_grid=tuple(rc_dict["param_grid"]),
        fixture_dir=rc_dict["fixture_dir"],
        output_dir=rc_dict["output_dir"],
    )

    experiments = []
    for e_dict in plan_dict["experiments"]:
        sym_d = e_dict["symbol"]
        tf_d = e_dict["timeframe"]
        win_d = e_dict["window"]
        ps_d = e_dict["parameter_set"]
        sp_d = e_dict["safety_policy"]

        exp = OfflineShadowExperiment(
            experiment_id=e_dict["experiment_id"],
            symbol=OfflineShadowSymbol(**sym_d),
            timeframe=OfflineShadowTimeframe(**tf_d),
            window=OfflineShadowWindow(**win_d),
            parameter_set=OfflineShadowParameterSet(**ps_d),
            safety_policy=OfflineShadowSafetyPolicy(**sp_d),
        )
        experiments.append(exp)

    plan = OfflineShadowExperimentPlan(
        plan_id=plan_dict["plan_id"],
        experiments=tuple(experiments),
        run_config=run_config,
        safety_policy=safety_policy,
    )

    matrix = materialize_replay_matrix(plan, args.fixture_dir)

    with open(args.output_json, "w") as f:
        json.dump(matrix, f, indent=2)

    print(f"Matrix written to {args.output_json} ({matrix['run_count']} runs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
