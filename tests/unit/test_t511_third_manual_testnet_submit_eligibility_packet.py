import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_third_manual_testnet_submit_eligibility_packet_v1 import generate_eligibility


def second_phase_ok():
    return {
        "decision": "ALLOW_THIRD_MANUAL_TESTNET_SUBMIT",
        "can_submit_again": True,
        "max_next_submit_count": 1,
    }


def test_t511_pass():
    r = generate_eligibility(second_phase_ok(), {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "PASS"
    assert r["eligible_for_third_manual_submit"] is True
    assert r["max_submit_count"] == 1
    assert r["required_manual_confirmation"] is True


def test_t511_fail_not_allowed():
    s = second_phase_ok()
    s["decision"] = "REVIEW"
    r = generate_eligibility(s, {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"


def test_t511_fail_max_count_gt1():
    s = second_phase_ok()
    s["max_next_submit_count"] = 2
    r = generate_eligibility(s, {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"


def test_t511_partial_missing_optional_score():
    r = generate_eligibility(second_phase_ok(), None, {"verdict": "PASS"})
    assert r["verdict"] == "PARTIAL"


def test_t511_fail_malformed_input():
    r = generate_eligibility(None, {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"
