import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_final_human_gated_one_shot_submit_phase_control_report_v1 import generate_phase_report


def readiness(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def verify(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def checklist(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def runbook(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def test_ready_one_shot():
    r = generate_phase_report(readiness("PASS"), verify("PASS"), checklist("PASS"), runbook("PASS"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "READY_FOR_ONE_SHOT_HUMAN_GATED_TESTNET_SUBMIT"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1


def test_ready_dry_run_only():
    r = generate_phase_report(readiness("PASS"), verify("PARTIAL"), checklist("PASS"), runbook("PASS"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "READY_FOR_HUMAN_COPY_PASTE_DRY_RUN"


def test_review():
    r = generate_phase_report(readiness("PASS"), verify("PASS"), checklist("PARTIAL"), runbook("PASS"))
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW"


def test_stop():
    r = generate_phase_report(readiness("FAIL"), verify("PASS"), checklist("PASS"), runbook("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "STOP"


def test_submit_allowed_remains_false():
    r = generate_phase_report(readiness("PASS"), verify("PASS"), checklist("PASS"), runbook("PASS"))
    assert r["submit_allowed"] is False
