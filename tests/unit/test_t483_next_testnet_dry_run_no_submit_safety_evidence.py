import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_next_testnet_dry_run_no_submit_safety_evidence_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    verify_safety_evidence,
    load_json,
    write_json,
)


def safe_flags():
    return {
        "exchange_api_calls_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_order_allowed": False,
        "cancel_order_allowed": False,
        "flatten_position_allowed": False,
    }


def valid_t482():
    return {"ok": True, "final_decision": "READY_FOR_NEXT_TESTNET_DRY_RUN_NO_SUBMIT_SAFETY_EVIDENCE_REVIEW", "safety_flags": safe_flags()}


def valid_t479():
    return {"ok": True, "artifact_report": {"status": "NEXT_ARTIFACT_ONLY_NO_SUBMIT_MATERIALIZED", "exchange_api_call_attempted": False, "submit_attempted": False, "cancel_attempted": False, "flatten_attempted": False}}


def valid_t480():
    return {"ok": True, "final_decision": "READY_FOR_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW", "safety_flags": safe_flags()}


def test_valid_inputs_pass(tmp_path):
    r = verify_safety_evidence(valid_t482(), valid_t479(), valid_t480())
    assert r["ok"] is True
    assert r["safety_evidence_status"] == "NEXT_DRY_RUN_NO_SUBMIT_SAFETY_EVIDENCE_VERIFIED"


def test_t482_blocked_fail(tmp_path):
    t482 = valid_t482(); t482["ok"] = False
    r = verify_safety_evidence(t482, valid_t479(), valid_t480())
    assert "CONSISTENCY_REPORT_NOT_READY" in r["violations"]


def test_t479_blocked_fail(tmp_path):
    t479 = valid_t479(); t479["ok"] = False
    r = verify_safety_evidence(valid_t482(), t479, valid_t480())
    assert "MATERIALIZATION_REPORT_NOT_READY" in r["violations"]


def test_t480_blocked_fail(tmp_path):
    t480 = valid_t480(); t480["ok"] = False
    r = verify_safety_evidence(valid_t482(), valid_t479(), t480)
    assert "PHASE_CONTROL_REPORT_NOT_READY" in r["violations"]


def test_artifact_status_wrong_fail(tmp_path):
    t479 = valid_t479(); t479["artifact_report"]["status"] = "BAD"
    r = verify_safety_evidence(valid_t482(), t479, valid_t480())
    assert "ARTIFACT_ONLY_MATERIALIZATION_NOT_CONFIRMED" in r["violations"]


def test_exchange_submit_cancel_flatten_attempt_fail(tmp_path):
    t479 = valid_t479(); t479["artifact_report"]["exchange_api_call_attempted"] = True
    r = verify_safety_evidence(valid_t482(), t479, valid_t480())
    assert "EXCHANGE_API_ATTEMPT_DETECTED" in r["violations"]

    t479 = valid_t479(); t479["artifact_report"]["submit_attempted"] = True
    r = verify_safety_evidence(valid_t482(), t479, valid_t480())
    assert "SUBMIT_ATTEMPT_DETECTED" in r["violations"]

    t479 = valid_t479(); t479["artifact_report"]["cancel_attempted"] = True
    r = verify_safety_evidence(valid_t482(), t479, valid_t480())
    assert "CANCEL_ATTEMPT_DETECTED" in r["violations"]

    t479 = valid_t479(); t479["artifact_report"]["flatten_attempted"] = True
    r = verify_safety_evidence(valid_t482(), t479, valid_t480())
    assert "FLATTEN_ATTEMPT_DETECTED" in r["violations"]


def test_never_allows_blocked_actions(tmp_path):
    r = verify_safety_evidence(valid_t482(), valid_t479(), valid_t480())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t482.json")
    p2 = str(tmp_path / "t479.json")
    p3 = str(tmp_path / "t480.json")
    write_json(p1, valid_t482())
    write_json(p2, valid_t479())
    with open(p3, "w", encoding="utf-8") as f:
        f.write("bad")
    r = verify_safety_evidence(load_json(p1), load_json(p2), load_json(p3))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t482.json")
    p2 = str(tmp_path / "t479.json")
    p3 = str(tmp_path / "missing.json")
    write_json(p1, valid_t482())
    write_json(p2, valid_t479())
    r = verify_safety_evidence(load_json(p1), load_json(p2), load_json(p3))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t482.json")
    p2 = str(tmp_path / "t479.json")
    p3 = str(tmp_path / "t480.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t482())
    write_json(p2, valid_t479())
    write_json(p3, valid_t480())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "verify_next_testnet_dry_run_no_submit_safety_evidence_v1.py"),
        "--consistency-report", p1,
        "--materialization-report", p2,
        "--phase-control-report", p3,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
