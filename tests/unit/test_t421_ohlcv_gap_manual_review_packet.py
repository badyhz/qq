import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_ohlcv_gap_manual_review_packet_v1 import generate_ohlcv_gap_manual_review_packet_v1


def test_gap_validated_pending_review(tmp_path):
    control_report = {
        "task_id": "T420",
        "readiness_status": "GAP_VALIDATED_PENDING_REVIEW",
        "final_decision": "READY_FOR_MANUAL_REVIEW_AFTER_GAP_VALIDATION",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "idempotency_ok": True,
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }

    result = generate_ohlcv_gap_manual_review_packet_v1(
        control_report=control_report
    )

    assert result["manual_review_required"] is True
    assert result["manual_review_packet_ready"] is True
    assert result["final_verdict"] == "PASS"
    assert result["source_final_decision"] == "READY_FOR_MANUAL_REVIEW_AFTER_GAP_VALIDATION"


def test_gap_not_closed(tmp_path):
    control_report = {
        "task_id": "T420",
        "readiness_status": "NOT_READY",
        "final_decision": "CONTINUE_SHADOW_COLLECTION",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "idempotency_ok": True,
        "estimated_gap_after_validation": 20,
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }

    result = generate_ohlcv_gap_manual_review_packet_v1(
        control_report=control_report
    )

    assert result["manual_review_packet_ready"] is False
    assert len(result["blocking_findings"]) > 0
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_fail_safe(tmp_path):
    control_report = {
        "task_id": "T420",
        "readiness_status": "FAIL",
        "final_decision": "FAIL_SAFE_BLOCK",
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "idempotency_ok": False,
        "blocked_reasons": ["Ledger idempotency check failed"],
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }

    result = generate_ohlcv_gap_manual_review_packet_v1(
        control_report=control_report
    )

    assert result["final_verdict"] == "FAIL"


def test_safety_flags(tmp_path):
    result = generate_ohlcv_gap_manual_review_packet_v1()
    assert result["allowed_mode"] == "SHADOW_ONLY"
    assert result["collection_mode"] == "SHADOW_COLLECTION"
    assert result["submit_permission"] == "NO_SUBMIT"
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["submit_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["flatten_attempted"] is False


def test_allowed_actions(tmp_path):
    result = generate_ohlcv_gap_manual_review_packet_v1()
    assert "SHADOW_ONLY" in result["allowed_actions"]
    assert "SHADOW_COLLECTION" in result["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in result["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_archive_task_range(tmp_path):
    result = generate_ohlcv_gap_manual_review_packet_v1()
    assert result["archive_range"] == "T208-T421"
    assert result["next_recommended_task_range"] == "T422-T425"


def test_json_flag_works(tmp_path):
    project_root = str(Path(__file__).parent.parent.parent)
    proc = subprocess.Popen(
        [sys.executable, str(Path(project_root) / "scripts" / "generate_ohlcv_gap_manual_review_packet_v1.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
        env={**os.environ, "QQ_RUNTIME_MODE": "dry-run", "PYTHONPATH": project_root}
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T421"
