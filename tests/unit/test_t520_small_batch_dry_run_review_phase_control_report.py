import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_small_batch_dry_run_review_phase_control_report_v1 import generate_report


def selection(v="PASS", m=5):
    return {"verdict": v, "max_dry_run_candidates": m}


def execution(v="PASS"):
    return {"verdict": v}


def aggregate(v="PASS"):
    return {"verdict": v}


def concentration(v="PASS", status="LOW"):
    return {"verdict": v, "concentration_status": status}


def test_t520_repeat_dry_run_allowed():
    r = generate_report(selection(), execution(), aggregate(), concentration("PASS", "LOW"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "ALLOW_REPEAT_SMALL_BATCH_DRY_RUN"


def test_t520_high_concentration_review():
    r = generate_report(selection(), execution(), aggregate(), concentration("PASS", "HIGH"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_t520_partial_review():
    r = generate_report(selection("PARTIAL"), execution(), aggregate(), concentration("PASS", "LOW"))
    assert r["verdict"] == "PARTIAL"


def test_t520_fail_stop():
    r = generate_report(selection(), execution("FAIL"), aggregate(), concentration("PASS", "LOW"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_t520_submit_never_allowed():
    r = generate_report(selection(), execution(), aggregate(), concentration("PASS", "LOW"))
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 0
    assert r["max_dry_run_candidates"] <= 5
