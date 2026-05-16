import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_manual_testnet_submit_risk_acceptance_checklist_v1 import generate_checklist


def cr(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def rs(v="PASS"):
    return {"verdict": v}


def test_ready():
    r = generate_checklist(cr("PASS"), rs("PASS"), None)
    assert r["verdict"] == "PASS"
    assert r["checklist_status"] == "READY_FOR_HUMAN_REVIEW"


def test_needs_review():
    r = generate_checklist(cr("PARTIAL"), rs("PASS"), None)
    assert r["verdict"] == "PARTIAL"
    assert r["checklist_status"] == "NEEDS_REVIEW"


def test_blocked():
    r = generate_checklist(cr("FAIL"), rs("PASS"), None)
    assert r["verdict"] == "FAIL"
    assert r["checklist_status"] == "BLOCKED"


def test_submit_never_allowed():
    r = generate_checklist(cr("PASS"), rs("PASS"), None)
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 0


def test_required_checks_present():
    r = generate_checklist(cr("PASS"), rs("PASS"), None)
    checks = " | ".join(r["required_human_checks"]).lower()
    for key in ["env=testnet", "symbol/side/quantity", "sl/tp", "dry-run", "naked/orphan", "mainnet/live"]:
        assert key in checks
