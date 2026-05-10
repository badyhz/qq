"""Targeted acceptance test for T406-T410 price field trust."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import scripts.audit_observation_price_field_candidates as t401
import scripts.audit_price_field_source_trust as t406
import scripts.generate_price_field_trust_policy_v1 as t407
import scripts.build_trusted_price_observation_records as t408
import scripts.validate_trusted_price_observation_records as t409
import scripts.generate_price_field_trust_control_report as t410


def test_t406_t410_price_field_trust(tmp_path: Path) -> None:
    csv_dir = tmp_path / "observation_sample_store"
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / "observation_samples.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["symbol", "timeframe", "strategy_key", "created_at", "close", "last", "entry_price", "mark_price"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "strategy_key": "test_setup",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "close": "60200.0",
                "last": "60201.5",
                "entry_price": "",
                "mark_price": "60199.0",
            }
        )
        writer.writerow(
            {
                "symbol": "ETHUSDT",
                "timeframe": "4h",
                "strategy_key": "test_setup_2",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "close": "3020.0",
                "last": "3020.5",
                "entry_price": "3010.0",
                "mark_price": "3019.5",
            }
        )

    # T401
    t401_result = t401.audit_observation_price_field_candidates(
        source_path=str(csv_path),
        output_dir=str(tmp_path / "t401_output"),
    )
    assert t401_result["task_id"] == "T401"
    assert t401_result["allowed_mode"] == "SHADOW_ONLY"
    assert t401_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t401_result["submit_permission"] == "NO_SUBMIT"
    assert t401_result["testnet_submit_allowed"] is False
    assert t401_result["real_submit_allowed"] is False
    assert t401_result["submit_attempted"] is False
    assert t401_result["cancel_attempted"] is False
    assert t401_result["flatten_attempted"] is False

    # T406
    t406_result = t406.audit_price_field_source_trust(
        source_path=str(csv_path),
        audit_result_t401=t401_result,
        output_dir=str(tmp_path / "t406_output"),
    )
    assert t406_result["task_id"] == "T406"
    assert t406_result["allowed_mode"] == "SHADOW_ONLY"
    assert t406_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t406_result["submit_permission"] == "NO_SUBMIT"
    assert t406_result["testnet_submit_allowed"] is False
    assert t406_result["real_submit_allowed"] is False
    assert t406_result["submit_attempted"] is False
    assert t406_result["cancel_attempted"] is False
    assert t406_result["flatten_attempted"] is False
    assert "close" in t406_result["candidate_price_fields"]
    assert "last" in t406_result["candidate_price_fields"]
    assert "entry_price" in t406_result["candidate_price_fields"]
    assert "mark_price" in t406_result["candidate_price_fields"]
    assert t406_result["gap_closure_field_count"] == 0
    assert t406_result["trust_audit_ready"] is True

    # Check entry_price trust level
    for assessment in t406_result["field_trust_assessments"]:
        if assessment["field"] == "entry_price":
            assert assessment["trust_level"] != "HIGH"
            assert assessment["can_use_for_gap_closure"] is False

    # T407
    t407_result = t407.generate_price_field_trust_policy_v1(
        audit_result_t406=t406_result,
        output_dir=str(tmp_path / "t407_output"),
    )
    assert t407_result["task_id"] == "T407"
    assert t407_result["allowed_mode"] == "SHADOW_ONLY"
    assert t407_result["testnet_submit_allowed"] is False
    assert t407_result["real_submit_allowed"] is False
    assert t407_result["submit_attempted"] is False
    assert t407_result["cancel_attempted"] is False
    assert t407_result["flatten_attempted"] is False
    assert t407_result["explicit_policy_allows_price_only"] is False
    assert t407_result["requires_full_ohlcv_for_gap_closure"] is True
    assert t407_result["fallback_values_allowed"] is False
    assert t407_result["gap_closure_allowed_fields"] == []
    assert t407_result["policy_ready"] is True

    # T408
    t408_result = t408.build_trusted_price_observation_records(
        audit_result_t401=t401_result,
        audit_result_t406=t406_result,
        policy_result_t407=t407_result,
        source_path=str(csv_path),
        output_dir=str(tmp_path / "t408_output"),
    )
    assert t408_result["task_id"] == "T408"
    assert t408_result["allowed_mode"] == "SHADOW_ONLY"
    assert t408_result["testnet_submit_allowed"] is False
    assert t408_result["real_submit_allowed"] is False
    assert t408_result["submit_attempted"] is False
    assert t408_result["cancel_attempted"] is False
    assert t408_result["flatten_attempted"] is False
    assert t408_result["gap_closure_records_built"] == 0
    assert t408_result["fallback_values_used"] is False
    assert t408_result["policy_ready"] is True
    for record in t408_result["records"]:
        assert record["auxiliary_only"] is True
        assert record["valid_for_gap_closure"] is False
        assert record["observation_only"] is True
        assert record["synthetic_placeholder"] is False

    # T409
    t409_result = t409.validate_trusted_price_observation_records(
        build_result_t408=t408_result,
        policy_result_t407=t407_result,
        output_dir=str(tmp_path / "t409_output"),
    )
    assert t409_result["task_id"] == "T409"
    assert t409_result["allowed_mode"] == "SHADOW_ONLY"
    assert t409_result["testnet_submit_allowed"] is False
    assert t409_result["real_submit_allowed"] is False
    assert t409_result["submit_attempted"] is False
    assert t409_result["cancel_attempted"] is False
    assert t409_result["flatten_attempted"] is False
    assert t409_result["explicit_policy_allows_price_only"] is False
    assert t409_result["requires_full_ohlcv_for_gap_closure"] is True
    assert t409_result["valid_for_gap_closure"] is False
    assert t409_result["gap_closure_records"] == 0
    assert t409_result["fallback_values_detected"] is False

    # T410
    t410_result = t410.generate_price_field_trust_control_report(
        audit_result_t406=t406_result,
        policy_result_t407=t407_result,
        build_result_t408=t408_result,
        validation_result_t409=t409_result,
        output_dir=str(tmp_path / "t410_output"),
    )
    assert t410_result["task_id"] == "T410"
    assert t410_result["allowed_mode"] == "SHADOW_ONLY"
    assert t410_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t410_result["testnet_submit_allowed"] is False
    assert t410_result["real_submit_allowed"] is False
    assert t410_result["submit_attempted"] is False
    assert t410_result["cancel_attempted"] is False
    assert t410_result["flatten_attempted"] is False
    assert t410_result["gap_closure_field_count"] == 0
    assert t410_result["gap_closure_records_built"] == 0
    assert t410_result["valid_for_gap_closure"] is False
    assert t410_result["previous_gap"] == 22
    assert t410_result["estimated_gap_after_trust_check"] == 22
    assert t410_result["readiness_status"] == "NOT_READY"
    assert t410_result["final_decision"] == "CONTINUE_SHADOW_COLLECTION"
    assert "SHADOW_ONLY" in t410_result["allowed_actions"]
    assert "SHADOW_COLLECTION" in t410_result["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in t410_result["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in t410_result["allowed_actions"]
    assert t410_result["archive_range"] == "T208-T410"
    assert t410_result["next_recommended_task_range"] == "T411-T415"


def test_scripts_support_json_flag() -> None:
    p1 = t406.build_arg_parser()
    p2 = t407.build_arg_parser()
    p3 = t408.build_arg_parser()
    p4 = t409.build_arg_parser()
    p5 = t410.build_arg_parser()

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
