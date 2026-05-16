import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_final_phase_control_report_v1 import generate_final_phase_report


def audit(verdict="PASS"):
    return {"verdict": verdict, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def health_score(verdict="PASS", decision="HEALTHY_SESSION_CLOSED"):
    return {"verdict": verdict, "decision": decision, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def operator(verdict="PASS"):
    return {"verdict": verdict, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def closeout(verdict="PASS", status="CLOSED"):
    return {"verdict": verdict, "closeout_status": status, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False, "max_submit_count": 0}


def test_closed():
    r = generate_final_phase_report(audit(), health_score(), operator(), closeout())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["decision"] == "CLOSED"
    assert r["can_continue"] is False


def test_monitor():
    r = generate_final_phase_report(audit(), health_score("PARTIAL", "MONITOR"), operator("PARTIAL"), closeout("PARTIAL", "MONITOR"))
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "MONITOR"


def test_review():
    r = generate_final_phase_report(audit(), health_score("PARTIAL", "REVIEW_REQUIRED"), operator("PARTIAL"), closeout("PARTIAL", "REVIEW"))
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_rollback_review():
    r = generate_final_phase_report(audit(), health_score("FAIL", "ROLLBACK_REVIEW_REQUIRED"), operator("FAIL"), closeout("FAIL", "ROLLBACK_REVIEW"))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "REQUIRE_HUMAN_ROLLBACK_REVIEW"


def test_stop():
    r = generate_final_phase_report(audit("FAIL"), health_score("FAIL"), operator("FAIL"), closeout("FAIL", "BLOCKED"))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_actions_always_false():
    r = generate_final_phase_report(audit(), health_score(), operator(), closeout())
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
    assert r["max_submit_count"] == 0
    assert r["readonly"] is True
