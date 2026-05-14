import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_result_review_phase_control_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_phase_control_report,
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


def allowed():
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "REVIEW_DRY_RUN_ARTIFACTS"]


def blocked():
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t466():
    return {"final_decision": "READY_FOR_TESTNET_DRY_RUN_MATERIALIZED_PAYLOAD_CONSISTENCY_REVIEW", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t467():
    return {"final_decision": "READY_FOR_TESTNET_DRY_RUN_RESULT_SAFETY_EVIDENCE_REVIEW", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t468():
    return {"final_decision": "READY_FOR_TESTNET_DRY_RUN_RESULT_REVIEW_SCORE", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t469():
    return {"final_decision": "READY_FOR_TESTNET_DRY_RUN_RESULT_REVIEW_PHASE_CONTROL", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def run_report(t466, t467, t468, t469, tmp_path):
    p466 = str(tmp_path / "t466.json")
    p467 = str(tmp_path / "t467.json")
    p468 = str(tmp_path / "t468.json")
    p469 = str(tmp_path / "t469.json")
    write_json(p466, t466)
    write_json(p467, t467)
    write_json(p468, t468)
    write_json(p469, t469)
    return generate_phase_control_report(t466, t467, t468, t469, p466, p467, p468, p469)


def test_all_pass_ready_for_iteration_review(tmp_path):
    r = run_report(valid_t466(), valid_t467(), valid_t468(), valid_t469(), tmp_path)
    assert r["ok"] is True
    assert r["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ITERATION_REVIEW"


def test_each_component_fail_exact_blocker(tmp_path):
    t466 = valid_t466(); t466["final_decision"] = "BAD"
    r = run_report(t466, valid_t467(), valid_t468(), valid_t469(), tmp_path)
    assert "T466_REVIEW_PACKET_NOT_READY" in r["blockers"]

    t467 = valid_t467(); t467["final_decision"] = "BAD"
    r = run_report(valid_t466(), t467, valid_t468(), valid_t469(), tmp_path)
    assert "T467_CONSISTENCY_NOT_VERIFIED" in r["blockers"]

    t468 = valid_t468(); t468["final_decision"] = "BAD"
    r = run_report(valid_t466(), valid_t467(), t468, valid_t469(), tmp_path)
    assert "T468_SAFETY_EVIDENCE_NOT_VERIFIED" in r["blockers"]

    t469 = valid_t469(); t469["final_decision"] = "BAD"
    r = run_report(valid_t466(), valid_t467(), valid_t468(), t469, tmp_path)
    assert "T469_REVIEW_SCORE_NOT_READY" in r["blockers"]


def test_exchange_submit_cancel_flatten_violation_blocker(tmp_path):
    t469 = valid_t469(); t469["safety_flags"]["exchange_api_calls_allowed"] = True
    r = run_report(valid_t466(), valid_t467(), valid_t468(), t469, tmp_path)
    assert "NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED" in r["blockers"]


def test_allowed_actions_never_contains_blocked(tmp_path):
    r = run_report(valid_t466(), valid_t467(), valid_t468(), valid_t469(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]


def test_blocked_actions_include_all(tmp_path):
    r = run_report(valid_t466(), valid_t467(), valid_t468(), valid_t469(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p466 = str(tmp_path / "t466.json")
    p467 = str(tmp_path / "t467.json")
    p468 = str(tmp_path / "t468.json")
    p469 = str(tmp_path / "t469.json")
    write_json(p466, valid_t466())
    write_json(p467, valid_t467())
    write_json(p468, valid_t468())
    with open(p469, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_phase_control_report(load_json(p466), load_json(p467), load_json(p468), load_json(p469), p466, p467, p468, p469)
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p466 = str(tmp_path / "t466.json")
    p467 = str(tmp_path / "t467.json")
    p468 = str(tmp_path / "t468.json")
    p469 = str(tmp_path / "missing.json")
    write_json(p466, valid_t466())
    write_json(p467, valid_t467())
    write_json(p468, valid_t468())
    r = generate_phase_control_report(load_json(p466), load_json(p467), load_json(p468), load_json(p469), p466, p467, p468, p469)
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p466 = str(tmp_path / "t466.json")
    p467 = str(tmp_path / "t467.json")
    p468 = str(tmp_path / "t468.json")
    p469 = str(tmp_path / "t469.json")
    out = str(tmp_path / "out.json")
    write_json(p466, valid_t466())
    write_json(p467, valid_t467())
    write_json(p468, valid_t468())
    write_json(p469, valid_t469())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_result_review_phase_control_report_v1.py"),
        "--review-packet", p466,
        "--consistency-report", p467,
        "--safety-evidence-report", p468,
        "--review-score-report", p469,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
