import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_manual_pre_dry_run_review_packet_v1 import (
    generate_review_packet,
    load_json,
    write_json
)


def test_ready_t430_generates_ready_packet(tmp_path):
    t430_report = {
        "ok": True,
        "task": "T430",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "phase_completion_status": "COMPLETED_PENDING_MANUAL_PRE_DRY_RUN_REVIEW",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW",
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        },
        "blocked_actions": ["TESTNET_DRY_RUN_ONLY", "TESTNET_SUBMIT", "REAL_SUBMIT", "SUBMIT_ORDER", "CANCEL_ORDER", "FLATTEN_POSITION"]
    }

    result = generate_review_packet(t430_report, "t430.json")

    assert result["ok"] is True
    assert result["task"] == "T431"
    assert result["phase"] == "MANUAL_PRE_DRY_RUN_REVIEW"
    assert result["review_packet_status"] == "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
    assert result["required_manual_decision"] == "APPROVE_OR_REJECT_TESTNET_DRY_RUN_PLANNING_REVIEW"
    assert result["final_decision"] == "READY_FOR_MANUAL_PRE_DRY_RUN_CHECKLIST"


def test_blocked_t430_generates_blocked_packet(tmp_path):
    t430_report = {
        "ok": False,
        "task": "T430",
        "phase": "PRE_DRY_RUN_READINESS_REVIEW",
        "phase_completion_status": "BLOCKED",
        "final_decision": "CONTINUE_PRE_DRY_RUN_READINESS_REVIEW",
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        }
    }

    result = generate_review_packet(t430_report, "t430.json")

    assert result["ok"] is False
    assert result["review_packet_status"] == "BLOCKED"
    assert result["final_decision"] == "CONTINUE_PRE_DRY_RUN_READINESS_REVIEW"


def test_safety_invariants(tmp_path):
    t430_report = {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_MANUAL_PRE_DRY_RUN_REVIEW",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
    }

    result = generate_review_packet(t430_report, "t430.json")

    sf = result["safety_flags"]
    assert sf["shadow_only"] is True
    assert sf["testnet_dry_run_allowed"] is False
    assert sf["testnet_submit_allowed"] is False
    assert sf["real_submit_allowed"] is False
    assert sf["submit_attempted"] is False
    assert sf["cancel_attempted"] is False
    assert sf["flatten_attempted"] is False


def test_blocked_actions_includes_required(tmp_path):
    t430_report = {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_MANUAL_PRE_DRY_RUN_REVIEW",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
    }

    result = generate_review_packet(t430_report, "t430.json")

    blocked = result["blocked_actions"]
    assert "TESTNET_DRY_RUN_ONLY" in blocked
    assert "TESTNET_SUBMIT" in blocked
    assert "REAL_SUBMIT" in blocked
    assert "SUBMIT_ORDER" in blocked
    assert "CANCEL_ORDER" in blocked
    assert "FLATTEN_POSITION" in blocked
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_checklist_items_complete(tmp_path):
    t430_report = {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_MANUAL_PRE_DRY_RUN_REVIEW",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
    }

    result = generate_review_packet(t430_report, "t430.json")

    checklist = result["checklist_items"]
    assert "REVIEW_T426_INPUT_PACKET" in checklist
    assert "REVIEW_T427_SAFETY_GATES" in checklist
    assert "REVIEW_T428_DATA_LINEAGE_LEDGER" in checklist
    assert "REVIEW_T429_READINESS_SCORE" in checklist
    assert "REVIEW_T430_PHASE_CONTROL" in checklist
    assert "CONFIRM_TESTNET_DRY_RUN_STILL_BLOCKED" in checklist
    assert "CONFIRM_NO_SUBMIT_CANCEL_FLATTEN" in checklist


def test_missing_t430_gives_blocked(tmp_path):
    result = generate_review_packet(None, "missing.json")

    assert result["ok"] is False
    assert result["review_packet_status"] == "BLOCKED"


def test_load_json_missing_file_returns_none(tmp_path):
    result = load_json(str(tmp_path / "nonexistent.json"))
    assert result is None


def test_load_json_invalid_json_returns_none(tmp_path):
    invalid_path = tmp_path / "invalid.json"
    with open(invalid_path, "w") as f:
        f.write("not valid json")
    result = load_json(str(invalid_path))
    assert result is None


def test_write_json_works(tmp_path):
    data = {"ok": True, "task": "T431"}
    out_path = tmp_path / "out.json"
    success = write_json(str(out_path), data)
    assert success is True
    with open(out_path, "r") as f:
        loaded = json.load(f)
    assert loaded["ok"] is True
    assert loaded["task"] == "T431"


def test_cli_smoke(tmp_path):
    t430_path = tmp_path / "t430.json"
    t430_report = {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_MANUAL_PRE_DRY_RUN_REVIEW",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
    }
    with open(t430_path, "w") as f:
        json.dump(t430_report, f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_manual_pre_dry_run_review_packet_v1.py"),
            "--phase-control-report", str(t430_path),
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task"] == "T431"


def test_cli_output_file(tmp_path):
    t430_path = tmp_path / "t430.json"
    out_path = tmp_path / "out.json"
    t430_report = {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_MANUAL_PRE_DRY_RUN_REVIEW",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW"
    }
    with open(t430_path, "w") as f:
        json.dump(t430_report, f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_manual_pre_dry_run_review_packet_v1.py"),
            "--phase-control-report", str(t430_path),
            "--output", str(out_path)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    proc.communicate()

    assert proc.returncode == 0
    assert out_path.exists()
    with open(out_path, "r") as f:
        result_json = json.load(f)
    assert result_json["task"] == "T431"
