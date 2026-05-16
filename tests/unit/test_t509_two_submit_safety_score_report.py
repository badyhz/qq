import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_two_submit_safety_score_report_v1 import generate_safety_score


def first_final():
    return {"decision": "ALLOW_NEXT_TESTNET_SUBMIT", "can_submit_again": True, "max_next_submit_count": 1}


def second_evidence(verdict="PASS"):
    return {"verdict": verdict}


def second_incident(level="NONE"):
    return {"incident_level": level}


def repeatability(status="REPEATABLE"):
    return {"repeatability_status": status}


def test_t509_pass_100():
    r = generate_safety_score(first_final(), second_evidence("PASS"), second_incident("NONE"), repeatability("REPEATABLE"))
    assert r["verdict"] == "PASS"
    assert r["safety_score"] == 100
    assert r["decision"] == "ALLOW_THIRD_MANUAL_TESTNET_SUBMIT"


def test_t509_partial_drift():
    r = generate_safety_score(first_final(), second_evidence("PASS"), second_incident("NONE"), repeatability("DRIFT_DETECTED"))
    assert r["verdict"] == "PARTIAL"


def test_t509_fail_critical():
    r = generate_safety_score(first_final(), second_evidence("PASS"), second_incident("CRITICAL"), repeatability("REPEATABLE"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_t509_fail_low_score():
    r = generate_safety_score(first_final(), second_evidence("PARTIAL"), second_incident("HIGH"), repeatability("DRIFT_DETECTED"))
    assert r["verdict"] == "FAIL"


def test_t509_no_auto_batch_submit():
    r = generate_safety_score(first_final(), second_evidence("PASS"), second_incident("NONE"), repeatability("REPEATABLE"))
    assert "BATCH_LIVE" not in r["decision"]
