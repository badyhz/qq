import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_manual_pre_dry_run_phase_control_report_v1 import (
    generate_phase_control_report,
    load_json,
    write_json
)


def valid_t431():
    return {
        "ok": True,
        "task": "T431",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_CHECKLIST",
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        },
        "allowed_actions": ["READ_REPORTS"],
        "blocked_actions": ["TESTNET_DRY_RUN_ONLY", "TESTNET_SUBMIT", "REAL_SUBMIT", "SUBMIT_ORDER", "CANCEL_ORDER", "FLATTEN_POSITION"]
    }


def valid_t432():
    return {
        "ok": True,
        "task": "T432",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_APPROVAL_ARTIFACT",
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        },
        "allowed_actions": ["READ_REPORTS"],
        "blocked_actions": ["TESTNET_DRY_RUN_ONLY", "TESTNET_SUBMIT", "REAL_SUBMIT", "SUBMIT_ORDER", "CANCEL_ORDER", "FLATTEN_POSITION"]
    }


def valid_t433():
    return {
        "ok": True,
        "task": "T433",
        "final_decision": "READY_FOR_MANUAL_PRE_DRY_RUN_FINAL_GATE",
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        },
        "allowed_actions": ["READ_REPORTS"],
        "blocked_actions": ["TESTNET_DRY_RUN_ONLY", "TESTNET_SUBMIT", "REAL_SUBMIT", "SUBMIT_ORDER", "CANCEL_ORDER", "FLATTEN_POSITION"]
    }


def valid_t434():
    return {
        "ok": True,
        "task": "T434",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW",
        "safety_flags": {
            "shadow_only": True,
            "testnet_dry_run_allowed": False,
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False
        },
        "allowed_actions": ["READ_REPORTS"],
        "blocked_actions": ["TESTNET_DRY_RUN_ONLY", "TESTNET_SUBMIT", "REAL_SUBMIT", "SUBMIT_ORDER", "CANCEL_ORDER", "FLATTEN_POSITION"]
    }


def test_all_pass_gives_ready_for_planning(tmp_path):
    result = generate_phase_control_report(
        valid_t431(),
        valid_t432(),
        valid_t433(),
        valid_t434()
    )

    assert result["ok"] is True
    assert result["task"] == "T435"
    assert result["phase"] == "MANUAL_PRE_DRY_RUN_REVIEW"
    assert result["phase_completion_status"] == "COMPLETED_PENDING_TESTNET_DRY_RUN_PLANNING_REVIEW"
    assert result["next_phase"] == "TESTNET_DRY_RUN_PLANNING_REVIEW"
    assert result["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"
    assert result["component_statuses"]["T431"] == "PASS"
    assert result["component_statuses"]["T432"] == "PASS"
    assert result["component_statuses"]["T433"] == "PASS"
    assert result["component_statuses"]["T434"] == "PASS"
    assert result["component_statuses"]["EXECUTION_BLOCK"] == "PASS"
    assert len(result["blockers"]) == 0


def test_t431_fail_gives_blocker(tmp_path):
    bad_t431 = valid_t431()
    bad_t431["ok"] = False
    bad_t431["final_decision"] = "CONTINUE_PRE_DRY_RUN_READINESS_REVIEW"

    result = generate_phase_control_report(
        bad_t431,
        valid_t432(),
        valid_t433(),
        valid_t434()
    )

    assert result["ok"] is False
    assert result["phase_completion_status"] == "BLOCKED"
    assert "T431_REVIEW_PACKET_NOT_READY" in result["blockers"]


def test_t432_fail_gives_blocker(tmp_path):
    bad_t432 = valid_t432()
    bad_t432["ok"] = False
    bad_t432["final_decision"] = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"

    result = generate_phase_control_report(
        valid_t431(),
        bad_t432,
        valid_t433(),
        valid_t434()
    )

    assert result["ok"] is False
    assert "T432_CHECKLIST_NOT_APPROVED" in result["blockers"]


def test_t433_fail_gives_blocker(tmp_path):
    bad_t433 = valid_t433()
    bad_t433["ok"] = False
    bad_t433["final_decision"] = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"

    result = generate_phase_control_report(
        valid_t431(),
        valid_t432(),
        bad_t433,
        valid_t434()
    )

    assert result["ok"] is False
    assert "T433_APPROVAL_ARTIFACT_NOT_READY" in result["blockers"]


def test_t434_fail_gives_blocker(tmp_path):
    bad_t434 = valid_t434()
    bad_t434["ok"] = False
    bad_t434["final_decision"] = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"

    result = generate_phase_control_report(
        valid_t431(),
        valid_t432(),
        valid_t433(),
        bad_t434
    )

    assert result["ok"] is False
    assert "T434_FINAL_GATE_NOT_PASSED" in result["blockers"]


def test_execution_block_violation_gives_blocker(tmp_path):
    bad_safety = valid_t431()
    bad_safety["safety_flags"]["testnet_dry_run_allowed"] = True

    result = generate_phase_control_report(
        bad_safety,
        valid_t432(),
        valid_t433(),
        valid_t434()
    )

    assert result["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in result["blockers"]


def test_allowed_actions_has_testnet_dry_run_only_gives_blocker(tmp_path):
    bad_allowed = valid_t431()
    bad_allowed["allowed_actions"] = ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY"]

    result = generate_phase_control_report(
        bad_allowed,
        valid_t432(),
        valid_t433(),
        valid_t434()
    )

    assert result["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in result["blockers"]


def test_blocked_actions_missing_flatten_gives_blocker(tmp_path):
    bad_blocked = valid_t431()
    bad_blocked["blocked_actions"] = ["TESTNET_DRY_RUN_ONLY", "TESTNET_SUBMIT", "REAL_SUBMIT", "SUBMIT_ORDER", "CANCEL_ORDER"]
    # Missing FLATTEN_POSITION

    result = generate_phase_control_report(
        bad_blocked,
        valid_t432(),
        valid_t433(),
        valid_t434()
    )

    assert result["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in result["blockers"]


def test_testnet_dry_run_still_blocked_even_when_all_pass(tmp_path):
    result = generate_phase_control_report(
        valid_t431(),
        valid_t432(),
        valid_t433(),
        valid_t434()
    )

    sf = result["safety_flags"]
    assert sf["testnet_dry_run_allowed"] is False
    assert "TESTNET_DRY_RUN_ONLY" in result["blocked_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_safety_invariants(tmp_path):
    result = generate_phase_control_report(
        valid_t431(),
        valid_t432(),
        valid_t433(),
        valid_t434()
    )

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
    paths = {
        "t431": tmp_path / "t431.json",
        "t432": tmp_path / "t432.json",
        "t433": tmp_path / "t433.json",
        "t434": tmp_path / "t434.json"
    }

    with open(paths["t431"], "w") as f:
        json.dump(valid_t431(), f)
    with open(paths["t432"], "w") as f:
        json.dump(valid_t432(), f)
    with open(paths["t433"], "w") as f:
        json.dump(valid_t433(), f)
    with open(paths["t434"], "w") as f:
        json.dump(valid_t434(), f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_manual_pre_dry_run_phase_control_report_v1.py"),
            "--review-packet", str(paths["t431"]),
            "--checklist-interpretation", str(paths["t432"]),
            "--approval-artifact", str(paths["t433"]),
            "--final-gate-report", str(paths["t434"]),
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task"] == "T435"
