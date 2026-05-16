import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_final_session_health_score_v1 import generate_health_score


def evidence(verdict="PASS"):
    return {"verdict": verdict, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def phase(verdict="PASS"):
    return {"verdict": verdict, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def incident(level="NONE"):
    return {"verdict": "PASS" if level == "NONE" else "FAIL", "incident_level": level, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def audit(verdict="PASS"):
    return {"verdict": verdict, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def test_healthy_pass():
    r = generate_health_score(evidence("PASS"), phase("PASS"), incident("NONE"), phase("PASS"), audit("PASS"))
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["decision"] == "HEALTHY_SESSION_CLOSED"
    assert r["health_score"] == 100


def test_low_monitor_partial():
    r = generate_health_score(evidence("PASS"), phase("PASS"), incident("LOW"), phase("PASS"), audit("PASS"))
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW_REQUIRED"
    assert r["health_score"] == 85


def test_medium_review_partial():
    r = generate_health_score(evidence("PASS"), phase("PASS"), incident("MEDIUM"), phase("PASS"), audit("PASS"))
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW_REQUIRED"
    assert r["health_score"] == 70


def test_high_fail_rollback():
    r = generate_health_score(evidence("PASS"), phase("PASS"), incident("HIGH"), phase("PASS"), audit("PASS"))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "ROLLBACK_REVIEW_REQUIRED"
    assert r["health_score"] == 40


def test_critical_fail_rollback():
    r = generate_health_score(evidence("PASS"), phase("PASS"), incident("CRITICAL"), phase("PASS"), audit("PASS"))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "ROLLBACK_REVIEW_REQUIRED"
    assert r["health_score"] == 0


def test_audit_fail():
    r = generate_health_score(evidence("PASS"), phase("PASS"), incident("NONE"), phase("PASS"), audit("FAIL"))
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"
    assert r["health_score"] == 50


def test_evidence_partial():
    r = generate_health_score(evidence("PARTIAL"), phase("PASS"), incident("NONE"), phase("PASS"), audit("PASS"))
    assert r["ok"] is False
    assert r["verdict"] == "PARTIAL"
    assert r["health_score"] == 80


def test_actions_always_false():
    r = generate_health_score(evidence("PASS"), phase("PASS"), incident("NONE"), phase("PASS"), audit("PASS"))
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
