import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_single_human_gated_execution_wrapper_artifact_phase_control_report_v1 import generate_phase_report


def artifact(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def invariant(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def preview(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def manifest(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def test_ready():
    r = generate_phase_report(artifact("PASS"), invariant("PASS"), preview("PASS"), manifest("PASS"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "READY_FOR_HUMAN_GATED_SINGLE_TESTNET_SUBMIT"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1


def test_partial_review():
    r = generate_phase_report(artifact("PASS"), invariant("PARTIAL"), preview("PASS"), manifest("PASS"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_fail_stop():
    r = generate_phase_report(artifact("FAIL"), invariant("PASS"), preview("PASS"), manifest("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_submit_allowed_remains_false():
    r = generate_phase_report(artifact("PASS"), invariant("PASS"), preview("PASS"), manifest("PASS"))
    assert r["submit_allowed"] is False


def test_max_submit_count_limited_to_1():
    r = generate_phase_report(artifact("PASS"), invariant("PASS"), preview("PASS"), manifest("PASS"))
    assert r["max_submit_count"] == 1


def test_submit_allowed_true_in_input_fail():
    a = artifact("PASS")
    a["submit_allowed"] = True
    r = generate_phase_report(a, invariant("PASS"), preview("PASS"), manifest("PASS"))
    assert r["verdict"] == "FAIL"
    assert "SUBMIT_ALLOWED_TRUE_NOT_PERMITTED" in r["blockers"]
