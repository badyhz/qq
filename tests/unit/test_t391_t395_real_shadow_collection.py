"""Targeted acceptance test for T391-T395 real shadow collection."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import scripts.discover_real_shadow_data_sources as t391
import scripts.build_real_shadow_observation_records as t392
import scripts.validate_real_shadow_observation_records as t393
import scripts.update_real_shadow_remediation_history as t394
import scripts.generate_real_shadow_collection_control_report as t395


def test_t391_t395_real_shadow_collection(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    data_dir = tmp_path / "data"
    logs_dir = tmp_path / "logs"

    # Create test observation sample store
    obs_store_dir = reports_dir / "observation_sample_store"
    obs_store_dir.mkdir(parents=True, exist_ok=True)

    obs_csv = obs_store_dir / "observation_samples.csv"
    obs_csv.write_text(
        "observation_sample_id,shadow_candidate_id,symbol,side,timeframe,strategy_key,collector_mode,candidate_source,near_miss,near_miss_reason,signal_strength_score,trend_score,breakout_score,risk_reward_score,primary_horizon_outcome,primary_horizon_realized_r,best_horizon_bars,best_horizon_realized_r,best_horizon_outcome,horizon_consistency_score,near_miss_quality_score,near_miss_verdict,near_miss_promotion_hint,sample_status,sample_weight,sample_origin,experiment_id,experiment_type,experiment_candidate_id,experiment_status,experiment_outcome,experiment_primary_horizon,experiment_realized_r_multiple,experiment_best_horizon_bars,experiment_best_horizon_realized_r,experiment_evaluation_status,created_at,source_reports\n"
        "obs_shadow_SOLUSDT_LONG_5m_1776988799999_94de1e74,shadow_SOLUSDT_LONG_5m_1776988799999_94de1e74,SOLUSDT,LONG,5m,SOLUSDT_LONG_5m,observation,shadow_universe_collection,True,breakout_not_confirmed,79.31214476,100.0,37.93643429,100.0,INSUFFICIENT_DATA,nan,30,nan,INSUFFICIENT_DATA,nan,51.7248579,NO_OUTCOME,WATCH_MORE,OBSERVATION_INSUFFICIENT_DATA,0.1,NEAR_MISS,,,,,,nan,nan,nan,nan,,2026-05-07T16:31:12.134221+00:00,shadow_candidate_outcomes;shadow_candidate_outcomes_by_horizon;shadow_near_miss;shadow_universe_collection\n"
        "obs_exp_expcand_93ef2ebe7d,,SOLUSDT,LONG,5m,SOLUSDT_LONG_5m,observation,shadow_observation_experiment_runs,True,,79.31214476,100.0,37.93643429,100.0,INSUFFICIENT_DATA,nan,30,nan,INSUFFICIENT_DATA,nan,nan,NO_OUTCOME,WATCH_MORE,OBSERVATION_INSUFFICIENT_DATA,0.1,SHADOW_EXPERIMENT,exp_SOLUSDT_LONG_5m_relax_near_miss,RELAX_NEAR_MISS,expcand_93ef2ebe7d,OBSERVATION,INSUFFICIENT_DATA,60,nan,30,nan,PARTIAL,2026-05-07T16:31:12.134221+00:00,shadow_observation_experiment_runs;shadow_experiment_outcomes;shadow_experiment_outcomes_by_horizon\n",
        encoding="utf-8",
    )

    obs_summary = obs_store_dir / "summary.json"
    obs_summary.write_text(
        json.dumps({
            "generated_at_utc": "2026-05-07T16:31:12.134221+00:00",
            "final_verdict": "PASS",
            "observation_count": 2,
            "near_miss_count": 2,
            "experiment_sample_count": 1,
            "evaluated_count": 0,
            "pending_outcome_count": 2,
            "csv_path": "reports/observation_sample_store/observation_samples.csv",
            "summary_json": "reports/observation_sample_store/summary.json",
            "summary_md": "reports/observation_sample_store/summary.md"
        }),
        encoding="utf-8",
    )

    # T391: Discover real shadow data sources
    t391_result = t391.discover_real_shadow_data_sources(
        reports_dir=str(reports_dir),
        data_dir=str(data_dir),
        logs_dir=str(logs_dir),
    )

    assert t391_result["task_id"] == "T391"
    assert t391_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t391_result["allowed_mode"] == "SHADOW_ONLY"
    assert t391_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t391_result["submit_permission"] == "NO_SUBMIT"
    assert t391_result["testnet_submit_allowed"] is False
    assert t391_result["real_submit_allowed"] is False
    assert t391_result["submit_attempted"] is False
    assert t391_result["cancel_attempted"] is False
    assert t391_result["flatten_attempted"] is False
    assert t391_result["eligible_source_count"] >= 0

    # Check QUEUE_PLACEHOLDER not in eligible sources
    for source in t391_result["eligible_sources"]:
        assert source["source_type"] != "QUEUE_PLACEHOLDER"
        assert source["source_type"] != "SYNTHETIC_PLACEHOLDER"

    # T392: Build real shadow observation records
    t392_result = t392.build_real_shadow_observation_records(
        discovery_result=t391_result,
        reports_dir=str(reports_dir),
        output_dir=str(reports_dir / "real_shadow_observation_build"),
    )

    assert t392_result["task_id"] == "T392"
    assert t392_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t392_result["allowed_mode"] == "SHADOW_ONLY"
    assert t392_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t392_result["testnet_submit_allowed"] is False
    assert t392_result["real_submit_allowed"] is False
    assert t392_result["submit_attempted"] is False
    assert t392_result["cancel_attempted"] is False
    assert t392_result["flatten_attempted"] is False

    for record in t392_result["records"]:
        assert record["observation_only"] is True
        assert "order_id" not in record
        assert "client_order_id" not in record
        assert "submit_payload" not in record
        assert "cancel_payload" not in record
        assert "flatten_payload" not in record

    # T393: Validate real shadow observation records
    t393_result = t393.validate_real_shadow_observation_records(
        build_result=t392_result,
        reports_dir=str(reports_dir),
        output_dir=str(reports_dir / "real_shadow_observation_validation"),
    )

    assert t393_result["task_id"] == "T393"
    assert t393_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t393_result["allowed_mode"] == "SHADOW_ONLY"
    assert t393_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t393_result["testnet_submit_allowed"] is False
    assert t393_result["real_submit_allowed"] is False
    assert t393_result["submit_attempted"] is False
    assert t393_result["cancel_attempted"] is False
    assert t393_result["flatten_attempted"] is False

    # T394: Update real shadow remediation history
    t394_result = t394.update_real_shadow_remediation_history(
        validation_result=t393_result,
        reports_dir=str(reports_dir),
        output_dir=str(reports_dir / "real_shadow_remediation_history_update"),
        history_dir=str(data_dir / "real_shadow_remediation_history"),
    )

    assert t394_result["task_id"] == "T394"
    assert t394_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t394_result["allowed_mode"] == "SHADOW_ONLY"
    assert t394_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t394_result["testnet_submit_allowed"] is False
    assert t394_result["real_submit_allowed"] is False
    assert t394_result["submit_attempted"] is False
    assert t394_result["cancel_attempted"] is False
    assert t394_result["flatten_attempted"] is False
    assert t394_result["idempotency_ok"] is True

    # Test T394 idempotency
    t394_result_2 = t394.update_real_shadow_remediation_history(
        validation_result=t393_result,
        reports_dir=str(reports_dir),
        output_dir=str(reports_dir / "real_shadow_remediation_history_update_2"),
        history_dir=str(data_dir / "real_shadow_remediation_history"),
    )
    assert t394_result_2["idempotency_ok"] is True
    assert t394_result_2["history_runs_after"] == t394_result["history_runs_after"]

    # T395: Generate real shadow collection control report
    t395_result = t395.generate_real_shadow_collection_control_report(
        discovery_result=t391_result,
        build_result=t392_result,
        validation_result=t393_result,
        history_result=t394_result,
        reports_dir=str(reports_dir),
        output_dir=str(reports_dir / "real_shadow_collection_control_report"),
    )

    assert t395_result["task_id"] == "T395"
    assert t395_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t395_result["allowed_mode"] == "SHADOW_ONLY"
    assert t395_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t395_result["testnet_submit_allowed"] is False
    assert t395_result["real_submit_allowed"] is False
    assert t395_result["submit_attempted"] is False
    assert t395_result["cancel_attempted"] is False
    assert t395_result["flatten_attempted"] is False
    assert t395_result["readiness_status"] in ("NOT_READY", "READY", "FAIL", "UNKNOWN")
    assert t395_result["final_decision"] in ("CONTINUE_SHADOW_COLLECTION", "CONTINUE_SHADOW_ONLY", "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW", "FAIL_SAFE_BLOCK")
    assert t395_result["archive_range"] == "T208-T395"
    assert t395_result["next_recommended_task_range"] == "T396-T400"

    # Check allowed actions
    assert "SHADOW_ONLY" in t395_result["allowed_actions"]
    assert "SHADOW_COLLECTION" in t395_result["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in t395_result["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in t395_result["allowed_actions"]

    # Check that placeholder records would be rejected
    placeholder_record = {
        "record_id": "TEST_PLACEHOLDER",
        "source_id": "test_source",
        "source_type": "QUEUE_PLACEHOLDER",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "setup": "observation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "observation_only": True,
        "synthetic_placeholder": True,
        "status": "COLLECTED",
        "reason": "test placeholder"
    }
    fake_build_result = {
        "records": [placeholder_record]
    }
    t393_result_placeholder = t393.validate_real_shadow_observation_records(
        build_result=fake_build_result,
        reports_dir=str(reports_dir),
        output_dir=str(reports_dir / "real_shadow_observation_validation_placeholder"),
    )
    assert t393_result_placeholder["placeholder_records"] > 0
    assert t393_result_placeholder["valid_for_gap_closure"] is False

    # Check that authentic records (non-placeholder) would be accepted
    authentic_record = {
        "record_id": "TEST_AUTHENTIC",
        "source_id": "observation_sample_store",
        "source_type": "MARKET_OBSERVATION",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "setup": "observation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "observation_only": True,
        "synthetic_placeholder": False,
        "status": "COLLECTED",
        "reason": "authentic test record"
    }
    fake_build_result_2 = {
        "records": [authentic_record]
    }
    t393_result_authentic = t393.validate_real_shadow_observation_records(
        build_result=fake_build_result_2,
        reports_dir=str(reports_dir),
        output_dir=str(reports_dir / "real_shadow_observation_validation_authentic"),
    )
    assert t393_result_authentic["placeholder_records"] == 0
    assert t393_result_authentic["authentic_source_records"] > 0


def test_scripts_support_json_flag() -> None:
    p1 = t391.build_arg_parser()
    p2 = t392.build_arg_parser()
    p3 = t393.build_arg_parser()
    p4 = t394.build_arg_parser()
    p5 = t395.build_arg_parser()

    a1 = [a.dest for a in p1._actions]
    a2 = [a.dest for a in p2._actions]
    a3 = [a.dest for a in p3._actions]
    a4 = [a.dest for a in p4._actions]
    a5 = [a.dest for a in p5._actions]

    assert "json" in a1
    assert "json" in a2
    assert "json" in a3
    assert "json" in a4
    assert "json" in a5
