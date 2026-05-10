import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_ohlcv_source_discovery_control_report import generate_ohlcv_source_discovery_control_report


def test_ready_with_records_and_mapping(tmp_path):
    mapping_result = {
        "mapping_ready": True,
        "selected_source_count": 1
    }

    records_result = {
        "records_built": 100
    }

    result = generate_ohlcv_source_discovery_control_report(
        mapping_result=mapping_result,
        records_result=records_result
    )

    assert result["valid_ohlcv_source_available"] is True
    assert result["final_decision"] == "READY_FOR_OHLCV_GAP_VALIDATION"
    assert result["gap_delta"] == 0
    assert result["estimated_gap_after_ohlcv_discovery"] == 22


def test_not_ready_without_mapping_or_records(tmp_path):
    mapping_result = {
        "mapping_ready": False,
        "selected_source_count": 0
    }

    records_result = {
        "records_built": 0
    }

    result = generate_ohlcv_source_discovery_control_report(
        mapping_result=mapping_result,
        records_result=records_result
    )

    assert result["final_decision"] in ["CONTINUE_SHADOW_COLLECTION", "CONTINUE_SHADOW_ONLY"]


def test_safety_flags(tmp_path):
    result = generate_ohlcv_source_discovery_control_report()

    assert result["allowed_mode"] == "SHADOW_ONLY"
    assert result["collection_mode"] == "SHADOW_COLLECTION"
    assert result["submit_permission"] == "NO_SUBMIT"
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["submit_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["flatten_attempted"] is False


def test_allowed_actions_has_no_testnet_dry_run_only(tmp_path):
    result = generate_ohlcv_source_discovery_control_report()

    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]
    assert "SHADOW_ONLY" in result["allowed_actions"]
    assert "SHADOW_COLLECTION" in result["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in result["allowed_actions"]


def test_archive_and_task_ranges(tmp_path):
    result = generate_ohlcv_source_discovery_control_report()

    assert result["archive_range"] == "T208-T415"
    assert result["next_recommended_task_range"] == "T416-T420"


def test_json_flag_works(tmp_path):
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent.parent.parent / "scripts" / "generate_ohlcv_source_discovery_control_report.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T415"
