"""Scenario loader. Loads fixture scenarios for multi-scenario testing."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioConfig:
    scenario_name: str
    description: str
    fixture_files: dict[str, str]  # filename -> content
    expected_status: str
    expected_warnings: int

    def to_dict(self) -> dict:
        return {
            "scenario_name": self.scenario_name,
            "description": self.description,
            "expected_status": self.expected_status,
            "expected_warnings": self.expected_warnings,
        }


def load_scenario(scenario_dir: pathlib.Path) -> ScenarioConfig:
    """Load a scenario from a fixture directory."""
    name = scenario_dir.name
    desc_file = scenario_dir / "description.json"
    if desc_file.exists():
        desc = json.loads(desc_file.read_text(encoding="utf-8"))
    else:
        desc = {"description": f"Scenario: {name}", "expected_status": "PASS", "expected_warnings": 0}

    fixture_files = {}
    for p in sorted(scenario_dir.glob("*.jsonl")):
        fixture_files[p.name] = p.read_text(encoding="utf-8")
    for p in sorted(scenario_dir.glob("*.json")):
        if p.name != "description.json":
            fixture_files[p.name] = p.read_text(encoding="utf-8")

    return ScenarioConfig(
        scenario_name=name,
        description=desc.get("description", ""),
        fixture_files=fixture_files,
        expected_status=desc.get("expected_status", "PASS"),
        expected_warnings=desc.get("expected_warnings", 0),
    )


def load_all_scenarios(scenarios_dir: pathlib.Path) -> list[ScenarioConfig]:
    """Load all scenarios from the scenarios directory."""
    scenarios = []
    if not scenarios_dir.exists():
        return scenarios
    for d in sorted(scenarios_dir.iterdir()):
        if d.is_dir():
            scenarios.append(load_scenario(d))
    return scenarios
