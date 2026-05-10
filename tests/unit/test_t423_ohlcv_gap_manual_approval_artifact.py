import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_ohlcv_gap_manual_approval_artifact_v1 import generate_ohlcv_gap_manual_approval_artifact_v1


def test_manual_review_passed_operator_approved(tmp_path):
    checklist_interpretation = {
        "task_id": "T422",
        "manual_review_status": "PASSED",
        "manual_review_passed": True,
        "manual_operator_approved": True,
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }

    result = generate_ohlcv_gap_manual_approval_artifact_v1(
        checklist_interpretation=checklist_interpretation
    )

    assert result["approval_artifact_ready"] is True
    assert result["approval_scope"] == "OHLCV_GAP_VALIDATION_ONLY"
    assert result["approval_does_not_allow_testnet_dry_run"] is True
    assert result["approval_does_not_allow_submit"] is True


def test_manual_review_pending(tmp_path):
    checklist_interpretation = {
        "task_id": "T422",
        "manual_review_status": "PENDING",
        "manual_review_passed": False,
        "manual_operator_approved": False,
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }

    result = generate_ohlcv_gap_manual_approval_artifact_v1(
        checklist_interpretation=checklist_interpretation
    )

    assert result["approval_artifact_ready"] is False
    assert len(result["blocking_reasons"]) > 0
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_manual_review_failed_or_blocked(tmp_path):
    # Test FAILED
    checklist_interpretation_failed = {
        "task_id": "T422",
        "manual_review_status": "FAILED",
        "manual_review_passed": False,
        "manual_operator_approved": False,
        "review_failures": ["Checklist item failed"],
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }
    result_failed = generate_ohlcv_gap_manual_approval_artifact_v1(
        checklist_interpretation=checklist_interpretation_failed
    )
    assert result_failed["approval_artifact_ready"] is False
    assert result_failed["final_verdict"] in ["PARTIAL", "FAIL"]
    assert len(result_failed["blocking_reasons"]) > 0

    # Test BLOCKED
    checklist_interpretation_blocked = {
        "task_id": "T422",
        "manual_review_status": "BLOCKED",
        "manual_review_passed": False,
        "manual_operator_approved": False,
        "review_failures": ["Manual review packet not ready"],
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }
    result_blocked = generate_ohlcv_gap_manual_approval_artifact_v1(
        checklist_interpretation=checklist_interpretation_blocked
    )
    assert result_blocked["approval_artifact_ready"] is False
    assert result_blocked["final_verdict"] in ["PARTIAL", "FAIL"]
    assert len(result_blocked["blocking_reasons"]) > 0


def test_safety_flags(tmp_path):
    result = generate_ohlcv_gap_manual_approval_artifact_v1()
    assert result["allowed_mode"] == "SHADOW_ONLY"
    assert result["collection_mode"] == "SHADOW_COLLECTION"
    assert result["submit_permission"] == "NO_SUBMIT"
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["submit_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["flatten_attempted"] is False


def test_allowed_actions(tmp_path):
    result = generate_ohlcv_gap_manual_approval_artifact_v1()
    assert "SHADOW_ONLY" in result["allowed_actions"]
    assert "SHADOW_COLLECTION" in result["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in result["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_archive_task_range(tmp_path):
    result = generate_ohlcv_gap_manual_approval_artifact_v1()
    assert result["archive_range"] == "T208-T423"
    assert result["next_recommended_task_range"] == "T424-T425"


def test_json_flag_works(tmp_path):
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent.parent.parent / "scripts" / "generate_ohlcv_gap_manual_approval_artifact_v1.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T423"
