import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_manual_testnet_submit_review_eligibility_packet_v1 import generate_packet


def base_phase():
    return {
        "decision": "ALLOW_ANOTHER_SMALL_BATCH_DRY_RUN",
        "submit_allowed": False,
        "max_submit_count": 0,
        "max_dry_run_candidates": 5,
    }


def test_pass():
    r = generate_packet(base_phase(), {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "PASS"
    assert r["review_mode"] == "REVIEW_ONLY"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 0


def test_partial_stability():
    r = generate_packet(base_phase(), {"verdict": "PARTIAL"}, {"verdict": "PASS"})
    assert r["verdict"] == "PARTIAL"


def test_fail_submit_allowed_true():
    p = base_phase(); p["submit_allowed"] = True
    r = generate_packet(p, {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"


def test_fail_max_submit_count_gt0():
    p = base_phase(); p["max_submit_count"] = 1
    r = generate_packet(p, {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"


def test_malformed_fail():
    r = generate_packet(None, {"verdict": "PASS"}, {"verdict": "PASS"})
    assert r["verdict"] == "FAIL"
