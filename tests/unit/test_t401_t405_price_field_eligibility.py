"""Targeted acceptance test for T401-T405 price field eligibility."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import scripts.audit_observation_price_field_candidates as t401
import scripts.generate_price_field_candidate_mapping_v1 as t402
import scripts.build_normalized_price_observation_records as t403
import scripts.validate_normalized_price_observation_records as t404
import scripts.generate_price_field_eligibility_control_report as t405


def test_t401_t405_price_field_eligibility(tmp_path: Path) -> None:
    # Create mock observation_samples.csv with price fields
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

    # T401: Audit price field candidates
    t401_result = t401.audit_observation_price_field_candidates(
        source_path=str(csv_path),
        output_dir=str(tmp_path / "t401_output"),
    )
    assert t401_result["task_id"] == "T401"
    assert t401_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t401_result["allowed_mode"] == "SHADOW_ONLY"
    assert t401_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t401_result["submit_permission"] == "NO_SUBMIT"
    assert t401_result["testnet_submit_allowed"] is False
    assert t401_result["real_submit_allowed"] is False
    assert t401_result["submit_attempted"] is False
    assert t401_result["cancel_attempted"] is False
    assert t401_result["flatten_attempted"] is False
    assert "close" in t401_result["candidate_price_fields"]
    assert "last" in t401_result["candidate_price_fields"]
    assert "mark_price" in t401_result["candidate_price_fields"]

    # T402: Generate price field mapping
    t402_result = t402.generate_price_field_candidate_mapping_v1(
        audit_result=t401_result,
        output_dir=str(tmp_path / "t402_output"),
    )
    assert t402_result["task_id"] == "T402"
    assert t402_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t402_result["allowed_mode"] == "SHADOW_ONLY"
    assert t402_result["testnet_submit_allowed"] is False
    assert t402_result["real_submit_allowed"] is False
    assert t402_result["fallback_values_used"] is False
    assert t402_result["primary_price_field"] is not None
    assert t402_result["mapping_ready"] is True

    # T403: Build normalized price records
    t403_result = t403.build_normalized_price_observation_records(
        audit_result=t401_result,
        mapping_result=t402_result,
        source_path=str(csv_path),
        output_dir=str(tmp_path / "t403_output"),
    )
    assert t403_result["task_id"] == "T403"
    assert t403_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t403_result["allowed_mode"] == "SHADOW_ONLY"
    assert t403_result["testnet_submit_allowed"] is False
    assert t403_result["real_submit_allowed"] is False
    assert t403_result["fallback_values_used"] is False
    assert t403_result["records_built"] >= 1
    for record in t403_result["records"]:
        assert record["synthetic_placeholder"] is False
        assert record["observation_only"] is True
        assert "price" in record
        assert "price_source_field" in record
        assert "order_id" not in record
        assert "client_order_id" not in record
        assert "submit_payload" not in record
        assert "cancel_payload" not in record
        assert "flatten_payload" not in record

    # T404: Validate normalized price records
    t404_result = t404.validate_normalized_price_observation_records(
        build_result=t403_result,
        output_dir=str(tmp_path / "t404_output"),
    )
    assert t404_result["task_id"] == "T404"
    assert t404_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t404_result["allowed_mode"] == "SHADOW_ONLY"
    assert t404_result["testnet_submit_allowed"] is False
    assert t404_result["real_submit_allowed"] is False
    assert t404_result["fallback_values_detected"] is False

    # T405: Generate control report
    t405_result = t405.generate_price_field_eligibility_control_report(
        audit_result=t401_result,
        mapping_result=t402_result,
        build_result=t403_result,
        validation_result=t404_result,
        output_dir=str(tmp_path / "t405_output"),
    )
    assert t405_result["task_id"] == "T405"
    assert t405_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t405_result["allowed_mode"] == "SHADOW_ONLY"
    assert t405_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t405_result["testnet_submit_allowed"] is False
    assert t405_result["real_submit_allowed"] is False
    assert t405_result["readiness_status"] in ("NOT_READY", "READY", "FAIL", "UNKNOWN")
    assert t405_result["final_decision"] in ("CONTINUE_SHADOW_COLLECTION", "CONTINUE_SHADOW_ONLY", "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW", "FAIL_SAFE_BLOCK")
    assert t405_result["archive_range"] == "T208-T405"
    assert t405_result["next_recommended_task_range"] == "T406-T410"
    assert "SHADOW_ONLY" in t405_result["allowed_actions"]
    assert "SHADOW_COLLECTION" in t405_result["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in t405_result["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in t405_result["allowed_actions"]

    # Test case without price fields
    csv_path_no_price = csv_dir / "observation_samples_no_price.csv"
    with open(csv_path_no_price, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["symbol", "timeframe", "strategy_key", "created_at", "score", "rank"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "strategy_key": "test_setup",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "score": "0.85",
                "rank": "1",
            }
        )
    t401_result_no_price = t401.audit_observation_price_field_candidates(
        source_path=str(csv_path_no_price),
        output_dir=str(tmp_path / "t401_output_no_price"),
    )
    assert t401_result_no_price["candidate_price_field_count"] == 0
    t402_result_no_price = t402.generate_price_field_candidate_mapping_v1(
        audit_result=t401_result_no_price,
        output_dir=str(tmp_path / "t402_output_no_price"),
    )
    assert t402_result_no_price["mapping_ready"] is False


def test_scripts_support_json_flag() -> None:
    p1 = t401.build_arg_parser()
    p2 = t402.build_arg_parser()
    p3 = t403.build_arg_parser()
    p4 = t404.build_arg_parser()
    p5 = t405.build_arg_parser()

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
