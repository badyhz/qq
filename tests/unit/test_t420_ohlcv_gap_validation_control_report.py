import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_ohlcv_gap_validation_control_report_v1 import generate_ohlcv_gap_validation_control_report_v1


def test_gap_not_closed(tmp_path):
    dry_check_result = {
        "task_id": "T418",
        "previous_gap": 22,
        "validated_sample_count": 2,
        "estimated_gap_after_validation": 20,
        "gap_delta": -2,
        "gap_validation_effective": True,
        "still_not_ready": True
    }

    ledger_result = {
        "task_id": "T419",
        "ledger_updated": True,
        "idempotency_ok": True
    }

    result = generate_ohlcv_gap_validation_control_report_v1(
        dry_check_result=dry_check_result,
        ledger_result=ledger_result
    )

    assert result["estimated_gap_after_validation"] == 20
    assert result["readiness_status"] == "NOT_READY"
    assert "TESTNET_DRY_RUN_BLOCKED" in result["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_gap_closed(tmp_path):
    dry_check_result = {
        "task_id": "T418",
        "previous_gap": 22,
        "validated_sample_count": 22,
        "estimated_gap_after_validation": 0,
        "gap_delta": -22,
        "gap_validation_effective": True,
        "still_not_ready": False
    }

    ledger_result = {
        "task_id": "T419",
        "ledger_updated": True,
        "idempotency_ok": True
    }

    result = generate_ohlcv_gap_validation_control_report_v1(
        dry_check_result=dry_check_result,
        ledger_result=ledger_result
    )

    assert result["estimated_gap_after_validation"] == 0
    assert result["readiness_status"] == "GAP_VALIDATED_PENDING_REVIEW"
    assert result["final_decision"] == "READY_FOR_MANUAL_REVIEW_AFTER_GAP_VALIDATION"
    assert result["testnet_submit_allowed"] is False
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_idempotency_failure(tmp_path):
    ledger_result = {
        "task_id": "T419",
        "ledger_updated": False,
        "idempotency_ok": False
    }

    result = generate_ohlcv_gap_validation_control_report_v1(
        ledger_result=ledger_result
    )

    assert result["final_decision"] == "FAIL_SAFE_BLOCK"
    assert result["final_verdict"] == "FAIL"


def test_safety_flags(tmp_path):
    result = generate_ohlcv_gap_validation_control_report_v1()
    assert result["allowed_mode"] == "SHADOW_ONLY"
    assert result["collection_mode"] == "SHADOW_COLLECTION"
    assert result["submit_permission"] == "NO_SUBMIT"
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["submit_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["flatten_attempted"] is False


def test_archive_task_range(tmp_path):
    result = generate_ohlcv_gap_validation_control_report_v1()
    assert result["archive_range"] == "T208-T420"
    assert result["next_recommended_task_range"] == "T421-T425"


def test_json_flag_works(tmp_path):
    project_root = str(Path(__file__).parent.parent.parent)
    proc = subprocess.Popen(
        [sys.executable, str(Path(project_root) / "scripts" / "generate_ohlcv_gap_validation_control_report_v1.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
        env={**os.environ, "QQ_RUNTIME_MODE": "dry-run", "PYTHONPATH": project_root}
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T420"
