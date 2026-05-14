import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_next_testnet_dry_run_result_review_phase_control_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_phase_control_report,
    load_json,
    write_json,
)


def safe_flags():
    return {
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


def allowed():
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "REVIEW_NEXT_DRY_RUN_ARTIFACTS"]


def blocked():
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t481():
    return {"final_decision": "READY_FOR_NEXT_TESTNET_DRY_RUN_PAYLOAD_MATERIALIZATION_CONSISTENCY_REVIEW", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t482():
    return {"final_decision": "READY_FOR_NEXT_TESTNET_DRY_RUN_NO_SUBMIT_SAFETY_EVIDENCE_REVIEW", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t483():
    return {"final_decision": "READY_FOR_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW_SCORE", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t484():
    return {"final_decision": "READY_FOR_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW_PHASE_CONTROL", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def run_report(t481, t482, t483, t484, tmp_path):
    p481 = str(tmp_path / "t481.json")
    p482 = str(tmp_path / "t482.json")
    p483 = str(tmp_path / "t483.json")
    p484 = str(tmp_path / "t484.json")
    write_json(p481, t481)
    write_json(p482, t482)
    write_json(p483, t483)
    write_json(p484, t484)
    return generate_phase_control_report(t481, t482, t483, t484, p481, p482, p483, p484)


def test_all_pass_ready_for_stability_review(tmp_path):
    r = run_report(valid_t481(), valid_t482(), valid_t483(), valid_t484(), tmp_path)
    assert r["ok"] is True
    assert r["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_STABILITY_REVIEW"


def test_each_component_fail_exact_blocker(tmp_path):
    t481 = valid_t481(); t481["final_decision"] = "BAD"
    r = run_report(t481, valid_t482(), valid_t483(), valid_t484(), tmp_path)
    assert "T481_REVIEW_PACKET_NOT_READY" in r["blockers"]

    t482 = valid_t482(); t482["final_decision"] = "BAD"
    r = run_report(valid_t481(), t482, valid_t483(), valid_t484(), tmp_path)
    assert "T482_CONSISTENCY_NOT_VERIFIED" in r["blockers"]

    t483 = valid_t483(); t483["final_decision"] = "BAD"
    r = run_report(valid_t481(), valid_t482(), t483, valid_t484(), tmp_path)
    assert "T483_SAFETY_EVIDENCE_NOT_VERIFIED" in r["blockers"]

    t484 = valid_t484(); t484["final_decision"] = "BAD"
    r = run_report(valid_t481(), valid_t482(), valid_t483(), t484, tmp_path)
    assert "T484_REVIEW_SCORE_NOT_READY" in r["blockers"]


def test_exchange_submit_cancel_flatten_violation_blocker(tmp_path):
    t484 = valid_t484(); t484["safety_flags"]["exchange_api_calls_allowed"] = True
    r = run_report(valid_t481(), valid_t482(), valid_t483(), t484, tmp_path)
    assert "NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED" in r["blockers"]


def test_allowed_actions_never_contains_blocked(tmp_path):
    r = run_report(valid_t481(), valid_t482(), valid_t483(), valid_t484(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]


def test_blocked_actions_include_all(tmp_path):
    r = run_report(valid_t481(), valid_t482(), valid_t483(), valid_t484(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p481 = str(tmp_path / "t481.json")
    p482 = str(tmp_path / "t482.json")
    p483 = str(tmp_path / "t483.json")
    p484 = str(tmp_path / "t484.json")
    write_json(p481, valid_t481())
    write_json(p482, valid_t482())
    write_json(p483, valid_t483())
    with open(p484, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_phase_control_report(load_json(p481), load_json(p482), load_json(p483), load_json(p484), p481, p482, p483, p484)
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p481 = str(tmp_path / "t481.json")
    p482 = str(tmp_path / "t482.json")
    p483 = str(tmp_path / "t483.json")
    p484 = str(tmp_path / "missing.json")
    write_json(p481, valid_t481())
    write_json(p482, valid_t482())
    write_json(p483, valid_t483())
    r = generate_phase_control_report(load_json(p481), load_json(p482), load_json(p483), load_json(p484), p481, p482, p483, p484)
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p481 = str(tmp_path / "t481.json")
    p482 = str(tmp_path / "t482.json")
    p483 = str(tmp_path / "t483.json")
    p484 = str(tmp_path / "t484.json")
    out = str(tmp_path / "out.json")
    write_json(p481, valid_t481())
    write_json(p482, valid_t482())
    write_json(p483, valid_t483())
    write_json(p484, valid_t484())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_next_testnet_dry_run_result_review_phase_control_report_v1.py"),
        "--review-packet", p481,
        "--consistency-report", p482,
        "--safety-evidence-report", p483,
        "--review-score-report", p484,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
