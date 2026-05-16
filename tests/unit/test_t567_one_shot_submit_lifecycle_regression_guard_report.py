import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_one_shot_submit_lifecycle_regression_guard_report_v1 import generate_regression_guard_report


def replay(verdict="PASS", include_readonly_phase=True):
    artifacts = []
    if include_readonly_phase:
        artifacts.append({"phase_family": "POST_HUMAN_SUBMIT_READONLY_VERIFICATION", "max_submit_count": 0})
    return {
        "verdict": verdict,
        "artifacts": artifacts,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def final_phase(verdict="PASS", decision="CLOSED", submit_allowed=False):
    return {
        "verdict": verdict,
        "decision": decision,
        "max_submit_count": 0,
        "submit_allowed": submit_allowed,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def audit(verdict="PASS"):
    return {
        "verdict": verdict,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def incident(level="NONE", rollback_required=False):
    return {
        "incident_level": level,
        "rollback_required": rollback_required,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def test_no_regression_pass():
    r = generate_regression_guard_report(replay(), final_phase(), audit(), incident("NONE"))
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["regression_status"] == "NO_REGRESSION"


def test_high_incident_closed_fail():
    r = generate_regression_guard_report(replay(), final_phase(decision="CLOSED"), audit(), incident("HIGH"))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["regression_status"] == "UNSAFE_REGRESSION"


def test_action_allowed_fail():
    r = generate_regression_guard_report(replay(), final_phase(submit_allowed=True), audit(), incident("NONE"))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["regression_status"] == "UNSAFE_REGRESSION"


def test_audit_fail_fail():
    r = generate_regression_guard_report(replay(), final_phase(decision="CLOSED"), audit("FAIL"), incident("NONE"))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["regression_status"] == "UNSAFE_REGRESSION"


def test_warning_drift_partial():
    r = generate_regression_guard_report(replay(include_readonly_phase=False), final_phase(), audit(), incident("NONE"))
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["regression_status"] == "WARNING_DRIFT"
