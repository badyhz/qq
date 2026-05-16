import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_second_testnet_submit_phase_control_report_v1 import generate_phase_report


def eligibility(v="PASS"):
    return {"verdict": v}


def command(v="PASS"):
    return {"verdict": v}


def repeatability(v="PASS"):
    return {"verdict": v}


def safety(v="PASS"):
    return {"verdict": v}


def test_t510_allow_third_manual_submit():
    r = generate_phase_report(eligibility("PASS"), command("PASS"), repeatability("PASS"), safety("PASS"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "ALLOW_THIRD_MANUAL_TESTNET_SUBMIT"
    assert r["can_submit_again"] is True
    assert r["max_next_submit_count"] == 1


def test_t510_partial_review():
    r = generate_phase_report(eligibility("PASS"), command("PASS"), repeatability("PARTIAL"), safety("PASS"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_t510_repeatability_fail_stop():
    r = generate_phase_report(eligibility("PASS"), command("PASS"), repeatability("FAIL"), safety("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_t510_safety_fail_stop():
    r = generate_phase_report(eligibility("PASS"), command("PASS"), repeatability("PASS"), safety("FAIL"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_t510_never_allow_count_gt1():
    r = generate_phase_report(eligibility("PASS"), command("PASS"), repeatability("PASS"), safety("PASS"))
    assert r["max_next_submit_count"] <= 1
