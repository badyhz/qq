from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_research_to_testnet_dry_run_migration_checklist import (
    generate_research_to_testnet_dry_run_migration_checklist,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = header + "\n"
    if rows:
        text += "\n".join(rows) + "\n"
    path.write_text(text, encoding="utf-8")


def _base_inputs(tmp_path: Path) -> dict[str, str]:
    phase = tmp_path / "phase.json"
    gaps = tmp_path / "gaps.csv"
    remediation = tmp_path / "remediation.csv"
    kpi = tmp_path / "kpi.json"
    health = tmp_path / "health.json"

    _write_json(
        phase,
        {
            "allow_testnet_dry_run_only": True,
            "minimum_requirements": {
                "system_health_pass": True,
                "shadow_research_history_days_min_met": True,
                "experiment_samples_min_met": True,
                "stability_not_all_needs_more_data": True,
                "strategy_candidate_weighted_samples_min_met": True,
                "no_trade_actions_attempted": True,
                "testnet_dry_run_readiness_not_fail": True,
            },
        },
    )
    _write_csv(gaps, "requirement_key,blocking", [])
    _write_csv(remediation, "action,priority", ["noop,P3"])
    _write_json(kpi, {"readiness_verdict": "PASS"})
    _write_json(health, {"final_verdict": "PASS"})

    return {
        "phase_review_json": str(phase),
        "readiness_gaps_csv": str(gaps),
        "remediation_plan_csv": str(remediation),
        "shadow_research_kpi_json": str(kpi),
        "system_health_json": str(health),
        "output_dir": str(tmp_path / "out"),
    }


def test_checklist_pass_when_all_sections_satisfied(tmp_path: Path) -> None:
    result = generate_research_to_testnet_dry_run_migration_checklist(**_base_inputs(tmp_path))
    assert result["final_verdict"] == "READY"
    assert result["migration_allowed_now"] is True
    assert result["blocking_items"] == []


def test_block_when_readiness_requirement_below_threshold(tmp_path: Path) -> None:
    inputs = _base_inputs(tmp_path)
    phase = Path(inputs["phase_review_json"])
    payload = json.loads(phase.read_text(encoding="utf-8"))
    payload["minimum_requirements"]["experiment_samples_min_met"] = False
    phase.write_text(json.dumps(payload), encoding="utf-8")

    result = generate_research_to_testnet_dry_run_migration_checklist(**inputs)
    assert result["final_verdict"] == "NOT_READY"
    assert "experiment_samples_min_met" in result["blocking_items"]


def test_block_when_testnet_submit_flag_false(tmp_path: Path) -> None:
    inputs = _base_inputs(tmp_path)
    phase = Path(inputs["phase_review_json"])
    payload = json.loads(phase.read_text(encoding="utf-8"))
    payload["allow_testnet_dry_run_only"] = False
    phase.write_text(json.dumps(payload), encoding="utf-8")

    result = generate_research_to_testnet_dry_run_migration_checklist(**inputs)
    assert result["migration_allowed_now"] is False
    assert result["next_allowed_mode"] == "SHADOW_ONLY"


def test_markdown_and_json_keys_are_deterministic(tmp_path: Path) -> None:
    inputs = _base_inputs(tmp_path)
    result = generate_research_to_testnet_dry_run_migration_checklist(**inputs)
    out_dir = Path(inputs["output_dir"])
    md = (out_dir / "migration_checklist.md").read_text(encoding="utf-8")
    assert "# Research To Testnet Dry-Run Migration Checklist" in md
    assert "- submit_allowed: false" in md
    for key in [
        "final_verdict",
        "migration_target",
        "migration_allowed_now",
        "checklist",
        "blocking_items",
        "next_allowed_mode",
        "testnet_submit_allowed",
    ]:
        assert key in result
