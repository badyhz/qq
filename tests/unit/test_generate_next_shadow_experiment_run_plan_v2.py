from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.generate_next_shadow_experiment_run_plan_v2 import generate_next_shadow_experiment_run_plan_v2


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_v2_preserves_no_submit_and_applies_tuning(tmp_path: Path) -> None:
    base_plan = tmp_path / "plan.csv"
    tuning = tmp_path / "tuning.csv"
    tracker = tmp_path / "tracker.csv"
    frequency = tmp_path / "frequency.json"
    research = tmp_path / "research.json"
    out = tmp_path / "out"

    _write_csv(
        base_plan,
        ["run_rank", "experiment_id", "strategy_key", "symbol", "side", "timeframe", "experiment_type", "collector_mode", "target_samples_this_run", "max_candidates_this_run", "priority_bucket", "allowed_mode", "submit_permission", "run_command", "reason"],
        [
            {"run_rank": "1", "experiment_id": "exp1", "strategy_key": "sk1", "symbol": "BTCUSDT", "side": "BUY", "timeframe": "5m", "experiment_type": "OBS", "collector_mode": "observation", "target_samples_this_run": "6", "max_candidates_this_run": "30", "priority_bucket": "P1", "allowed_mode": "SHADOW_ONLY", "submit_permission": "NO_SUBMIT", "run_command": "cmd", "reason": "r"}
        ],
    )
    _write_csv(
        tuning,
        ["experiment_id", "tuning_action", "suggested_target_samples", "current_near_miss_threshold"],
        [{"experiment_id": "exp1", "tuning_action": "INCREASE_TARGET_SAMPLES", "suggested_target_samples": "9", "current_near_miss_threshold": "0.8"}],
    )
    _write_csv(tracker, ["experiment_id", "samples_needed_for_decision"], [{"experiment_id": "exp1", "samples_needed_for_decision": "1"}])
    _write_json(frequency, {"allow_increase_shadow_frequency": False})
    _write_json(research, {"final_verdict": "PARTIAL"})

    summary = generate_next_shadow_experiment_run_plan_v2(
        next_run_plan_csv=str(base_plan),
        tuning_suggestions_csv=str(tuning),
        experiment_sample_tracker_csv=str(tracker),
        frequency_review_json=str(frequency),
        daily_research_control_json=str(research),
        output_dir=str(out),
    )

    assert summary["final_verdict"] == "PASS"
    assert summary["plan_version"] == "v2"
    assert summary["submit_permission"] == "NO_SUBMIT"
    assert summary["testnet_submit_allowed"] is False
    assert summary["real_submit_allowed"] is False
    assert summary["tuning_applied_count"] == 1

    rows = list(csv.DictReader((out / "next_shadow_experiment_run_plan_v2.csv").open("r", encoding="utf-8")))
    assert rows[0]["target_samples_this_run"] == "9"
    assert "frequency_cap_applied" in rows[0]["reason"]
    assert "research_control_partial" in rows[0]["reason"]


def test_v2_lower_threshold_floor(tmp_path: Path) -> None:
    base_plan = tmp_path / "plan.csv"
    tuning = tmp_path / "tuning.csv"
    tracker = tmp_path / "tracker.csv"
    frequency = tmp_path / "frequency.json"
    research = tmp_path / "research.json"
    out = tmp_path / "out"

    _write_csv(
        base_plan,
        ["run_rank", "experiment_id", "strategy_key", "symbol", "side", "timeframe", "experiment_type", "collector_mode", "target_samples_this_run", "max_candidates_this_run", "priority_bucket", "allowed_mode", "submit_permission", "run_command", "reason", "near_miss_threshold"],
        [{"run_rank": "1", "experiment_id": "exp2", "strategy_key": "sk2", "symbol": "ETHUSDT", "side": "SELL", "timeframe": "15m", "experiment_type": "OBS", "collector_mode": "observation", "target_samples_this_run": "5", "max_candidates_this_run": "12", "priority_bucket": "P2", "allowed_mode": "SHADOW_ONLY", "submit_permission": "NO_SUBMIT", "run_command": "cmd", "reason": "r", "near_miss_threshold": "0.72"}],
    )
    _write_csv(
        tuning,
        ["experiment_id", "tuning_action", "current_near_miss_threshold"],
        [{"experiment_id": "exp2", "tuning_action": "LOWER_NEAR_MISS_THRESHOLD_SLIGHTLY", "current_near_miss_threshold": "0.72"}],
    )
    _write_csv(tracker, ["experiment_id", "samples_needed_for_decision"], [{"experiment_id": "exp2", "samples_needed_for_decision": "0"}])
    _write_json(frequency, {"allow_increase_shadow_frequency": True})
    _write_json(research, {"final_verdict": "PASS"})

    generate_next_shadow_experiment_run_plan_v2(
        next_run_plan_csv=str(base_plan),
        tuning_suggestions_csv=str(tuning),
        experiment_sample_tracker_csv=str(tracker),
        frequency_review_json=str(frequency),
        daily_research_control_json=str(research),
        output_dir=str(out),
    )

    rows = list(csv.DictReader((out / "next_shadow_experiment_run_plan_v2.csv").open("r", encoding="utf-8")))
    assert float(rows[0]["near_miss_threshold"]) >= 0.70
