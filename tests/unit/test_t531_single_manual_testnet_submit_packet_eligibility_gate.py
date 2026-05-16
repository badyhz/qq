import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_single_manual_testnet_submit_packet_eligibility_gate_v1 import generate_gate


def phase(decision="ALLOW_SINGLE_MANUAL_SUBMIT_PACKET_GENERATION", submit_allowed=False, max_submit_count=0):
    return {
        "decision": decision,
        "submit_allowed": submit_allowed,
        "max_submit_count": max_submit_count,
    }


def test_pass():
    r = generate_gate(phase(), {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "PASS"
    assert r["eligible_for_packet_generation"] is True
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1


def test_fail_wrong_phase_decision():
    r = generate_gate(phase(decision="REVIEW"), {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"


def test_fail_submit_allowed_true():
    r = generate_gate(phase(submit_allowed=True), {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"


def test_partial_missing_optional_score():
    r = generate_gate(phase(), None, {"verdict": "PASS"})
    assert r["verdict"] == "PARTIAL"


def test_malformed_input_fail():
    r = generate_gate(None, {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"
