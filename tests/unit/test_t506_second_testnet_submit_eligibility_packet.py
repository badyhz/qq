import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_second_testnet_submit_eligibility_packet_v1 import generate_eligibility


def first_final_ok():
    return {
        "decision": "ALLOW_NEXT_TESTNET_SUBMIT",
        "can_submit_again": True,
        "max_next_submit_count": 1,
    }


def test_t506_pass_eligible():
    r = generate_eligibility(first_final_ok())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["eligible_for_second_submit"] is True
    assert r["max_submit_count"] == 1
    assert r["required_manual_confirmation"] is True


def test_t506_fail_not_allowed():
    f = first_final_ok()
    f["decision"] = "REVIEW"
    r = generate_eligibility(f)
    assert r["verdict"] == "FAIL"


def test_t506_fail_max_count_gt1():
    f = first_final_ok()
    f["max_next_submit_count"] = 2
    r = generate_eligibility(f)
    assert r["verdict"] == "FAIL"


def test_t506_partial_warning_inheritance():
    r = generate_eligibility(first_final_ok(), {"verdict": "PARTIAL"})
    assert r["verdict"] == "PARTIAL"
    assert "INHERITED_AUDIT_PARTIAL_WARNING" in r["warnings"]


def test_t506_fail_malformed_input():
    r = generate_eligibility(None)
    assert r["verdict"] == "FAIL"
