import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_repeat_small_batch_dry_run_eligibility_packet_v1 import generate_packet


def phase_ok():
    return {
        "decision": "ALLOW_REPEAT_SMALL_BATCH_DRY_RUN",
        "submit_allowed": False,
        "max_submit_count": 0,
        "max_dry_run_candidates": 5,
    }


def test_t521_pass():
    r = generate_packet(phase_ok(), {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "PASS"
    assert r["eligible_for_repeat_dry_run"] is True
    assert r["submit_allowed"] is False
    assert r["max_dry_run_candidates"] <= 5


def test_t521_review_not_allowed_fail():
    p = phase_ok()
    p["decision"] = "REVIEW"
    r = generate_packet(p, {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"


def test_t521_submit_allowed_true_fail():
    p = phase_ok()
    p["submit_allowed"] = True
    r = generate_packet(p, {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"


def test_t521_prev_aggregate_partial_partial():
    r = generate_packet(phase_ok(), {"verdict": "PASS"}, {"verdict": "PARTIAL"})
    assert r["verdict"] == "PARTIAL"


def test_t521_malformed_input():
    r = generate_packet(None, {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"
