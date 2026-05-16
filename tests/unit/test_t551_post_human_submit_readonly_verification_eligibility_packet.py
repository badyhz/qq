import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_post_human_submit_readonly_verification_eligibility_packet_v1 import generate_eligibility


def phase(v="PASS", decision="READY_FOR_ONE_SHOT_HUMAN_GATED_TESTNET_SUBMIT"):
    return {"verdict": v, "decision": decision, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False, "max_submit_count": 1}


def runbook(v="PASS"):
    return {"verdict": v, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def checklist(v="PASS"):
    return {"verdict": v, "submit_allowed": False, "cancel_allowed": False, "flatten_allowed": False}


def test_pass():
    r = generate_eligibility(phase("PASS"), runbook("PASS"), checklist("PASS"))
    assert r["verdict"] == "PASS"
    assert r["verification_mode"] == "POST_HUMAN_SUBMIT_READONLY"
    assert r["readonly"] is True
    assert r["submit_allowed"] is False
    assert r["cancel_allowed"] is False
    assert r["flatten_allowed"] is False
    assert r["max_submit_count"] == 1


def test_partial_dry_run_only():
    r = generate_eligibility(phase("PASS", "READY_FOR_HUMAN_COPY_PASTE_DRY_RUN"), runbook("PASS"), checklist("PASS"))
    assert r["verdict"] == "PARTIAL"


def test_fail_submit_allowed_true():
    p = phase("PASS")
    p["submit_allowed"] = True
    r = generate_eligibility(p, runbook("PASS"), checklist("PASS"))
    assert r["verdict"] == "FAIL"


def test_fail_max_count_gt_1():
    p = phase("PASS")
    p["max_submit_count"] = 2
    r = generate_eligibility(p, runbook("PASS"), checklist("PASS"))
    assert r["verdict"] == "FAIL"


def test_malformed_input():
    r = generate_eligibility(None, runbook("PASS"), checklist("PASS"))
    assert r["verdict"] == "FAIL"
