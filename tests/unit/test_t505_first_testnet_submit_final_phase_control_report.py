import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_first_testnet_submit_final_phase_control_report_v1 import generate_final_report


def phase(verdict="PASS"):
    return {"verdict": verdict}


def evidence(verdict="PASS"):
    return {"verdict": verdict, "submit_executed": True}


def incident(verdict="PASS", level="NONE"):
    return {"verdict": verdict, "incident_level": level}


def rollback(rec="NO_ACTION"):
    return {"recommendation": rec}


def audit(verdict="PASS"):
    return {"verdict": verdict}


def test_t505_allow_next_submit():
    r = generate_final_report(phase("PASS"), evidence("PASS"), incident("PASS", "NONE"), rollback("NO_ACTION"), audit("PASS"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "ALLOW_NEXT_TESTNET_SUBMIT"
    assert r["can_submit_again"] is True
    assert r["max_next_submit_count"] == 1


def test_t505_partial_review():
    r = generate_final_report(phase("PASS"), evidence("PARTIAL"), incident("PARTIAL", "MEDIUM"), rollback("REVIEW_REQUIRED"), audit("PARTIAL"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_t505_critical_stop():
    r = generate_final_report(phase("PASS"), evidence("FAIL"), incident("FAIL", "CRITICAL"), rollback("REVIEW_REQUIRED"), audit("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_t505_rollback_review_required():
    r = generate_final_report(phase("PASS"), evidence("FAIL"), incident("FAIL", "HIGH"), rollback("MANUAL_CONFIRM_FLATTEN_REQUIRED"), audit("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "REQUIRE_ROLLBACK_REVIEW"


def test_t505_audit_fail_stop():
    r = generate_final_report(phase("PASS"), evidence("PASS"), incident("PASS", "NONE"), rollback("NO_ACTION"), audit("FAIL"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"
