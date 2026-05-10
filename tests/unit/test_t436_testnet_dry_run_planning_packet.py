import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_testnet_dry_run_planning_packet_v1 import (
    generate_planning_packet,
    load_json,
    write_json,
    REQUIRED_PLAN_ITEMS
)


def test_ready_t435_gives_ready_for_constraint_review(tmp_path):
    t435_report = {
        "ok": True,
        "task": "T435",
        "phase": "MANUAL_PRE_DRY_RUN_REVIEW",
        "phase_completion_status": "COMPLETED_PENDING_TESTNET_DRY_RUN_PLANNING_REVIEW",
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
        "blocked_actions": ["TESTNET_DRY_RUN_ONLY", "TESTNET_SUBMIT", "REAL_SUBMIT", "SUBMIT_ORDER", "CANCEL_ORDER", "FLATTEN_POSITION"]
    }

    result = generate_planning_packet(t435_report, "t435.json")

    assert result["ok"] is True
    assert result["task"] == "T436"
    assert result["phase"] == "TESTNET_DRY_RUN_PLANNING_REVIEW"
    assert result["planning_packet_status"] == "READY_FOR_TESTNET_DRY_RUN_PLAN_CONSTRAINT_REVIEW"
    assert result["planning_scope"] == "PLAN_TESTNET_DRY_RUN_ONLY_BUT_DO_NOT_ENABLE"
    assert result["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_PLAN_CONSTRAINT_REVIEW"


def test_blocked_t435_gives_blocked(tmp_path):
    t435_report = {
        "ok": False,
        "task": "T435",
        "phase_completion_status": "BLOCKED",
        "final_decision": "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"
    }

    result = generate_planning_packet(t435_report, "t435.json")

    assert result["ok"] is False
    assert result["planning_packet_status"] == "BLOCKED"
    assert result["final_decision"] == "CONTINUE_MANUAL_PRE_DRY_RUN_REVIEW"


def test_required_plan_items_present(tmp_path):
    t435_report = {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_TESTNET_DRY_RUN_PLANNING_REVIEW",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"
    }

    result = generate_planning_packet(t435_report, "t435.json")

    items = result["required_plan_items"]
    for required in REQUIRED_PLAN_ITEMS:
        assert required in items


def test_safety_invariants(tmp_path):
    t435_report = {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_TESTNET_DRY_RUN_PLANNING_REVIEW",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"
    }

    result = generate_planning_packet(t435_report, "t435.json")

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


def test_missing_t435_gives_blocked(tmp_path):
    result = generate_planning_packet(None, "missing.json")

    assert result["ok"] is False
    assert result["planning_packet_status"] == "BLOCKED"


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
    t435_path = tmp_path / "t435.json"
    t435_report = {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_TESTNET_DRY_RUN_PLANNING_REVIEW",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"
    }
    with open(t435_path, "w") as f:
        json.dump(t435_report, f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_planning_packet_v1.py"),
            "--manual-pre-dry-run-phase-report", str(t435_path),
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task"] == "T436"


def test_cli_output_file(tmp_path):
    t435_path = tmp_path / "t435.json"
    out_path = tmp_path / "out.json"
    t435_report = {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_TESTNET_DRY_RUN_PLANNING_REVIEW",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_PLANNING_REVIEW"
    }
    with open(t435_path, "w") as f:
        json.dump(t435_report, f)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_planning_packet_v1.py"),
            "--manual-pre-dry-run-phase-report", str(t435_path),
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
    assert result_json["task"] == "T436"
