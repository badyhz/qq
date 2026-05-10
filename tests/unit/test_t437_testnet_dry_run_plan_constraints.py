import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.verify_testnet_dry_run_plan_constraints_v1 import (
    verify_plan_constraints,
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


def valid_plan():
    return {
        "mode": "TESTNET_DRY_RUN_PLANNING_ONLY",
        "exchange_api_calls": False,
        "submit_order": False,
        "cancel_order": False,
        "flatten_position": False,
        "input_artifacts": ["t435.json", "t436.json"],
        "output_artifacts": ["t437.json", "t438.json"],
        "operator_review_required": True,
        "rollback_plan": "Revert to T435 state, no changes to core trading logic",
        "notes": "Planning only, no execution"
    }


def test_valid_plan_gives_pass(tmp_path):
    result = verify_plan_constraints(valid_t436(), valid_plan())

    assert result["ok"] is True
    assert result["task"] == "T437"
    assert result["constraint_status"] == "TESTNET_DRY_RUN_PLAN_CONSTRAINTS_VERIFIED"
    assert result["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_PLAN_RISK_REVIEW"
    assert len(result["violations"]) == 0


def test_invalid_mode_gives_violation(tmp_path):
    bad_plan = valid_plan()
    bad_plan["mode"] = "TESTNET_DRY_RUN_ONLY"

    result = verify_plan_constraints(valid_t436(), bad_plan)

    assert result["ok"] is False
    assert "INVALID_MODE" in result["violations"]


def test_exchange_api_calls_true_gives_violation(tmp_path):
    bad_plan = valid_plan()
    bad_plan["exchange_api_calls"] = True

    result = verify_plan_constraints(valid_t436(), bad_plan)

    assert result["ok"] is False
    assert "EXCHANGE_API_CALLS_NOT_ALLOWED" in result["violations"]


def test_submit_order_true_gives_violation(tmp_path):
    bad_plan = valid_plan()
    bad_plan["submit_order"] = True

    result = verify_plan_constraints(valid_t436(), bad_plan)

    assert result["ok"] is False
    assert "SUBMIT_ORDER_NOT_ALLOWED" in result["violations"]


def test_cancel_order_true_gives_violation(tmp_path):
    bad_plan = valid_plan()
    bad_plan["cancel_order"] = True

    result = verify_plan_constraints(valid_t436(), bad_plan)

    assert result["ok"] is False
    assert "CANCEL_ORDER_NOT_ALLOWED" in result["violations"]


def test_flatten_position_true_gives_violation(tmp_path):
    bad_plan = valid_plan()
    bad_plan["flatten_position"] = True

    result = verify_plan_constraints(valid_t436(), bad_plan)

    assert result["ok"] is False
    assert "FLATTEN_POSITION_NOT_ALLOWED" in result["violations"]


def test_missing_input_artifacts_gives_violation(tmp_path):
    bad_plan = valid_plan()
    bad_plan["input_artifacts"] = []

    result = verify_plan_constraints(valid_t436(), bad_plan)

    assert result["ok"] is False
    assert "INPUT_ARTIFACTS_MISSING" in result["violations"]


def test_missing_output_artifacts_gives_violation(tmp_path):
    bad_plan = valid_plan()
    bad_plan["output_artifacts"] = []

    result = verify_plan_constraints(valid_t436(), bad_plan)

    assert result["ok"] is False
    assert "OUTPUT_ARTIFACTS_MISSING" in result["violations"]


def test_operator_review_false_gives_violation(tmp_path):
    bad_plan = valid_plan()
    bad_plan["operator_review_required"] = False

    result = verify_plan_constraints(valid_t436(), bad_plan)

    assert result["ok"] is False
    assert "OPERATOR_REVIEW_NOT_REQUIRED" in result["violations"]


def test_rollback_missing_gives_violation(tmp_path):
    bad_plan = valid_plan()
    bad_plan["rollback_plan"] = ""

    result = verify_plan_constraints(valid_t436(), bad_plan)

    assert result["ok"] is False
    assert "ROLLBACK_PLAN_MISSING" in result["violations"]


def test_t436_blocked_gives_violation(tmp_path):
    bad_t436 = valid_t436()
    bad_t436["ok"] = False

    result = verify_plan_constraints(bad_t436, valid_plan())

    assert result["ok"] is False
    assert "PLANNING_PACKET_NOT_READY" in result["violations"]


def test_safety_invariants(tmp_path):
    result = verify_plan_constraints(valid_t436(), valid_plan())

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
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


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
    t436_path = tmp_path / "t436.json"
    plan_path = tmp_path / "plan.json"

    with open(t436_path, "w") as f:
        json.dump(valid_t436(), f)
    with open(plan_path, "w") as f:
        json.dump(valid_plan(), f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "verify_testnet_dry_run_plan_constraints_v1.py"),
            "--planning-packet", str(t436_path),
            "--dry-run-plan", str(plan_path),
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task"] == "T437"
