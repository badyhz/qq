import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_single_manual_submit_packet_phase_control_report_v1 import generate_phase_report


def p(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def test_ready():
    r = generate_phase_report(p("PASS"), p("PASS"), p("PASS"), p("PASS"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "READY_FOR_HUMAN_MANUAL_TESTNET_SUBMIT"


def test_partial_review():
    r = generate_phase_report(p("PASS"), p("PARTIAL"), p("PASS"), p("PASS"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_fail_stop():
    r = generate_phase_report(p("PASS"), p("FAIL"), p("PASS"), p("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_submit_allowed_false_and_limit_1():
    r = generate_phase_report(p("PASS"), p("PASS"), p("PASS"), p("PASS"))
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1
