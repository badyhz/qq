import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_small_batch_dry_run_eligibility_packet_v1 import generate_eligibility


def consistency(v="PASS"):
    return {"verdict": v}


def evidence(v="PASS"):
    return {"verdict": v}


def incident(v="PASS", level="NONE"):
    return {"verdict": v, "incident_level": level}


def test_t514_pass():
    r = generate_eligibility(consistency("PASS"), evidence("PASS"), incident("PASS", "NONE"))
    assert r["verdict"] == "PASS"
    assert r["eligible_for_small_batch_dry_run"] is True
    assert r["batch_mode"] == "DRY_RUN_ONLY"
    assert r["max_dry_run_candidates"] <= 5


def test_t514_consistency_partial_review():
    r = generate_eligibility(consistency("PARTIAL"), evidence("PASS"), incident("PASS", "NONE"))
    assert r["verdict"] in ["PARTIAL", "FAIL"]


def test_t514_incident_fail():
    r = generate_eligibility(consistency("PASS"), evidence("PASS"), incident("FAIL", "HIGH"))
    assert r["verdict"] == "FAIL"


def test_t514_submit_allowed_never_true():
    r = generate_eligibility(consistency("PASS"), evidence("PASS"), incident("PASS", "NONE"))
    assert r["submit_allowed"] is False


def test_t514_max_candidates_capped_at_5():
    r = generate_eligibility(consistency("PASS"), evidence("PASS"), incident("PASS", "NONE"))
    assert r["max_dry_run_candidates"] <= 5
