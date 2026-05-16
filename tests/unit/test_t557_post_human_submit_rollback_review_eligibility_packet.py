import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_rollback_review_eligibility_packet_v1 import generate_rollback_eligibility


def incident(level="NONE"):
    return {"verdict": "PASS" if level == "NONE" else "FAIL", "incident_level": level, "incident_types": [], "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def phase():
    return {"verdict": "PASS", "decision": "VERIFIED_ONE_SHOT_TESTNET_SUBMIT", "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False, "max_submit_count": 0}


def test_none_pass():
    r = generate_rollback_eligibility(incident("NONE"), phase())
    assert r["verdict"] == "PASS"
    assert r["eligible_for_rollback_review"] is False
    assert r["required_action"] == "NONE"
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False


def test_medium_partial():
    r = generate_rollback_eligibility(incident("MEDIUM"), phase())
    assert r["verdict"] == "PARTIAL"
    assert r["eligible_for_rollback_review"] is True
    assert r["required_action"] == "REVIEW"


def test_high_fail_eligible():
    r = generate_rollback_eligibility(incident("HIGH"), phase())
    assert r["verdict"] == "FAIL"
    assert r["eligible_for_rollback_review"] is True
    assert r["required_action"] == "HUMAN_ROLLBACK_DECISION_REQUIRED"


def test_critical_fail_eligible():
    r = generate_rollback_eligibility(incident("CRITICAL"), phase())
    assert r["verdict"] == "FAIL"
    assert r["eligible_for_rollback_review"] is True
    assert r["required_action"] == "HUMAN_ROLLBACK_DECISION_REQUIRED"


def test_actions_never_allowed():
    r = generate_rollback_eligibility(incident("CRITICAL"), phase())
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
