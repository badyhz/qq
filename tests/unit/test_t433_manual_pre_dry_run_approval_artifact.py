import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_manual_pre_dry_run_approval_artifact_v1 import (
    generate_approval_artifact,
    load_json,
    write_json
)


def test_approved_t432_generates_approval_artifact(tmp_path):
    t432_report = {
        "ok": True,
        "task": "T432",
        "phase": "MANUAL_PRE_DRY_RUN_REVIEW",
        "checklist_status": "MANUAL_PRE_DRY_RUN_CHECKLIST_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT",
        "reviewer": "test_operator"
    }

    result = generate_approval_artifact(t432_report)

    assert result["ok"] is True
    assert result["task"] == "T433"
    assert result["approval_status"] == "MANUAL_PRE_DRY_RUN_APPROVED"
    assert result["approval_scope"] == "APPROVE_TESTNET_DRY_RUN_PLANNING_REVIEW_ONLY"
    assert result["final_decision"] == "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE"


def test_approval_scope_is_planning_only(tmp_path):
    t432_report = {
        "ok": True,
        "task": "T432",
        "checklist_status": "MANUAL_PRE_DRY_RUN_CHECKLIST_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT"
    }

    result = generate_approval_artifact(t432_report)

    assert result["approval_scope"] == "APPROVE_TESTNET_DRY_RUN_PLANNING_REVIEW_ONLY"
    assert "TESTNET_DRY_RUN_ONLY still blocked" in result["approval_limitations"]


def test_testnet_dry_run_still_blocked(tmp_path):
    t432_report = {
        "ok": True,
        "task": "T432",
        "checklist_status": "MANUAL_PRE_DRY_RUN_CHECKLIST_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT"
    }

    result = generate_approval_artifact(t432_report)

    sf = result["safety_flags"]
    assert sf["testnet_dry_run_allowed"] is False
    assert "TESTNET_DRY_RUN_ONLY" in result["blocked_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_rejected_t432_gives_blocked(tmp_path):
    t432_report = {
        "ok": False,
        "task": "T432",
        "checklist_status": "MANUAL_PRE_DRY_RUN_CHECKLIST_REJECTED_OR_INCOMPLETE",
        "final_decision": "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"
    }

    result = generate_approval_artifact(t432_report)

    assert result["ok"] is False
    assert result["approval_status"] == "BLOCKED"
    assert result["final_decision"] == "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"


def test_missing_t432_gives_blocked(tmp_path):
    result = generate_approval_artifact(None)

    assert result["ok"] is False
    assert result["approval_status"] == "BLOCKED"


def test_safety_invariants(tmp_path):
    t432_report = {
        "ok": True,
        "checklist_status": "MANUAL_PRE_DRY_RUN_CHECKLIST_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT"
    }

    result = generate_approval_artifact(t432_report)

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
    t432_path = tmp_path / "t432.json"
    t432_report = {
        "ok": True,
        "task": "T432",
        "checklist_status": "MANUAL_PRE_DRY_RUN_CHECKLIST_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT"
    }

    with open(t432_path, "w") as f:
        json.dump(t432_report, f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_manual_pre_dry_run_approval_artifact_v1.py"),
            "--checklist-interpretation", str(t432_path),
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task"] == "T433"


def test_cli_output_file(tmp_path):
    t432_path = tmp_path / "t432.json"
    out_path = tmp_path / "out.json"
    t432_report = {
        "ok": True,
        "task": "T432",
        "checklist_status": "MANUAL_PRE_DRY_RUN_CHECKLIST_APPROVED",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT"
    }

    with open(t432_path, "w") as f:
        json.dump(t432_report, f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_manual_pre_dry_run_approval_artifact_v1.py"),
            "--checklist-interpretation", str(t432_path),
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
    assert result_json["task"] == "T433"
