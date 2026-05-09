"""Targeted acceptance test for T386-T390 shadow collection round.

Exercises the five T386-T390 scripts directly without importing
test_signal_outcome.py or modifying any existing test files.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import scripts.run_shadow_collection_round_v1 as t386
import scripts.validate_shadow_collection_output_v1 as t387
import scripts.update_shadow_remediation_history_v1 as t388
import scripts.analyze_shadow_collection_gap_delta_v1 as t389
import scripts.generate_shadow_collection_control_report_v1 as t390


def test_t386_t390_shadow_collection_round(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    data = tmp_path / "data"
    for folder in [
        "shadow_collection_queue_v1",
        "shadow_data_quality_rules_v1",
        "readiness_blocker_attribution",
        "shadow_collection_plan_v4",
        "shadow_collection_round_v1",
        "shadow_collection_output_validation_v1",
        "shadow_remediation_history_update_v1",
        "shadow_collection_gap_delta_v1",
        "shadow_collection_control_report_v1",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    (reports / "shadow_collection_queue_v1" / "shadow_collection_queue_v1.json").write_text(
        json.dumps({
            "task_id": "T381",
            "queue_ready": True,
            "queue_item_count": 4,
            "queue_items": [
                {
                    "queue_id": "QUEUE-001",
                    "symbol": "BTCUSDT",
                    "timeframe": "4h",
                    "setup": "quality_improvement",
                    "target_samples": 3,
                    "priority": "HIGH",
                    "observation_only": True,
                    "reason": "improve_sample_quality",
                },
            ],
        }),
        encoding="utf-8",
    )

    (reports / "shadow_data_quality_rules_v1" / "shadow_data_quality_rules_v1.json").write_text(
        json.dumps({
            "task_id": "T382",
            "rules_version": "v1",
            "required_fields": ["timestamp", "symbol", "timeframe"],
            "dedupe_key_fields": ["timestamp", "symbol", "timeframe"],
            "timestamp_rules": {"required": True, "timezone": "UTC", "allow_future_timestamp": False},
            "coverage_rules": {"min_symbol_coverage": 2, "min_timeframe_coverage": 2, "min_samples_per_bucket": 5},
            "quality_gate_ready": True,
        }),
        encoding="utf-8",
    )

    (reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json").write_text(
        json.dumps({
            "task_id": "T383",
            "readiness_final_verdict": "NOT_READY",
            "blocker_count": 5,
            "blockers": [
                {
                    "code": "SAMPLE_QUALITY_NOT_READY",
                    "severity": "HIGH",
                    "actionable": True,
                    "recommended_action": "improve_shadow_sample_quality",
                },
            ],
        }),
        encoding="utf-8",
    )

    (reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json").write_text(
        json.dumps({
            "task_id": "T378",
            "plan_version": "v4",
            "total_target_samples": 26,
            "collection_items": [],
        }),
        encoding="utf-8",
    )

    r386 = t386.run_shadow_collection_round_v1(
        shadow_collection_queue_v1_json=str(reports / "shadow_collection_queue_v1" / "shadow_collection_queue_v1.json"),
        output_dir=str(reports / "shadow_collection_round_v1"),
    )

    assert r386["task_id"] == "T386"
    assert r386["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert r386["allowed_mode"] == "SHADOW_ONLY"
    assert r386["collection_mode"] == "SHADOW_COLLECTION"
    assert r386["submit_permission"] == "NO_SUBMIT"
    assert r386["testnet_submit_allowed"] is False
    assert r386["real_submit_allowed"] is False
    assert r386["submit_attempted"] is False
    assert r386["cancel_attempted"] is False
    assert r386["flatten_attempted"] is False

    for record in r386["records"]:
        assert record["observation_only"] is True
        assert "order_id" not in record
        assert "client_order_id" not in record
        assert "submit_payload" not in record
        assert "cancel_payload" not in record
        assert "flatten_payload" not in record
        # T390-FIX2: Check synthetic_placeholder and source_type
        assert record["synthetic_placeholder"] is True
        assert record["source_type"] == "QUEUE_PLACEHOLDER"

    r387 = t387.validate_shadow_collection_output_v1(
        shadow_collection_round_v1_json=str(reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json"),
        shadow_data_quality_rules_v1_json=str(reports / "shadow_data_quality_rules_v1" / "shadow_data_quality_rules_v1.json"),
        output_dir=str(reports / "shadow_collection_output_validation_v1"),
    )

    assert r387["task_id"] == "T387"
    assert r387["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert r387["allowed_mode"] == "SHADOW_ONLY"
    assert r387["collection_mode"] == "SHADOW_COLLECTION"
    assert r387["testnet_submit_allowed"] is False
    assert r387["real_submit_allowed"] is False
    assert r387["submit_attempted"] is False
    assert r387["cancel_attempted"] is False
    assert r387["flatten_attempted"] is False
    # T390-FIX2: Check data_authenticity_passed and valid_for_gap_closure are false for placeholder samples
    assert r387["data_authenticity_passed"] is False
    assert r387["valid_for_gap_closure"] is False
    assert len(r387["gap_closure_eligible_records"]) == 0

    r388 = t388.update_shadow_remediation_history_v1(
        shadow_collection_round_v1_json=str(reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json"),
        shadow_collection_output_validation_v1_json=str(reports / "shadow_collection_output_validation_v1" / "shadow_collection_output_validation_v1.json"),
        output_dir=str(reports / "shadow_remediation_history_update_v1"),
        history_dir=str(data / "shadow_remediation_history"),
    )

    assert r388["task_id"] == "T388"
    assert r388["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert r388["allowed_mode"] == "SHADOW_ONLY"
    assert r388["collection_mode"] == "SHADOW_COLLECTION"
    assert r388["testnet_submit_allowed"] is False
    assert r388["real_submit_allowed"] is False
    assert r388["submit_attempted"] is False
    assert r388["cancel_attempted"] is False
    assert r388["flatten_attempted"] is False
    assert r388["idempotency_ok"] is True
    # T390-FIX2: No records added because valid_for_gap_closure is false
    assert r388["history_updated"] is False
    assert r388["new_records_added"] == 0

    r389 = t389.analyze_shadow_collection_gap_delta_v1(
        shadow_remediation_history_update_v1_json=str(reports / "shadow_remediation_history_update_v1" / "shadow_remediation_history_update_v1.json"),
        readiness_blocker_attribution_json=str(reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json"),
        shadow_collection_plan_v4_json=str(reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json"),
        shadow_collection_output_validation_v1_json=str(reports / "shadow_collection_output_validation_v1" / "shadow_collection_output_validation_v1.json"),
        output_dir=str(reports / "shadow_collection_gap_delta_v1"),
    )

    assert r389["task_id"] == "T389"
    assert r389["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert r389["allowed_mode"] == "SHADOW_ONLY"
    assert r389["collection_mode"] == "SHADOW_COLLECTION"
    assert r389["testnet_submit_allowed"] is False
    assert r389["real_submit_allowed"] is False
    assert r389["submit_attempted"] is False
    assert r389["cancel_attempted"] is False
    assert r389["flatten_attempted"] is False
    assert r389["still_not_ready"] is True
    # T390-FIX2: Gap remains unchanged because valid_for_gap_closure is false
    assert r389["previous_gap"] == 22
    assert r389["estimated_gap_after_collection"] == 22
    assert r389["collection_effective"] is False

    r390 = t390.generate_shadow_collection_control_report_v1(
        shadow_collection_round_v1_json=str(reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json"),
        shadow_collection_output_validation_v1_json=str(reports / "shadow_collection_output_validation_v1" / "shadow_collection_output_validation_v1.json"),
        shadow_remediation_history_update_v1_json=str(reports / "shadow_remediation_history_update_v1" / "shadow_remediation_history_update_v1.json"),
        shadow_collection_gap_delta_v1_json=str(reports / "shadow_collection_gap_delta_v1" / "shadow_collection_gap_delta_v1.json"),
        output_dir=str(reports / "shadow_collection_control_report_v1"),
    )

    assert r390["task_id"] == "T390"
    assert r390["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert r390["allowed_mode"] == "SHADOW_ONLY"
    assert r390["collection_mode"] == "SHADOW_COLLECTION"
    assert r390["testnet_submit_allowed"] is False
    assert r390["real_submit_allowed"] is False
    assert r390["submit_attempted"] is False
    assert r390["cancel_attempted"] is False
    assert r390["flatten_attempted"] is False

    # T390-FIX2: Check required outputs
    assert r390["readiness_status"] == "NOT_READY"
    assert r390["final_decision"] == "CONTINUE_SHADOW_COLLECTION"
    assert "SHADOW_COLLECTION" in r390["allowed_actions"]
    assert "SHADOW_ONLY" in r390["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in r390["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in r390["allowed_actions"]

    assert r390["archive_range"] == "T208-T390"
    assert r390["next_recommended_task_range"] == "T391-T395"


def test_t388_idempotency(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    data = tmp_path / "data"
    for folder in [
        "shadow_collection_queue_v1",
        "shadow_data_quality_rules_v1",
        "shadow_collection_round_v1",
        "shadow_collection_output_validation_v1",
        "shadow_remediation_history_update_v1",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    (reports / "shadow_collection_queue_v1" / "shadow_collection_queue_v1.json").write_text(
        json.dumps({
            "task_id": "T381",
            "queue_ready": True,
            "queue_item_count": 1,
            "queue_items": [
                {
                    "queue_id": "QUEUE-001",
                    "symbol": "BTCUSDT",
                    "timeframe": "4h",
                    "setup": "quality_improvement",
                    "target_samples": 2,
                    "priority": "HIGH",
                    "observation_only": True,
                    "reason": "improve_sample_quality",
                },
            ],
        }),
        encoding="utf-8",
    )

    (reports / "shadow_data_quality_rules_v1" / "shadow_data_quality_rules_v1.json").write_text(
        json.dumps({
            "task_id": "T382",
            "rules_version": "v1",
            "required_fields": ["timestamp", "symbol", "timeframe"],
            "dedupe_key_fields": ["timestamp", "symbol", "timeframe"],
            "timestamp_rules": {"required": True, "timezone": "UTC", "allow_future_timestamp": False},
            "coverage_rules": {"min_symbol_coverage": 2, "min_timeframe_coverage": 2, "min_samples_per_bucket": 5},
            "quality_gate_ready": True,
        }),
        encoding="utf-8",
    )

    r386 = t386.run_shadow_collection_round_v1(
        shadow_collection_queue_v1_json=str(reports / "shadow_collection_queue_v1" / "shadow_collection_queue_v1.json"),
        output_dir=str(reports / "shadow_collection_round_v1"),
    )

    r387 = t387.validate_shadow_collection_output_v1(
        shadow_collection_round_v1_json=str(reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json"),
        shadow_data_quality_rules_v1_json=str(reports / "shadow_data_quality_rules_v1" / "shadow_data_quality_rules_v1.json"),
        output_dir=str(reports / "shadow_collection_output_validation_v1"),
    )

    r388_first = t388.update_shadow_remediation_history_v1(
        shadow_collection_round_v1_json=str(reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json"),
        shadow_collection_output_validation_v1_json=str(reports / "shadow_collection_output_validation_v1" / "shadow_collection_output_validation_v1.json"),
        output_dir=str(reports / "shadow_remediation_history_update_v1"),
        history_dir=str(data / "shadow_remediation_history"),
    )

    previous_runs_after = r388_first["history_runs_after"]

    r388_second = t388.update_shadow_remediation_history_v1(
        shadow_collection_round_v1_json=str(reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json"),
        shadow_collection_output_validation_v1_json=str(reports / "shadow_collection_output_validation_v1" / "shadow_collection_output_validation_v1.json"),
        output_dir=str(reports / "shadow_remediation_history_update_v1"),
        history_dir=str(data / "shadow_remediation_history"),
    )

    assert r388_second["idempotency_ok"] is True
    assert r388_second["history_runs_after"] == previous_runs_after


def test_scripts_support_json_flag() -> None:
    p1 = t386.build_arg_parser()
    p2 = t387.build_arg_parser()
    p3 = t388.build_arg_parser()
    p4 = t389.build_arg_parser()
    p5 = t390.build_arg_parser()

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


def test_quality_passed_false_behavior(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    data = tmp_path / "data"
    for folder in [
        "shadow_collection_queue_v1",
        "shadow_data_quality_rules_v1",
        "readiness_blocker_attribution",
        "shadow_collection_plan_v4",
        "shadow_collection_round_v1",
        "shadow_collection_output_validation_v1",
        "shadow_remediation_history_update_v1",
        "shadow_collection_gap_delta_v1",
        "shadow_collection_control_report_v1",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    (reports / "shadow_collection_queue_v1" / "shadow_collection_queue_v1.json").write_text(
        json.dumps({
            "task_id": "T381",
            "queue_ready": True,
            "queue_item_count": 1,
            "queue_items": [
                {
                    "queue_id": "QUEUE-001",
                    "symbol": "BTCUSDT",
                    "timeframe": "4h",
                    "setup": "quality_improvement",
                    "target_samples": 3,
                    "priority": "HIGH",
                    "observation_only": True,
                    "reason": "improve_sample_quality",
                },
            ],
        }),
        encoding="utf-8",
    )

    (reports / "shadow_data_quality_rules_v1" / "shadow_data_quality_rules_v1.json").write_text(
        json.dumps({
            "task_id": "T382",
            "rules_version": "v1",
            "required_fields": ["timestamp", "symbol", "timeframe", "open", "high", "low", "close", "volume"],
            "dedupe_key_fields": ["timestamp", "symbol", "timeframe"],
            "timestamp_rules": {"required": True, "timezone": "UTC", "allow_future_timestamp": False},
            "coverage_rules": {"min_symbol_coverage": 2, "min_timeframe_coverage": 2, "min_samples_per_bucket": 5},
            "quality_gate_ready": True,
        }),
        encoding="utf-8",
    )

    (reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json").write_text(
        json.dumps({
            "task_id": "T383",
            "readiness_final_verdict": "NOT_READY",
            "blocker_count": 5,
            "blockers": [
                {
                    "code": "SAMPLE_QUALITY_NOT_READY",
                    "severity": "HIGH",
                    "actionable": True,
                    "recommended_action": "improve_shadow_sample_quality",
                },
            ],
        }),
        encoding="utf-8",
    )

    (reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json").write_text(
        json.dumps({
            "task_id": "T378",
            "plan_version": "v4",
            "total_target_samples": 26,
            "collection_items": [],
        }),
        encoding="utf-8",
    )

    # Create a manual round with invalid records (missing required fields)
    (reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json").write_text(
        json.dumps({
            "task_id": "T386",
            "queue_ready": True,
            "collection_run_id": "TEST_ROUND",
            "observation_records_generated": 3,
            "records": [
                {
                    "record_id": "REC1",
                    "queue_id": "QUEUE-001",
                    "symbol": "BTCUSDT",
                    "timeframe": "4h",
                    "observation_only": True,
                    "status": "COLLECTED",
                    "reason": "test",
                    # Missing timestamp, open, high, low, close, volume
                },
                {
                    "record_id": "REC2",
                    "queue_id": "QUEUE-001",
                    "symbol": "BTCUSDT",
                    "timeframe": "4h",
                    "observation_only": True,
                    "status": "COLLECTED",
                    "reason": "test",
                    # Missing timestamp, open, high, low, close, volume
                },
            ],
        }),
        encoding="utf-8",
    )

    r387 = t387.validate_shadow_collection_output_v1(
        shadow_collection_round_v1_json=str(reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json"),
        shadow_data_quality_rules_v1_json=str(reports / "shadow_data_quality_rules_v1" / "shadow_data_quality_rules_v1.json"),
        output_dir=str(reports / "shadow_collection_output_validation_v1"),
    )

    (reports / "shadow_remediation_history_update_v1" / "shadow_remediation_history_update_v1.json").write_text(
        json.dumps({
            "task_id": "T388",
            "history_updated": False,
            "new_records_added": 0,
            "previous_history_runs": 0,
            "history_runs_after": 0,
        }),
        encoding="utf-8",
    )

    r389 = t389.analyze_shadow_collection_gap_delta_v1(
        shadow_remediation_history_update_v1_json=str(reports / "shadow_remediation_history_update_v1" / "shadow_remediation_history_update_v1.json"),
        readiness_blocker_attribution_json=str(reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json"),
        shadow_collection_plan_v4_json=str(reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json"),
        shadow_collection_output_validation_v1_json=str(reports / "shadow_collection_output_validation_v1" / "shadow_collection_output_validation_v1.json"),
        output_dir=str(reports / "shadow_collection_gap_delta_v1"),
    )

    (reports / "shadow_collection_gap_delta_v1" / "shadow_collection_gap_delta_v1.json").write_text(
        json.dumps({
            "task_id": "T389",
            "previous_gap": 22,
            "new_records_added": 0,
            "estimated_gap_after_collection": 22,
            "gap_delta": 0,
            "collection_effective": False,
            "still_not_ready": True,
        }),
        encoding="utf-8",
    )

    r390 = t390.generate_shadow_collection_control_report_v1(
        shadow_collection_round_v1_json=str(reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json"),
        shadow_collection_output_validation_v1_json=str(reports / "shadow_collection_output_validation_v1" / "shadow_collection_output_validation_v1.json"),
        shadow_remediation_history_update_v1_json=str(reports / "shadow_remediation_history_update_v1" / "shadow_remediation_history_update_v1.json"),
        shadow_collection_gap_delta_v1_json=str(reports / "shadow_collection_gap_delta_v1" / "shadow_collection_gap_delta_v1.json"),
        output_dir=str(reports / "shadow_collection_control_report_v1"),
    )

    # Check T388 behavior when quality_passed=false
    assert r387["quality_passed"] is False or r387["valid_records"] == 0
    # T390-FIX2: Also check data_authenticity_passed and valid_for_gap_closure are false
    assert r387["data_authenticity_passed"] is False
    assert r387["valid_for_gap_closure"] is False

    # Check T389 - gap should not decrease when quality_passed=false
    assert r389["previous_gap"] == 22
    assert r389["estimated_gap_after_collection"] == 22
    assert r389["gap_delta"] == 0
    assert r389["collection_effective"] is False

    # Check T390
    assert r390["collection_effective"] is False
    assert r390["readiness_status"] == "NOT_READY"
    assert r390["final_decision"] == "CONTINUE_SHADOW_COLLECTION"
    assert "quality_passed=false" in r390["blocked_reasons"]
    assert "valid_for_gap_closure=false" in r390["blocked_reasons"]
    assert "SHADOW_COLLECTION" in r390["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in r390["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in r390["allowed_actions"]


def test_authentic_records_behavior(tmp_path: Path) -> None:
    # Test that authentic (non-synthetic) records from real sources pass authenticity checks
    reports = tmp_path / "reports"
    data = tmp_path / "data"
    for folder in [
        "shadow_collection_queue_v1",
        "shadow_data_quality_rules_v1",
        "shadow_collection_round_v1",
        "shadow_collection_output_validation_v1",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    (reports / "shadow_data_quality_rules_v1" / "shadow_data_quality_rules_v1.json").write_text(
        json.dumps({
            "task_id": "T382",
            "rules_version": "v1",
            "required_fields": ["timestamp", "symbol", "timeframe"],
            "dedupe_key_fields": ["timestamp", "symbol", "timeframe"],
            "timestamp_rules": {"required": True, "timezone": "UTC", "allow_future_timestamp": False},
            "coverage_rules": {"min_symbol_coverage": 2, "min_timeframe_coverage": 2, "min_samples_per_bucket": 5},
            "quality_gate_ready": True,
        }),
        encoding="utf-8",
    )

    # Create a manual round with authentic records from SHADOW_LOG
    (reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json").write_text(
        json.dumps({
            "task_id": "T386",
            "queue_ready": True,
            "collection_run_id": "TEST_AUTHENTIC_ROUND",
            "observation_records_generated": 2,
            "records": [
                {
                    "record_id": "AUTH_REC1",
                    "queue_id": "QUEUE-001",
                    "symbol": "BTCUSDT",
                    "timeframe": "4h",
                    "setup": "quality_improvement",
                    "observation_only": True,
                    "target_sample_index": 0,
                    "status": "COLLECTED",
                    "reason": "shadow observation collected",
                    "timestamp": "2024-01-01T00:00:00+00:00",
                    "open": 42000.0,
                    "high": 42500.0,
                    "low": 41800.0,
                    "close": 42200.0,
                    "volume": 1000.0,
                    "synthetic_placeholder": False,
                    "source_type": "SHADOW_LOG",
                },
                {
                    "record_id": "AUTH_REC2",
                    "queue_id": "QUEUE-001",
                    "symbol": "BTCUSDT",
                    "timeframe": "4h",
                    "setup": "quality_improvement",
                    "observation_only": True,
                    "target_sample_index": 1,
                    "status": "COLLECTED",
                    "reason": "shadow observation collected",
                    "timestamp": "2024-01-01T04:00:00+00:00",
                    "open": 42200.0,
                    "high": 42800.0,
                    "low": 42000.0,
                    "close": 42600.0,
                    "volume": 1200.0,
                    "synthetic_placeholder": False,
                    "source_type": "SHADOW_LOG",
                },
            ],
        }),
        encoding="utf-8",
    )

    r387 = t387.validate_shadow_collection_output_v1(
        shadow_collection_round_v1_json=str(reports / "shadow_collection_round_v1" / "shadow_collection_round_v1.json"),
        shadow_data_quality_rules_v1_json=str(reports / "shadow_data_quality_rules_v1" / "shadow_data_quality_rules_v1.json"),
        output_dir=str(reports / "shadow_collection_output_validation_v1"),
    )

    # Authentic records should pass data_authenticity_passed and valid_for_gap_closure
    assert r387["quality_passed"] is True
    assert r387["data_authenticity_passed"] is True
    assert r387["valid_for_gap_closure"] is True
    assert len(r387["gap_closure_eligible_records"]) == 2
