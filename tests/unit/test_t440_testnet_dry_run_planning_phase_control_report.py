import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_testnet_dry_run_planning_phase_control_report_v1 import (
    generate_phase_control_report,
    load_json,
    write_json
)


def valid_t436():
    return {
        "ok": True,
        "task": "T436",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_PLAN_CONSTRAINT_REVIEW",
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


def valid_t437():
    return {
        "ok": True,
        "task": "T437",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_PLAN_RISK_REVIEW",
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


def valid_t438():
    return {
        "ok": True,
        "task": "T438",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_PLANNING_APPROVAL_ARTIFACT",
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


def valid_t439():
    return {
        "ok": True,
        "task": "T439",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_PLANNING_FINAL_GATE",
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


def test_all_pass_gives_ready_for_readiness_review(tmp_path):
    result = generate_phase_control_report(
        valid_t436(),
        valid_t437(),
        valid_t438(),
        valid_t439()
    )

    assert result["ok"] is True
    assert result["task"] == "T440"
    assert result["phase"] == "TESTNET_DRY_RUN_PLANNING_REVIEW"
    assert result["phase_completion_status"] == "COMPLETED_PENDING_TESTNET_DRY_RUN_READINESS_REVIEW"
    assert result["next_phase"] == "TESTNET_DRY_RUN_READINESS_REVIEW"
    assert result["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_READINESS_REVIEW"
    assert result["component_statuses"]["T436"] == "PASS"
    assert result["component_statuses"]["T437"] == "PASS"
    assert result["component_statuses"]["T438"] == "PASS"
    assert result["component_statuses"]["T439"] == "PASS"
    assert result["component_statuses"]["EXECUTION_BLOCK"] == "PASS"
    assert len(result["blockers"]) == 0


def test_t436_fail_gives_blocker(tmp_path):
    bad_t436 = valid_t436()
    bad_t436["ok"] = False
    bad_t436["final_decision"] = "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"

    result = generate_phase_control_report(
        bad_t436,
        valid_t437(),
        valid_t438(),
        valid_t439()
    )

    assert result["ok"] is False
    assert "T436_PLANNING_PACKET_NOT_READY" in result["blockers"]


def test_t437_fail_gives_blocker(tmp_path):
    bad_t437 = valid_t437()
    bad_t437["ok"] = False
    bad_t437["final_decision"] = "BLOCK_TESTNET_DRY_RUN_PLANNING_REVIEW"

    result = generate_phase_control_report(
        valid_t436(),
        bad_t437,
        valid_t438(),
        valid_t439()
    )

    assert result["ok"] is False
    assert "T437_CONSTRAINTS_NOT_VERIFIED" in result["blockers"]


def test_t438_fail_gives_blocker(tmp_path):
    bad_t438 = valid_t438()
    bad_t438["ok"] = False
    bad_t438["final_decision"] = "CONTINUE_TESTNET_DRY_RUN_PLANNING_REVIEW"

    result = generate_phase_control_report(
        valid_t436(),
        valid_t437(),
        bad_t438,
        valid_t439()
    )

    assert result["ok"] is False
    assert "T438_RISK_REVIEW_NOT_PASSED" in result["blockers"]


def test_t439_fail_gives_blocker(tmp_path):
    bad_t439 = valid_t439()
    bad_t439["ok"] = False
    bad_t439["final_decision"] = "CONTINUE_TESTNET_DRY_RUN_PLANNING_REVIEW"

    result = generate_phase_control_report(
        valid_t436(),
        valid_t437(),
        valid_t438(),
        bad_t439
    )

    assert result["ok"] is False
    assert "T439_APPROVAL_ARTIFACT_NOT_READY" in result["blockers"]


def test_execution_block_violation_gives_blocker(tmp_path):
    bad_safety = valid_t436()
    bad_safety["safety_flags"]["testnet_dry_run_allowed"] = True

    result = generate_phase_control_report(
        bad_safety,
        valid_t437(),
        valid_t438(),
        valid_t439()
    )

    assert result["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in result["blockers"]


def test_allowed_actions_has_testnet_dry_run_only_gives_blocker(tmp_path):
    bad_allowed = valid_t436()
    bad_allowed["allowed_actions"] = ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY"]

    result = generate_phase_control_report(
        bad_allowed,
        valid_t437(),
        valid_t438(),
        valid_t439()
    )

    assert result["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in result["blockers"]


def test_blocked_actions_missing_flatten_gives_blocker(tmp_path):
    bad_blocked = valid_t436()
    bad_blocked["blocked_actions"] = ["TESTNET_DRY_RUN_ONLY", "TESTNET_SUBMIT", "REAL_SUBMIT", "SUBMIT_ORDER", "CANCEL_ORDER"]

    result = generate_phase_control_report(
        bad_blocked,
        valid_t437(),
        valid_t438(),
        valid_t439()
    )

    assert result["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in result["blockers"]


def test_testnet_dry_run_still_blocked_even_when_all_pass(tmp_path):
    result = generate_phase_control_report(
        valid_t436(),
        valid_t437(),
        valid_t438(),
        valid_t439()
    )

    sf = result["safety_flags"]
    assert sf["testnet_dry_run_allowed"] is False
    assert "TESTNET_DRY_RUN_ONLY" in result["blocked_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_safety_invariants(tmp_path):
    result = generate_phase_control_report(
        valid_t436(),
        valid_t437(),
        valid_t438(),
        valid_t439()
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
        "t436": tmp_path / "t436.json",
        "t437": tmp_path / "t437.json",
        "t438": tmp_path / "t438.json",
        "t439": tmp_path / "t439.json"
    }

    with open(paths["t436"], "w") as f:
        json.dump(valid_t436(), f)
    with open(paths["t437"], "w") as f:
        json.dump(valid_t437(), f)
    with open(paths["t438"], "w") as f:
        json.dump(valid_t438(), f)
    with open(paths["t439"], "w") as f:
        json.dump(valid_t439(), f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_planning_phase_control_report_v1.py"),
            "--planning-packet", str(paths["t436"]),
            "--constraint-report", str(paths["t437"]),
            "--risk-review-report", str(paths["t438"]),
            "--approval-artifact", str(paths["t439"]),
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task"] == "T440"
