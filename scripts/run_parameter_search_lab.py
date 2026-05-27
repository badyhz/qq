#!/usr/bin/env python3
"""Run parameter search lab — expand bounded parameter search spaces.

Usage:
    python3 scripts/run_parameter_search_lab.py \
        --registry /tmp/multi_strategy_research_workbench/strategy_registry.json \
        --output-dir /tmp/multi_strategy_research_workbench \
        --search-budget 120

Output: parameter_search.json

Safety: local only, no network, no exchange, no live.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.parameter_search_engine import run_parameter_search
from core.strategy_research_parameters import ParameterSchema, ParameterSpec
from core.strategy_registry_adapters import STRATEGY_DEFINITIONS


def _load_registry_schemas(registry_path: Path) -> dict:
    """Load strategy schemas from registry JSON."""
    data = json.loads(registry_path.read_text())
    schemas = {}
    for strat in data.get("strategies", []):
        sid = strat["strategy_id"]
        param_schema_raw = strat.get("parameter_schema", {})
        specs = []
        for pname, pdef in sorted(param_schema_raw.items()):
            if pdef.get("type") == "enum":
                specs.append(ParameterSpec(
                    name=pname, type="enum",
                    values=tuple(pdef.get("values", [])),
                ))
            else:
                specs.append(ParameterSpec(
                    name=pname, type=pdef.get("type", "int"),
                    min=pdef.get("min"), max=pdef.get("max"),
                    default=pdef.get("default"),
                ))
        schemas[sid] = ParameterSchema(strategy_id=sid, parameters=tuple(specs))
    return schemas


def main() -> int:
    parser = argparse.ArgumentParser(description="Run parameter search lab")
    parser.add_argument("--registry", required=True, help="Path to strategy_registry.json")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--search-budget", type=int, default=120, help="Max parameter combinations")
    args = parser.parse_args()

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"ERROR: registry not found: {registry_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    schemas = _load_registry_schemas(registry_path)
    if not schemas:
        print("ERROR: no strategies in registry", file=sys.stderr)
        return 1

    result = run_parameter_search(schemas, search_budget=args.search_budget)

    out_file = output_dir / "parameter_search.json"
    out_file.write_text(result.to_json())
    print(f"Wrote {out_file} ({result.evaluated_combinations} combinations)")
    if result.budget_truncated:
        print(f"WARNING: budget truncated ({result.expanded_combinations} > {result.search_budget})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
