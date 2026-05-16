import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_readonly_verification_phase_control_report_v1 import generate_phase_report


def eligibility(v="PASS"):
    return {"verdict": v, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def parser(v="PASS"):
    return {"verdict": v, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def plan(v="PASS"):
    return {"verdict": v, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def evidence(v="PASS", naked=False, orphan=False):
    return {"verdict": v, "naked_position_detected": naked, "orphan_protection_detected": orphan, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def test_verified():
    r = generate_phase_report(eligibility("PASS"), parser("PASS"), plan("PASS"), evidence("PASS"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "VERIFIED_ONE_SHOT_TESTNET_SUBMIT"
    assert r["readonly"] is True
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
    assert r["max_submit_count"] == 0


def test_partial_review():
    r = generate_phase_report(eligibility("PASS"), parser("PASS"), plan("PARTIAL"), evidence("PASS"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_naked_rollback_review():
    r = generate_phase_report(eligibility("PASS"), parser("PASS"), plan("PASS"), evidence("PASS", naked=True))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "REQUIRE_ROLLBACK_REVIEW"


def test_orphan_rollback_review():
    r = generate_phase_report(eligibility("PASS"), parser("PASS"), plan("PASS"), evidence("PASS", orphan=True))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "REQUIRE_ROLLBACK_REVIEW"


def test_fail_stop():
    r = generate_phase_report(eligibility("FAIL"), parser("PASS"), plan("PASS"), evidence("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_no_actions_allowed():
    r = generate_phase_report(eligibility("PASS"), parser("PASS"), plan("PASS"), evidence("PASS"))
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
    assert r["max_submit_count"] == 0
