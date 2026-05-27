import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_ohlcv_gap_manual_approval_gate_report_v1 import generate_ohlcv_gap_manual_approval_gate_report_v1


def test_all_approval_conditions_met(tmp_path):
    review_packet = {
        "task_id": "T421",
        "manual_review_packet_ready": True
    }
    checklist_interpretation = {
        "task_id": "T422",
        "manual_review_passed": True,
        "manual_operator_approved": True
    }
    approval_artifact = {
        "task_id": "T423",
        "approval_artifact_ready": True,
        "approval_scope": "OHLCV_GAP_VALIDATION_ONLY"
    }

    result = generate_ohlcv_gap_manual_approval_gate_report_v1(
        review_packet=review_packet,
        checklist_interpretation=checklist_interpretation,
        approval_artifact=approval_artifact
    )

    assert result["final_gate_passed"] is True
    assert result["final_gate_status"] == "PASSED"
    assert result["final_verdict"] == "PASS"
    assert result["testnet_submit_allowed"] is False
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_approval_artifact_not_ready(tmp_path):
    review_packet = {
        "task_id": "T421",
        "manual_review_packet_ready": True
    }
    checklist_interpretation = {
        "task_id": "T422",
        "manual_review_passed": True,
        "manual_operator_approved": True
    }
    approval_artifact = {
        "task_id": "T423",
        "approval_artifact_ready": False,
        "approval_scope": "OHLCV_GAP_VALIDATION_ONLY"
    }

    result = generate_ohlcv_gap_manual_approval_gate_report_v1(
        review_packet=review_packet,
        checklist_interpretation=checklist_interpretation,
        approval_artifact=approval_artifact
    )

    assert result["final_gate_passed"] is False
    assert result["final_gate_status"] in ["PENDING", "BLOCKED"]
    assert len(result["blocking_reasons"]) > 0


def test_manual_operator_not_approved(tmp_path):
    review_packet = {
        "task_id": "T421",
        "manual_review_packet_ready": True
    }
    checklist_interpretation = {
        "task_id": "T422",
        "manual_review_passed": True,
        "manual_operator_approved": False
    }
    approval_artifact = {
        "task_id": "T423",
        "approval_artifact_ready": True,
        "approval_scope": "OHLCV_GAP_VALIDATION_ONLY"
    }

    result = generate_ohlcv_gap_manual_approval_gate_report_v1(
        review_packet=review_packet,
        checklist_interpretation=checklist_interpretation,
        approval_artifact=approval_artifact
    )

    assert result["final_gate_passed"] is False
    assert result["final_gate_status"] == "PENDING"
    assert len(result["blocking_reasons"]) > 0


def test_wrong_approval_scope(tmp_path):
    review_packet = {
        "task_id": "T421",
        "manual_review_packet_ready": True
    }
    checklist_interpretation = {
        "task_id": "T422",
        "manual_review_passed": True,
        "manual_operator_approved": True
    }
    approval_artifact = {
        "task_id": "T423",
        "approval_artifact_ready": True,
        "approval_scope": "WRONG_SCOPE"
    }

    result = generate_ohlcv_gap_manual_approval_gate_report_v1(
        review_packet=review_packet,
        checklist_interpretation=checklist_interpretation,
        approval_artifact=approval_artifact
    )

    assert result["final_gate_passed"] is False
    assert result["final_gate_status"] in ["FAILED", "BLOCKED"]


def test_safety_flags(tmp_path):
    result = generate_ohlcv_gap_manual_approval_gate_report_v1()
    assert result["allowed_mode"] == "SHADOW_ONLY"
    assert result["collection_mode"] == "SHADOW_COLLECTION"
    assert result["submit_permission"] == "NO_SUBMIT"
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["submit_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["flatten_attempted"] is False


def test_archive_task_range(tmp_path):
    result = generate_ohlcv_gap_manual_approval_gate_report_v1()
    assert result["archive_range"] == "T208-T424"
    assert result["next_recommended_task_range"] == "T425"


def test_json_flag_works(tmp_path):
    project_root = str(Path(__file__).parent.parent.parent)
    proc = subprocess.Popen(
        [sys.executable, str(Path(project_root) / "scripts" / "generate_ohlcv_gap_manual_approval_gate_report_v1.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
        env={**os.environ, "QQ_RUNTIME_MODE": "dry-run", "PYTHONPATH": project_root}
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T424"
