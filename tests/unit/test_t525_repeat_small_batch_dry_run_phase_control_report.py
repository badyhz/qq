import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_repeat_small_batch_dry_run_phase_control_report_v1 import generate_report


def packet(v="PASS"):
    return {"verdict": v, "max_dry_run_candidates": 5}


def test_t525_allow_another_dry_run():
    r = generate_report(packet("PASS"), packet("PASS"), packet("PASS"), packet("PASS"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "ALLOW_ANOTHER_SMALL_BATCH_DRY_RUN"
    assert r["submit_allowed"] is False


def test_t525_partial_review():
    r = generate_report(packet("PASS"), packet("PARTIAL"), packet("PASS"), packet("PASS"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_t525_fail_stop():
    r = generate_report(packet("PASS"), packet("FAIL"), packet("PASS"), packet("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_t525_submit_never_allowed():
    r = generate_report(packet("PASS"), packet("PASS"), packet("PASS"), packet("PASS"))
    assert r["submit_allowed"] is False


def test_t525_max_submit_count_always_zero():
    r = generate_report(packet("PASS"), packet("PASS"), packet("PASS"), packet("PASS"))
    assert r["max_submit_count"] == 0
    assert r["max_dry_run_candidates"] <= 5
