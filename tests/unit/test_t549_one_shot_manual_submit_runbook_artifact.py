import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_one_shot_manual_submit_runbook_artifact_v1 import generate_runbook


def checklist(v="PASS", status="READY_FOR_HUMAN_DECISION"):
    return {"verdict": v, "checklist_status": status, "submit_allowed": False}


def artifact(v="PASS"):
    return {
        "verdict": v,
        "submit_allowed": False,
        "dry_run_command": "python3 dry-run",
        "human_execution_command_template": "python3 submit --allow-testnet-submit --confirm-token TOKEN --env testnet",
    }


def token(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def test_pass():
    r = generate_runbook(checklist("PASS"), artifact("PASS"), token("PASS"))
    assert r["verdict"] == "PASS"
    assert r["runbook_type"] == "ONE_SHOT_MANUAL_TESTNET_SUBMIT_RUNBOOK"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1


def test_checklist_partial_partial():
    r = generate_runbook(checklist("PARTIAL", "NEEDS_REVIEW"), artifact("PASS"), token("PASS"))
    assert r["verdict"] == "FAIL"


def test_checklist_fail_fail():
    r = generate_runbook(checklist("FAIL", "BLOCKED"), artifact("PASS"), token("PASS"))
    assert r["verdict"] == "FAIL"


def test_token_gate_present():
    r = generate_runbook(checklist("PASS"), artifact("PASS"), token("PASS"))
    flags = r["manual_submit_step"]["required_flags"]
    assert "--allow-testnet-submit" in flags
    assert "--confirm-token" in flags
    assert "--env testnet" in flags


def test_abort_conditions_present():
    r = generate_runbook(checklist("PASS"), artifact("PASS"), token("PASS"))
    cond = r["abort_conditions"]
    assert "ENV_NOT_TESTNET" in cond
    assert "TOKEN_MISMATCH" in cond
    assert "COMMAND_MISMATCH" in cond
    assert "MAINNET_OR_LIVE_MARKER" in cond
    assert "REPEATED_SUBMIT_ATTEMPT" in cond
    assert "MISSING_SL_TP_PLAN" in cond
    assert "DRY_RUN_VERIFICATION_NOT_PASS" in cond
