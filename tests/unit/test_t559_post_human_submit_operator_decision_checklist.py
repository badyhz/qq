import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_operator_decision_checklist_v1 import generate_operator_checklist


def incident(level="NONE"):
    return {"verdict": "PASS" if level == "NONE" else "FAIL", "incident_level": level, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def eligibility(eligible=True):
    return {"verdict": "PASS" if not eligible else "FAIL", "eligible_for_rollback_review": eligible, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def test_no_action():
    r = generate_operator_checklist(incident("NONE"), eligibility(False))
    assert r["verdict"] == "PASS"
    assert r["checklist_status"] == "NO_ACTION_REQUIRED"


def test_monitor():
    r = generate_operator_checklist(incident("LOW"), eligibility(True))
    assert r["verdict"] == "PASS"
    assert r["checklist_status"] == "MONITOR"


def test_rollback_review():
    r = generate_operator_checklist(incident("CRITICAL"), eligibility(True))
    assert r["checklist_status"] == "ROLLBACK_REVIEW_REQUIRED"
    assert len(r["required_human_checks"]) > 0


def test_blocked():
    r = generate_operator_checklist(None, eligibility(True))
    assert r["verdict"] == "FAIL"
    assert r["checklist_status"] == "BLOCKED"


def test_required_checks_present():
    r = generate_operator_checklist(incident("CRITICAL"), eligibility(True))
    checks = r["required_human_checks"]
    assert "verify env=testnet" in checks
    assert "verify current position manually" in checks
    assert "verify protective SL/TP state" in checks
    assert "verify naked/orphan status" in checks
    assert "verify safe_flatten dry-run before any confirm" in checks
    assert "verify no mainnet/live marker" in checks
    assert "verify no repeated submit" in checks


def test_actions_false():
    r = generate_operator_checklist(incident("CRITICAL"), eligibility(True))
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
