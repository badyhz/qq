import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_manual_pre_dry_run_final_gate_report_v1 import (
    generate_final_gate_report,
    load_json,
    write_json
)


def test_approved_artifact_gives_ready_for_planning(tmp_path):
    t433_report = {
        "ok": True,
        "task": "T433",
        "phase": "MANUAL_PRE_DRY_RUN_REVIEW",
        "approval_status": "MANUAL_PRE_DRY_RUN_APPROVED",
        "approval_scope": "APPROVE_TESTNET_DRY_RUN_PLANNING_REVIEW_ONLY",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE"
    }

    result = generate_final_gate_report(t433_report)

    assert result["ok"] is True
    assert result["task"] == "T434"
    assert result["final_gate_status"] == "MANUAL_PRE_DRY_RUN_FINAL_GATE_PASSED"
    assert result["gate_result"] == "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"
    assert result["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"


def test_blocked_artifact_gives_blocked(tmp_path):
    t433_report = {
        "ok": False,
        "task": "T433",
        "approval_status": "BLOCKED",
        "final_decision": "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"
    }

    result = generate_final_gate_report(t433_report)

    assert result["ok"] is False
    assert result["final_gate_status"] == "BLOCKED"
    assert result["final_decision"] == "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"


def test_never_allows_testnet_dry_run_only(tmp_path):
    t433_report = {
        "ok": True,
        "approval_status": "MANUAL_PRE_DRY_RUN_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE"
    }

    result = generate_final_gate_report(t433_report)

    sf = result["safety_flags"]
    assert sf["testnet_dry_run_allowed"] is False
    assert "TESTNET_DRY_RUN_ONLY" in result["blocked_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_not_ready_for_testnet_dry_run_only(tmp_path):
    t433_report = {
        "ok": True,
        "approval_status": "MANUAL_PRE_DRY_RUN_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE"
    }

    result = generate_final_gate_report(t433_report)

    # Important: should be planning review, not dry run only
    assert result["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"
    assert result["final_decision"] != "READY_FOR_TESTNET_DRY_RUN_ONLY"


def test_safety_invariants(tmp_path):
    t433_report = {
        "ok": True,
        "approval_status": "MANUAL_PRE_DRY_RUN_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE"
    }

    result = generate_final_gate_report(t433_report)

    sf = result["safety_flags"]
    assert sf["shadow_only"] is True
    assert sf["testnet_dry_run_allowed"] is False
    assert sf["testnet_submit_allowed"] is False
    assert sf["real_submit_allowed"] is False
    assert sf["submit_attempted"] is False
    assert sf["cancel_attempted"] is False
    assert sf["flatten_attempted"] is False

    blocked = result["blocked_actions"]
    assert "TESTNET_DRY_RUN_ONLY" in blocked
    assert "TESTNET_SUBMIT" in blocked
    assert "REAL_SUBMIT" in blocked
    assert "SUBMIT_ORDER" in blocked
    assert "CANCEL_ORDER" in blocked
    assert "FLATTEN_POSITION" in blocked


def test_missing_artifact_gives_blocked(tmp_path):
    result = generate_final_gate_report(None)

    assert result["ok"] is False
    assert result["final_gate_status"] == "BLOCKED"


def test_load_json_functions(tmp_path):
    assert load_json(str(tmp_path / "nonexistent.json")) is None

    invalid_path = tmp_path / "invalid.json"
    with open(invalid_path, "w") as f:
        f.write("not json")
    assert load_json(str(invalid_path)) is None

    data = {"ok": True}
    out_path = tmp_path / "out.json"
    assert write_json(str(out_path), data) is True
    loaded = load_json(str(out_path))
    assert loaded["ok"] is True


def test_cli_smoke(tmp_path):
    t433_path = tmp_path / "t433.json"
    t433_report = {
        "ok": True,
        "task": "T433",
        "approval_status": "MANUAL_PRE_DRY_RUN_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE"
    }

    with open(t433_path, "w") as f:
        json.dump(t433_report, f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_manual_pre_dry_run_final_gate_report_v1.py"),
            "--approval-artifact", str(t433_path),
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task"] == "T434"


def test_cli_output_file(tmp_path):
    t433_path = tmp_path / "t433.json"
    out_path = tmp_path / "out.json"
    t433_report = {
        "ok": True,
        "task": "T433",
        "approval_status": "MANUAL_PRE_DRY_RUN_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE"
    }

    with open(t433_path, "w") as f:
        json.dump(t433_report, f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_manual_pre_dry_run_final_gate_report_v1.py"),
            "--approval-artifact", str(t433_path),
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
    assert result_json["task"] == "T434"
