import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_testnet_dry_run_plan_risk_review_v1 import (
    generate_risk_review,
    load_json,
    write_json,
    RISK_ITEMS,
    REQUIRED_CONTROLS
)


def valid_t437():
    return {
        "ok": True,
        "task": "T437",
        "constraint_status": "TESTNET_DRY_RUN_PLAN_CONSTRAINTS_VERIFIED",
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


def test_valid_t437_gives_pass(tmp_path):
    result = generate_risk_review(valid_t437())

    assert result["ok"] is True
    assert result["task"] == "T438"
    assert result["risk_review_status"] == "TESTNET_DRY_RUN_PLAN_RISK_REVIEW_PASSED"
    assert result["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_PLANNING_APPROVAL_ARTIFACT"


def test_blocked_t437_gives_blocked(tmp_path):
    bad_t437 = valid_t437()
    bad_t437["ok"] = False
    bad_t437["final_decision"] = "BLOCK_TESTNET_DRY_RUN_PLANNING_REVIEW"

    result = generate_risk_review(bad_t437)

    assert result["ok"] is False
    assert result["risk_review_status"] == "BLOCKED"
    assert result["final_decision"] == "CONTINUE_TESTNET_DRY_RUN_PLANNING_REVIEW"


def test_risk_items_present(tmp_path):
    result = generate_risk_review(valid_t437())

    items = result["risk_items"]
    for required in RISK_ITEMS:
        assert required in items


def test_required_controls_present(tmp_path):
    result = generate_risk_review(valid_t437())

    controls = result["required_controls"]
    for required in REQUIRED_CONTROLS:
        assert required in controls


def test_testnet_dry_run_still_blocked(tmp_path):
    result = generate_risk_review(valid_t437())

    sf = result["safety_flags"]
    assert sf["testnet_dry_run_allowed"] is False
    assert "TESTNET_DRY_RUN_ONLY" in result["blocked_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]


def test_safety_invariants(tmp_path):
    result = generate_risk_review(valid_t437())

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


def test_missing_t437_gives_blocked(tmp_path):
    result = generate_risk_review(None)

    assert result["ok"] is False
    assert result["risk_review_status"] == "BLOCKED"


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
    t437_path = tmp_path / "t437.json"

    with open(t437_path, "w") as f:
        json.dump(valid_t437(), f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_plan_risk_review_v1.py"),
            "--constraint-report", str(t437_path),
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task"] == "T438"


def test_cli_output_file(tmp_path):
    t437_path = tmp_path / "t437.json"
    out_path = tmp_path / "out.json"

    with open(t437_path, "w") as f:
        json.dump(valid_t437(), f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_plan_risk_review_v1.py"),
            "--constraint-report", str(t437_path),
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
    assert result_json["task"] == "T438"
