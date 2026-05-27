#!/usr/bin/env python3
"""CLI: Generate a deterministic offline shadow experiment plan."""
import argparse
import json
import sys
from dataclasses import asdict

from core.offline_shadow_plan_generator import generate_experiment_plan
from core.offline_shadow_run_config import OfflineShadowRunConfig


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate offline shadow experiment plan"
    )
    parser.add_argument("--output-json", required=True, help="Path to output JSON")
    parser.add_argument(
        "--symbols", default="BTCUSDT,ETHUSDT", help="Comma-separated symbols"
    )
    parser.add_argument(
        "--timeframes", default="5m,15m", help="Comma-separated timeframes"
    )
    parser.add_argument(
        "--windows",
        default="train,validation,test",
        help="Comma-separated window names",
    )
    parser.add_argument(
        "--param-grid",
        default="conservative,balanced,aggressive",
        help="Comma-separated param grid names",
    )
    args = parser.parse_args()

    symbols = tuple(args.symbols.split(","))
    timeframes = tuple(args.timeframes.split(","))
    windows = tuple(args.windows.split(","))
    param_grid = tuple(args.param_grid.split(","))

    run_config = OfflineShadowRunConfig(
        config_id="cli_plan",
        symbols=symbols,
        timeframes=timeframes,
        windows=windows,
        param_grid=param_grid,
        fixture_dir="",
        output_dir="",
    )

    plan = generate_experiment_plan(run_config)
    # Serialize: experiments as list of dicts, safety_policy inline
    plan_dict = {
        "plan_id": plan.plan_id,
        "experiments": [
            {
                "experiment_id": e.experiment_id,
                "symbol": asdict(e.symbol),
                "timeframe": asdict(e.timeframe),
                "window": asdict(e.window),
                "parameter_set": asdict(e.parameter_set),
                "safety_policy": asdict(e.safety_policy),
            }
            for e in plan.experiments
        ],
        "run_config": asdict(plan.run_config),
        "safety_policy": asdict(plan.safety_policy),
    }

    with open(args.output_json, "w") as f:
        json.dump(plan_dict, f, indent=2)

    print(f"Plan written to {args.output_json} ({len(plan.experiments)} experiments)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
