import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_human_gated_execution_wrapper_phase_control_report_v1 import generate_phase_report


def elig(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def plan(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def token(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def gate(v="PASS", status="READY_FOR_HUMAN_EXECUTION"):
    return {"verdict": v, "gate_status": status, "submit_allowed": False}


def test_ready():
    r = generate_phase_report(elig("PASS"), plan("PASS"), token("PASS"), gate("PASS", "READY_FOR_HUMAN_EXECUTION"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "READY_FOR_SINGLE_HUMAN_GATED_TESTNET_EXECUTION"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1
    assert r["can_continue"] is True


def test_partial_review():
    r = generate_phase_report(elig("PASS"), plan("PASS"), token("PARTIAL"), gate("PARTIAL", "NEEDS_REVIEW"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"
    assert r["can_continue"] is False


def test_fail_stop():
    r = generate_phase_report(elig("FAIL"), plan("PASS"), token("PASS"), gate("PASS", "READY_FOR_HUMAN_EXECUTION"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"
    assert r["can_continue"] is False


def test_submit_allowed_remains_false_always():
    r = generate_phase_report(elig("PASS"), plan("PASS"), token("PASS"), gate("PASS", "READY_FOR_HUMAN_EXECUTION"))
    assert r["submit_allowed"] is False

    r = generate_phase_report(elig("FAIL"), plan("FAIL"), token("FAIL"), gate("FAIL", "BLOCKED"))
    assert r["submit_allowed"] is False


def test_max_submit_count_1():
    r = generate_phase_report(elig("PASS"), plan("PASS"), token("PASS"), gate("PASS", "READY_FOR_HUMAN_EXECUTION"))
    assert r["max_submit_count"] == 1


def test_submit_allowed_true_in_input_fail():
    e = elig("PASS")
    e["submit_allowed"] = True
    r = generate_phase_report(e, plan("PASS"), token("PASS"), gate("PASS", "READY_FOR_HUMAN_EXECUTION"))
    assert r["verdict"] == "FAIL"
    assert "SUBMIT_ALLOWED_TRUE_NOT_PERMITTED" in r["blockers"]
