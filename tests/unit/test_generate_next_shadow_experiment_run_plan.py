from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.generate_next_shadow_experiment_run_plan import generate_next_shadow_experiment_run_plan


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


def test_plan_ordering_and_no_submit_flags(tmp_path: Path) -> None:
    tracker = tmp_path / "tracker.csv"
    priority = tmp_path / "priority.csv"
    expansion = tmp_path / "expansion.csv"
    schedule = tmp_path / "schedule.json"
    review = tmp_path / "review.json"
    out = tmp_path / "out"

    _write_csv(
        tracker,
        ["experiment_id", "strategy_key", "symbol", "side", "timeframe", "experiment_type", "collection_status", "next_run_sample_target", "next_action"],
        [
            {"experiment_id": "exp_b", "strategy_key": "sk2", "symbol": "ETHUSDT", "side": "SELL", "timeframe": "15m", "experiment_type": "BASELINE_STRICT", "collection_status": "ACTIVE", "next_run_sample_target": "4", "next_action": "collect"},
            {"experiment_id": "exp_a", "strategy_key": "sk1", "symbol": "BTCUSDT", "side": "BUY", "timeframe": "5m", "experiment_type": "OBS", "collection_status": "ACTIVE", "next_run_sample_target": "8", "next_action": "collect"},
        ],
    )
    _write_csv(priority, ["experiment_id", "priority_bucket"], [{"experiment_id": "exp_b", "priority_bucket": "P1"}, {"experiment_id": "exp_a", "priority_bucket": "P0"}])
    _write_csv(expansion, ["strategy_key", "expansion_allowed_now", "max_candidates_adjustment"], [{"strategy_key": "sk1", "expansion_allowed_now": "false", "max_candidates_adjustment": "12"}])
    _write_json(schedule, {"allowed_mode": "SHADOW_ONLY"})
    _write_json(review, {"allow_expand_observation_universe": False})

    summary = generate_next_shadow_experiment_run_plan(
        experiment_sample_tracker_csv=str(tracker),
        experiment_priority_rank_csv=str(priority),
        expansion_candidates_csv=str(expansion),
        shadow_scan_daily_schedule_json=str(schedule),
        observation_universe_expansion_review_json=str(review),
        output_dir=str(out),
    )

    assert summary["final_verdict"] == "PASS"
    assert summary["submit_permission"] == "NO_SUBMIT"
    assert summary["testnet_submit_allowed"] is False
    assert summary["real_submit_allowed"] is False

    rows = list(csv.DictReader((out / "next_shadow_experiment_run_plan.csv").open("r", encoding="utf-8")))
    assert rows[0]["experiment_id"] == "exp_a"
    assert rows[0]["collector_mode"] == "observation"
    assert rows[1]["collector_mode"] == "strict"


def test_threshold_and_paused_filter(tmp_path: Path) -> None:
    tracker = tmp_path / "tracker.csv"
    priority = tmp_path / "priority.csv"
    expansion = tmp_path / "expansion.csv"
    schedule = tmp_path / "schedule.json"
    review = tmp_path / "review.json"
    out = tmp_path / "out"

    _write_csv(
        tracker,
        ["experiment_id", "strategy_key", "symbol", "side", "timeframe", "experiment_type", "collection_status", "next_run_sample_target", "next_action"],
        [
            {"experiment_id": "exp_zero", "strategy_key": "sk0", "symbol": "XRPUSDT", "side": "BUY", "timeframe": "5m", "experiment_type": "OBS", "collection_status": "ACTIVE", "next_run_sample_target": "0", "next_action": "collect"},
            {"experiment_id": "exp_pause", "strategy_key": "skp", "symbol": "OPUSDT", "side": "SELL", "timeframe": "5m", "experiment_type": "OBS", "collection_status": "PAUSED", "next_run_sample_target": "10", "next_action": "collect"},
        ],
    )
    _write_csv(priority, ["experiment_id", "priority_bucket"], [])
    _write_csv(expansion, ["strategy_key", "expansion_allowed_now", "max_candidates_adjustment"], [])
    _write_json(schedule, {})
    _write_json(review, {})

    summary = generate_next_shadow_experiment_run_plan(
        experiment_sample_tracker_csv=str(tracker),
        experiment_priority_rank_csv=str(priority),
        expansion_candidates_csv=str(expansion),
        shadow_scan_daily_schedule_json=str(schedule),
        observation_universe_expansion_review_json=str(review),
        output_dir=str(out),
    )

    assert summary["plan_row_count"] == 0
    assert summary["final_verdict"] == "PARTIAL"
