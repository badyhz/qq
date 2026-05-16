import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_incident_review_phase_control_report_v1 import generate_phase_report


def incident(level="NONE"):
    return {"verdict": "PASS" if level == "NONE" else "FAIL", "incident_level": level, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def eligibility(eligible=False):
    return {"verdict": "PASS" if not eligible else "FAIL", "eligible_for_rollback_review": eligible, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def checklist(status="NO_ACTION_REQUIRED"):
    return {"verdict": "PASS" if status in ("NO_ACTION_REQUIRED", "MONITOR") else "PARTIAL", "checklist_status": status, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def test_verified_safe():
    r = generate_phase_report(incident("NONE"), eligibility(False), checklist("NO_ACTION_REQUIRED"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "VERIFIED_SAFE_NO_ACTION"


def test_monitor_low():
    r = generate_phase_report(incident("LOW"), eligibility(False), checklist("MONITOR"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "MONITOR_ONLY"


def test_medium_review():
    r = generate_phase_report(incident("MEDIUM"), eligibility(True), checklist("ROLLBACK_REVIEW_REQUIRED"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_critical_rollback_review():
    r = generate_phase_report(incident("CRITICAL"), eligibility(True), checklist("ROLLBACK_REVIEW_REQUIRED"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "REQUIRE_HUMAN_ROLLBACK_REVIEW"


def test_stop_malformed():
    r = generate_phase_report(None, eligibility(False), checklist("NO_ACTION_REQUIRED"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_actions_always_false():
    r = generate_phase_report(incident("NONE"), eligibility(False), checklist("NO_ACTION_REQUIRED"))
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
    assert r["max_submit_count"] == 0
