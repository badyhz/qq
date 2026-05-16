import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_one_shot_submit_lifecycle_safety_dashboard_v1 import generate_safety_dashboard


def replay(verdict="PASS"):
    return {
        "verdict": verdict,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def guard(verdict="PASS", status="NO_REGRESSION"):
    return {
        "verdict": verdict,
        "regression_status": status,
        "checked_guards": [
            {
                "name": "audit_manifest_pass_required_for_healthy_close",
                "passed": True,
                "severity": "unsafe",
                "detail": "ok",
            }
        ],
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def final_phase(verdict="PASS", decision="CLOSED"):
    return {
        "verdict": verdict,
        "decision": decision,
        "max_submit_count": 0,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def health(score=100, level="NONE"):
    return {
        "health_score": score,
        "incident_level": level,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def operator(status="CLOSED_HEALTHY"):
    return {
        "session_status": status,
        "submit_allowed": False,
        "cancel_allowed": False,
        "flatten_allowed": False,
    }


def test_closed_healthy():
    r = generate_safety_dashboard(replay(), guard(), final_phase(), health(), operator())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["lifecycle_status"] == "CLOSED_HEALTHY"


def test_monitor():
    r = generate_safety_dashboard(
        replay(),
        guard("PARTIAL", "WARNING_DRIFT"),
        final_phase("PARTIAL", "MONITOR"),
        health(80, "LOW"),
        operator("MONITOR"),
    )
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["lifecycle_status"] == "MONITOR"


def test_review():
    r = generate_safety_dashboard(
        replay(),
        guard("PARTIAL", "WARNING_DRIFT"),
        final_phase("PARTIAL", "REVIEW"),
        health(75, "LOW"),
        operator("REVIEW_REQUIRED"),
    )
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["lifecycle_status"] == "REVIEW"


def test_rollback():
    r = generate_safety_dashboard(
        replay(),
        guard("FAIL", "UNSAFE_REGRESSION"),
        final_phase("FAIL", "REQUIRE_HUMAN_ROLLBACK_REVIEW"),
        health(20, "CRITICAL"),
        operator("ROLLBACK_REVIEW_REQUIRED"),
    )
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["lifecycle_status"] == "ROLLBACK_REVIEW"


def test_actions_always_false():
    r = generate_safety_dashboard(replay(), guard(), final_phase(), health(), operator())
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
