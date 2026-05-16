import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_final_closeout_gate_v1 import generate_closeout_gate


def health_score(verdict="PASS", decision="HEALTHY_SESSION_CLOSED"):
    return {"verdict": verdict, "decision": decision, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def operator(verdict="PASS", status="CLOSED_HEALTHY"):
    return {"verdict": verdict, "session_status": status, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def audit(verdict="PASS"):
    return {"verdict": verdict, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def test_closed():
    r = generate_closeout_gate(health_score(), operator(), audit())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["closeout_status"] == "CLOSED"
    assert r["next_allowed_phase"] == "NONE"


def test_monitor():
    r = generate_closeout_gate(health_score("PARTIAL", "MONITOR"), operator("PARTIAL", "MONITOR"), audit())
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["closeout_status"] == "MONITOR"
    assert r["next_allowed_phase"] == "MONITORING_REVIEW"


def test_review():
    r = generate_closeout_gate(health_score("PARTIAL", "REVIEW_REQUIRED"), operator("PARTIAL", "REVIEW_REQUIRED"), audit())
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["closeout_status"] == "REVIEW"
    assert r["next_allowed_phase"] == "HUMAN_REVIEW"


def test_rollback_review():
    r = generate_closeout_gate(health_score("FAIL", "ROLLBACK_REVIEW_REQUIRED"), operator("FAIL", "ROLLBACK_REVIEW_REQUIRED"), audit())
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["closeout_status"] == "ROLLBACK_REVIEW"
    assert r["next_allowed_phase"] == "HUMAN_ROLLBACK_REVIEW"


def test_actions_always_false():
    r = generate_closeout_gate(health_score(), operator(), audit())
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
    assert r["max_submit_count"] == 0
