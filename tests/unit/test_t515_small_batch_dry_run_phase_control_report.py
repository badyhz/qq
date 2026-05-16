import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_small_batch_dry_run_phase_control_report_v1 import generate_phase_control


def elig(v="PASS", max_dry=5):
    return {"verdict": v, "max_dry_run_candidates": max_dry}


def cons(v="PASS"):
    return {"verdict": v}


def test_t515_allow_dry_run_only():
    r = generate_phase_control(elig("PASS", 5), cons("PASS"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "ALLOW_SMALL_BATCH_DRY_RUN_ONLY"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 0
    assert r["max_dry_run_candidates"] <= 5


def test_t515_partial_review():
    r = generate_phase_control(elig("PARTIAL", 5), cons("PASS"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_t515_fail_stop():
    r = generate_phase_control(elig("FAIL", 5), cons("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_t515_submit_never_allowed():
    r = generate_phase_control(elig("PASS", 5), cons("PASS"))
    assert r["submit_allowed"] is False


def test_t515_candidate_cap():
    r = generate_phase_control(elig("PASS", 99), cons("PASS"))
    assert r["max_dry_run_candidates"] <= 5
