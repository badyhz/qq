import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.interpret_ohlcv_gap_manual_review_checklist_v1 import interpret_ohlcv_gap_manual_review_checklist_v1


def test_checklist_all_pass_operator_not_approved(tmp_path):
    review_packet = {
        "task_id": "T421",
        "manual_review_packet_ready": True,
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }

    checklist_result = {
        "gap_validation_result_reviewed": True,
        "ledger_idempotency_reviewed": True,
        "safety_flags_reviewed": True,
        "no_testnet_dry_run_permission_confirmed": True,
        "no_submit_permission_confirmed": True,
        "manual_operator_approval_required": True,
        "manual_operator_approved": False
    }

    result = interpret_ohlcv_gap_manual_review_checklist_v1(
        review_packet=review_packet,
        checklist_result=checklist_result
    )

    assert result["manual_review_status"] == "PENDING"
    assert result["manual_review_passed"] is False
    assert "TESTNET_DRY_RUN_BLOCKED" in result["allowed_actions"]


def test_checklist_all_pass_operator_approved(tmp_path):
    review_packet = {
        "task_id": "T421",
        "manual_review_packet_ready": True,
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }

    checklist_result = {
        "gap_validation_result_reviewed": True,
        "ledger_idempotency_reviewed": True,
        "safety_flags_reviewed": True,
        "no_testnet_dry_run_permission_confirmed": True,
        "no_submit_permission_confirmed": True,
        "manual_operator_approval_required": True,
        "manual_operator_approved": True
    }

    result = interpret_ohlcv_gap_manual_review_checklist_v1(
        review_packet=review_packet,
        checklist_result=checklist_result
    )

    assert result["manual_review_status"] == "PASSED"
    assert result["manual_review_passed"] is True
    assert result["testnet_submit_allowed"] is False
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_checklist_has_failures(tmp_path):
    review_packet = {
        "task_id": "T421",
        "manual_review_packet_ready": True,
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }

    checklist_result = {
        "gap_validation_result_reviewed": True,
        "ledger_idempotency_reviewed": False,
        "safety_flags_reviewed": True,
        "no_testnet_dry_run_permission_confirmed": True,
        "no_submit_permission_confirmed": True,
        "manual_operator_approval_required": True,
        "manual_operator_approved": True
    }

    result = interpret_ohlcv_gap_manual_review_checklist_v1(
        review_packet=review_packet,
        checklist_result=checklist_result
    )

    assert result["manual_review_status"] == "FAILED"
    assert len(result["review_failures"]) > 0
    assert result["manual_review_passed"] is False


def test_packet_not_ready(tmp_path):
    review_packet = {
        "task_id": "T421",
        "manual_review_packet_ready": False,
        "allowed_actions": ["SHADOW_ONLY", "SHADOW_COLLECTION", "TESTNET_DRY_RUN_BLOCKED"]
    }

    result = interpret_ohlcv_gap_manual_review_checklist_v1(
        review_packet=review_packet
    )

    assert result["manual_review_status"] in ["BLOCKED", "PENDING"]
    assert result["manual_review_passed"] is False


def test_safety_flags(tmp_path):
    result = interpret_ohlcv_gap_manual_review_checklist_v1()
    assert result["allowed_mode"] == "SHADOW_ONLY"
    assert result["collection_mode"] == "SHADOW_COLLECTION"
    assert result["submit_permission"] == "NO_SUBMIT"
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["submit_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["flatten_attempted"] is False


def test_archive_task_range(tmp_path):
    result = interpret_ohlcv_gap_manual_review_checklist_v1()
    assert result["archive_range"] == "T208-T422"
    assert result["next_recommended_task_range"] == "T423-T425"


def test_json_flag_works(tmp_path):
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent.parent.parent / "scripts" / "interpret_ohlcv_gap_manual_review_checklist_v1.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T422"
