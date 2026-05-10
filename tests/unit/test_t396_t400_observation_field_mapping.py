"""Targeted acceptance test for T396-T400 observation field mapping."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import scripts.audit_observation_sample_store_schema as t396
import scripts.generate_observation_field_mapping_v1 as t397
import scripts.build_enriched_real_shadow_records as t398
import scripts.validate_enriched_real_shadow_records as t399
import scripts.generate_enriched_shadow_collection_control_report as t400


def test_t396_t400_observation_field_mapping(tmp_path: Path) -> None:
    # Create mock observation_samples.csv with OHLCV
    csv_dir = tmp_path / "observation_sample_store"
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / "observation_samples.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["symbol", "timeframe", "strategy_key", "created_at", "open", "high", "low", "close", "volume"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "strategy_key": "test_setup",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "open": "60000.0",
                "high": "60500.0",
                "low": "59500.0",
                "close": "60200.0",
                "volume": "1000.0",
            }
        )
        writer.writerow(
            {
                "symbol": "ETHUSDT",
                "timeframe": "4h",
                "strategy_key": "test_setup_2",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "open": "3000.0",
                "high": "3050.0",
                "low": "2950.0",
                "close": "3020.0",
                "volume": "500.0",
            }
        )

    # T396: Audit schema
    t396_result = t396.audit_observation_sample_store_schema(
        source_path=str(csv_path),
        output_dir=str(tmp_path / "audit_output"),
    )
    assert t396_result["task_id"] == "T396"
    assert t396_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t396_result["allowed_mode"] == "SHADOW_ONLY"
    assert t396_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t396_result["submit_permission"] == "NO_SUBMIT"
    assert t396_result["testnet_submit_allowed"] is False
    assert t396_result["real_submit_allowed"] is False
    assert t396_result["submit_attempted"] is False
    assert t396_result["cancel_attempted"] is False
    assert t396_result["flatten_attempted"] is False

    # T397: Generate mapping
    t397_result = t397.generate_observation_field_mapping_v1(
        audit_result=t396_result,
        output_dir=str(tmp_path / "mapping_output"),
    )
    assert t397_result["task_id"] == "T397"
    assert t397_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t397_result["allowed_mode"] == "SHADOW_ONLY"
    assert t397_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t397_result["testnet_submit_allowed"] is False
    assert t397_result["real_submit_allowed"] is False
    assert t397_result["fallback_values_used"] is False

    # T398: Build enriched records
    t398_result = t398.build_enriched_real_shadow_records(
        audit_result=t396_result,
        mapping_result=t397_result,
        source_path=str(csv_path),
        output_dir=str(tmp_path / "build_output"),
    )
    assert t398_result["task_id"] == "T398"
    assert t398_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t398_result["allowed_mode"] == "SHADOW_ONLY"
    assert t398_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t398_result["testnet_submit_allowed"] is False
    assert t398_result["real_submit_allowed"] is False
    assert t398_result["fallback_values_used"] is False
    for record in t398_result["records"]:
        assert record["synthetic_placeholder"] is False
        assert record["observation_only"] is True
        assert "order_id" not in record
        assert "client_order_id" not in record
        assert "submit_payload" not in record
        assert "cancel_payload" not in record
        assert "flatten_payload" not in record

    # T399: Validate enriched records
    t399_result = t399.validate_enriched_real_shadow_records(
        build_result=t398_result,
        output_dir=str(tmp_path / "validation_output"),
    )
    assert t399_result["task_id"] == "T399"
    assert t399_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t399_result["allowed_mode"] == "SHADOW_ONLY"
    assert t399_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t399_result["testnet_submit_allowed"] is False
    assert t399_result["real_submit_allowed"] is False
    assert t399_result["fallback_values_detected"] is False

    # T400: Generate control report
    t400_result = t400.generate_enriched_shadow_collection_control_report(
        audit_result=t396_result,
        mapping_result=t397_result,
        build_result=t398_result,
        validation_result=t399_result,
        output_dir=str(tmp_path / "control_report_output"),
    )
    assert t400_result["task_id"] == "T400"
    assert t400_result["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t400_result["allowed_mode"] == "SHADOW_ONLY"
    assert t400_result["collection_mode"] == "SHADOW_COLLECTION"
    assert t400_result["testnet_submit_allowed"] is False
    assert t400_result["real_submit_allowed"] is False
    assert t400_result["readiness_status"] in ("NOT_READY", "READY", "FAIL", "UNKNOWN")
    assert t400_result["final_decision"] in ("CONTINUE_SHADOW_COLLECTION", "CONTINUE_SHADOW_ONLY", "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW", "FAIL_SAFE_BLOCK")
    assert t400_result["archive_range"] == "T208-T400"
    assert t400_result["next_recommended_task_range"] == "T401-T405"
    assert "SHADOW_ONLY" in t400_result["allowed_actions"]
    assert "SHADOW_COLLECTION" in t400_result["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in t400_result["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in t400_result["allowed_actions"]

    # Test case without OHLCV
    csv_path_no_ohlcv = csv_dir / "observation_samples_no_ohlcv.csv"
    with open(csv_path_no_ohlcv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["symbol", "timeframe", "strategy_key", "created_at"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "strategy_key": "test_setup",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    t396_result_no_ohlcv = t396.audit_observation_sample_store_schema(
        source_path=str(csv_path_no_ohlcv),
        output_dir=str(tmp_path / "audit_output_no_ohlcv"),
    )
    assert t396_result_no_ohlcv["ohlcv_fields_present"] is False
    t397_result_no_ohlcv = t397.generate_observation_field_mapping_v1(
        audit_result=t396_result_no_ohlcv,
        output_dir=str(tmp_path / "mapping_output_no_ohlcv"),
    )
    assert t397_result_no_ohlcv["mapping_ready"] is False


def test_scripts_support_json_flag() -> None:
    p1 = t396.build_arg_parser()
    p2 = t397.build_arg_parser()
    p3 = t398.build_arg_parser()
    p4 = t399.build_arg_parser()
    p5 = t400.build_arg_parser()

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
