import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_testnet_dry_run_result_safety_evidence_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    verify_safety_evidence,
    load_json,
    write_json,
)


def safe_flags():
    return {
        "testnet_dry_run_allowed": True,
        "exchange_api_calls_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_order_allowed": False,
        "cancel_order_allowed": False,
        "flatten_position_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


def valid_t467():
    return {"ok": True, "final_decision": "READY_FOR_TESTNET_DRY_RUN_RESULT_SAFETY_EVIDENCE_REVIEW", "safety_flags": safe_flags()}


def valid_t463():
    return {
        "ok": True,
        "execution_result_status": "TESTNET_DRY_RUN_ONLY_EXECUTION_REPORTED",
        "simulated_execution_summary": {
            "status": "ARTIFACT_ONLY_NO_SUBMIT_COMPLETED",
            "exchange_api_call_attempted": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
        "safety_flags": safe_flags(),
    }


def valid_t464():
    return {"ok": True, "artifact_verification_status": "TESTNET_DRY_RUN_ONLY_ARTIFACTS_VERIFIED", "safety_flags": safe_flags()}


def test_valid_inputs_pass(tmp_path):
    r = verify_safety_evidence(valid_t467(), valid_t463(), valid_t464())
    assert r["ok"] is True
    assert r["safety_evidence_status"] == "DRY_RUN_RESULT_NO_SUBMIT_SAFETY_EVIDENCE_VERIFIED"


def test_t467_blocked_fail(tmp_path):
    t = valid_t467(); t["ok"] = False
    r = verify_safety_evidence(t, valid_t463(), valid_t464())
    assert r["ok"] is False
    assert "CONSISTENCY_REPORT_NOT_READY" in r["violations"]


def test_t463_blocked_fail(tmp_path):
    t = valid_t463(); t["ok"] = False
    r = verify_safety_evidence(valid_t467(), t, valid_t464())
    assert r["ok"] is False
    assert "EXECUTION_RESULT_REPORT_NOT_READY" in r["violations"]


def test_t464_blocked_fail(tmp_path):
    t = valid_t464(); t["ok"] = False
    r = verify_safety_evidence(valid_t467(), valid_t463(), t)
    assert r["ok"] is False
    assert "ARTIFACT_VERIFICATION_REPORT_NOT_READY" in r["violations"]


def test_simulated_status_wrong_fail(tmp_path):
    t = valid_t463(); t["simulated_execution_summary"]["status"] = "BAD"
    r = verify_safety_evidence(valid_t467(), t, valid_t464())
    assert r["ok"] is False
    assert "SIMULATED_EXECUTION_NOT_COMPLETED" in r["violations"]


def test_exchange_submit_cancel_flatten_attempt_fail(tmp_path):
    t = valid_t463(); t["simulated_execution_summary"]["exchange_api_call_attempted"] = True
    r = verify_safety_evidence(valid_t467(), t, valid_t464())
    assert "EXCHANGE_API_ATTEMPT_DETECTED" in r["violations"]

    t = valid_t463(); t["simulated_execution_summary"]["submit_attempted"] = True
    r = verify_safety_evidence(valid_t467(), t, valid_t464())
    assert "SUBMIT_ATTEMPT_DETECTED" in r["violations"]

    t = valid_t463(); t["simulated_execution_summary"]["cancel_attempted"] = True
    r = verify_safety_evidence(valid_t467(), t, valid_t464())
    assert "CANCEL_ATTEMPT_DETECTED" in r["violations"]

    t = valid_t463(); t["simulated_execution_summary"]["flatten_attempted"] = True
    r = verify_safety_evidence(valid_t467(), t, valid_t464())
    assert "FLATTEN_ATTEMPT_DETECTED" in r["violations"]


def test_never_allows_blocked_actions(tmp_path):
    r = verify_safety_evidence(valid_t467(), valid_t463(), valid_t464())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t467.json")
    p2 = str(tmp_path / "t463.json")
    p3 = str(tmp_path / "t464.json")
    write_json(p1, valid_t467())
    write_json(p2, valid_t463())
    with open(p3, "w", encoding="utf-8") as f:
        f.write("bad")
    r = verify_safety_evidence(load_json(p1), load_json(p2), load_json(p3))
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t467.json")
    p2 = str(tmp_path / "t463.json")
    p3 = str(tmp_path / "missing.json")
    write_json(p1, valid_t467())
    write_json(p2, valid_t463())
    r = verify_safety_evidence(load_json(p1), load_json(p2), load_json(p3))
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t467.json")
    p2 = str(tmp_path / "t463.json")
    p3 = str(tmp_path / "t464.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t467())
    write_json(p2, valid_t463())
    write_json(p3, valid_t464())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "verify_testnet_dry_run_result_safety_evidence_v1.py"),
        "--consistency-report", p1,
        "--execution-result-report", p2,
        "--artifact-verification-report", p3,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
