from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.evaluate_testnet_reset_readiness import evaluate_testnet_reset_readiness


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = header + "\n"
    if rows:
        text += "\n".join(rows) + "\n"
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def ready_inputs(tmp_path: Path) -> dict[str, str]:
    system_health = tmp_path / "system_health.json"
    gate_dashboard = tmp_path / "gate_dashboard.json"
    runner_report = tmp_path / "runner_report.json"
    strategy_csv = tmp_path / "strategy.csv"
    symbol_side_csv = tmp_path / "symbol_side.csv"
    promotion_csv = tmp_path / "promotion.csv"

    _write_json(system_health, {"final_verdict": "PASS", "account_state": {"orphan_status": "CLEAN"}})
    _write_json(gate_dashboard, {"by_decision": {"BLOCK_SYSTEM_HEALTH": 0}})
    _write_json(runner_report, {"approved_candidate_count": 1, "safety_verdict": "PASS"})
    _write_csv(strategy_csv, "sample_confidence_level", ["HIGH"])
    _write_csv(symbol_side_csv, "recommendation", ["ALLOW"])
    _write_csv(promotion_csv, "promotion_decision", ["PROMOTE"])

    return {
        "system_health_json": str(system_health),
        "gate_dashboard_json": str(gate_dashboard),
        "runner_dry_run_report_json": str(runner_report),
        "strategy_candidate_csv": str(strategy_csv),
        "symbol_side_csv": str(symbol_side_csv),
        "strategy_promotion_csv": str(promotion_csv),
        "output_dir": str(tmp_path / "out"),
    }


def test_ready_pass_case(ready_inputs: dict[str, str]) -> None:
    result = evaluate_testnet_reset_readiness(**ready_inputs)
    assert result["readiness_verdict"] == "READY"
    assert result["can_submit_after_reset"] is True
    assert result["blocking_reasons"] == []


@pytest.mark.parametrize(
    ("mutator", "expected_reason"),
    [
        (lambda d: _write_json(Path(d["system_health_json"]), {"final_verdict": "PASS", "account_state": {"orphan_status": "DIRTY"}}), "orphan_not_clean"),
        (lambda d: _write_json(Path(d["gate_dashboard_json"]), {"by_decision": {"BLOCK_SYSTEM_HEALTH": 2}}), "critical_gate_blocks_present"),
        (lambda d: _write_json(Path(d["runner_dry_run_report_json"]), {"approved_candidate_count": 1, "safety_verdict": "FAIL"}), "runner_dry_run_not_safe"),
        (lambda d: Path(d["strategy_candidate_csv"]).unlink(), "sample_confidence_too_small"),
    ],
)
def test_blocking_conditions(ready_inputs: dict[str, str], mutator, expected_reason: str) -> None:
    mutator(ready_inputs)
    result = evaluate_testnet_reset_readiness(**ready_inputs)
    assert result["readiness_verdict"] == "NOT_READY"
    assert result["can_submit_after_reset"] is False
    assert expected_reason in result["blocking_reasons"]


def test_blocking_reasons_order_is_deterministic(ready_inputs: dict[str, str]) -> None:
    _write_json(Path(ready_inputs["system_health_json"]), {"final_verdict": "FAIL", "account_state": {"orphan_status": "DIRTY"}})
    _write_json(Path(ready_inputs["gate_dashboard_json"]), {"by_decision": {"BLOCK_SYSTEM_HEALTH": 1}})
    _write_json(Path(ready_inputs["runner_dry_run_report_json"]), {"approved_candidate_count": 0, "safety_verdict": "FAIL"})
    Path(ready_inputs["strategy_candidate_csv"]).write_text("sample_confidence_level\nTOO_SMALL\n", encoding="utf-8")
    Path(ready_inputs["symbol_side_csv"]).write_text("recommendation\nREJECT\n", encoding="utf-8")
    Path(ready_inputs["strategy_promotion_csv"]).write_text("promotion_decision\nREJECT_STRATEGY\n", encoding="utf-8")

    result = evaluate_testnet_reset_readiness(**ready_inputs)
    assert result["blocking_reasons"] == [
        "system_health_not_pass",
        "orphan_not_clean",
        "critical_gate_blocks_present",
        "no_approved_candidate",
        "sample_confidence_too_small",
        "symbol_side_rejected",
        "strategy_promotion_rejected",
        "runner_dry_run_not_safe",
    ]
