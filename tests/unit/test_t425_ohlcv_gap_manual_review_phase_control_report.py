import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_ohlcv_gap_manual_review_phase_control_report_v1 import generate_ohlcv_gap_manual_review_phase_control_report_v1


def test_manual_gate_passed(tmp_path):
    manual_gate_report = {
        "task_id": "T424",
        "final_gate_passed": True,
        "final_gate_status": "PASSED",
        "approval_scope": "OHLCV_GAP_VALIDATION_ONLY"
    }

    result = generate_ohlcv_gap_manual_review_phase_control_report_v1(
        manual_gate_report=manual_gate_report
    )

    assert result["manual_review_phase_completed"] is True
    assert result["phase_completion_status"] == "COMPLETED_PENDING_PRE_DRY_RUN_REVIEW"
    assert result["next_phase"] == "PRE_DRY_RUN_READINESS_REVIEW"
    assert result["testnet_dry_run_still_blocked"] is True
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_manual_gate_pending(tmp_path):
    manual_gate_report = {
        "task_id": "T424",
        "final_gate_passed": False,
        "final_gate_status": "PENDING",
        "approval_scope": "OHLCV_GAP_VALIDATION_ONLY",
        "blocking_reasons": ["Manual operator not approved"]
    }

    result = generate_ohlcv_gap_manual_review_phase_control_report_v1(
        manual_gate_report=manual_gate_report
    )

    assert result["manual_review_phase_completed"] is False
    assert result["phase_completion_status"] == "CONTINUE_MANUAL_REVIEW"
    assert result["final_verdict"] == "PARTIAL"
    assert len(result["blocked_reasons"]) > 0


def test_manual_gate_failed_or_blocked(tmp_path):
    manual_gate_report_failed = {
        "task_id": "T424",
        "final_gate_passed": False,
        "final_gate_status": "FAILED",
        "approval_scope": "OHLCV_GAP_VALIDATION_ONLY",
        "blocking_reasons": ["Manual review not passed"]
    }
    result_failed = generate_ohlcv_gap_manual_review_phase_control_report_v1(
        manual_gate_report=manual_gate_report_failed
    )
    assert result_failed["phase_completion_status"] == "FAIL_SAFE_BLOCK"
    assert result_failed["final_verdict"] == "FAIL"

    manual_gate_report_blocked = {
        "task_id": "T424",
        "final_gate_passed": False,
        "final_gate_status": "BLOCKED",
        "approval_scope": "OHLCV_GAP_VALIDATION_ONLY",
        "blocking_reasons": ["Manual review packet not ready"]
    }
    result_blocked = generate_ohlcv_gap_manual_review_phase_control_report_v1(
        manual_gate_report=manual_gate_report_blocked
    )
    assert result_blocked["phase_completion_status"] == "FAIL_SAFE_BLOCK"
    assert result_blocked["final_verdict"] == "FAIL"


def test_safety_flags(tmp_path):
    result = generate_ohlcv_gap_manual_review_phase_control_report_v1()
    assert result["allowed_mode"] == "SHADOW_ONLY"
    assert result["collection_mode"] == "SHADOW_COLLECTION"
    assert result["submit_permission"] == "NO_SUBMIT"
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["submit_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["flatten_attempted"] is False


def test_archive_task_range(tmp_path):
    result = generate_ohlcv_gap_manual_review_phase_control_report_v1()
    assert result["archive_range"] == "T208-T425"
    assert result["completed_task_range"] == "T421-T425"
    assert result["next_recommended_task_range"] == "T426-T430"


def test_json_flag_works(tmp_path):
    project_root = str(Path(__file__).parent.parent.parent)
    proc = subprocess.Popen(
        [sys.executable, str(Path(project_root) / "scripts" / "generate_ohlcv_gap_manual_review_phase_control_report_v1.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
        env={**os.environ, "QQ_RUNTIME_MODE": "dry-run", "PYTHONPATH": project_root}
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T425"
