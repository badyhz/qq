import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_iteration_review_phase_control_report_v1 import (
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
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "REVIEW_DRY_RUN_ARTIFACTS", "GENERATE_NEXT_DRY_RUN_PLAN"]


def blocked():
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t471():
    return {"final_decision": "READY_FOR_DRY_RUN_RESULT_BLOCKER_ANALYSIS", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t472():
    return {"final_decision": "READY_FOR_NEXT_DRY_RUN_ITERATION_PLAN", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t473():
    return {"final_decision": "READY_FOR_DRY_RUN_ITERATION_APPROVAL_ARTIFACT", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t474():
    return {"final_decision": "READY_FOR_DRY_RUN_ITERATION_REVIEW_PHASE_CONTROL", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def run_report(t471, t472, t473, t474, tmp_path):
    p471 = str(tmp_path / "t471.json")
    p472 = str(tmp_path / "t472.json")
    p473 = str(tmp_path / "t473.json")
    p474 = str(tmp_path / "t474.json")
    write_json(p471, t471)
    write_json(p472, t472)
    write_json(p473, t473)
    write_json(p474, t474)
    return generate_phase_control_report(t471, t472, t473, t474, p471, p472, p473, p474)


def test_all_pass_ready_for_next_iteration(tmp_path):
    r = run_report(valid_t471(), valid_t472(), valid_t473(), valid_t474(), tmp_path)
    assert r["ok"] is True
    assert r["final_decision"] == "READY_FOR_NEXT_TESTNET_DRY_RUN_ONLY_ITERATION"


def test_each_component_fail_exact_blocker(tmp_path):
    t471 = valid_t471(); t471["final_decision"] = "BAD"
    r = run_report(t471, valid_t472(), valid_t473(), valid_t474(), tmp_path)
    assert "T471_ITERATION_REVIEW_PACKET_NOT_READY" in r["blockers"]

    t472 = valid_t472(); t472["final_decision"] = "BAD"
    r = run_report(valid_t471(), t472, valid_t473(), valid_t474(), tmp_path)
    assert "T472_BLOCKER_ANALYSIS_NOT_READY" in r["blockers"]

    t473 = valid_t473(); t473["final_decision"] = "BAD"
    r = run_report(valid_t471(), valid_t472(), t473, valid_t474(), tmp_path)
    assert "T473_ITERATION_PLAN_NOT_READY" in r["blockers"]

    t474 = valid_t474(); t474["final_decision"] = "BAD"
    r = run_report(valid_t471(), valid_t472(), valid_t473(), t474, tmp_path)
    assert "T474_APPROVAL_ARTIFACT_NOT_READY" in r["blockers"]


def test_exchange_submit_cancel_flatten_violation_blocker(tmp_path):
    t474 = valid_t474(); t474["safety_flags"]["exchange_api_calls_allowed"] = True
    r = run_report(valid_t471(), valid_t472(), valid_t473(), t474, tmp_path)
    assert "NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED" in r["blockers"]


def test_allowed_actions_never_contains_blocked(tmp_path):
    r = run_report(valid_t471(), valid_t472(), valid_t473(), valid_t474(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]


def test_blocked_actions_include_all(tmp_path):
    r = run_report(valid_t471(), valid_t472(), valid_t473(), valid_t474(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p471 = str(tmp_path / "t471.json")
    p472 = str(tmp_path / "t472.json")
    p473 = str(tmp_path / "t473.json")
    p474 = str(tmp_path / "t474.json")
    write_json(p471, valid_t471())
    write_json(p472, valid_t472())
    write_json(p473, valid_t473())
    with open(p474, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_phase_control_report(load_json(p471), load_json(p472), load_json(p473), load_json(p474), p471, p472, p473, p474)
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p471 = str(tmp_path / "t471.json")
    p472 = str(tmp_path / "t472.json")
    p473 = str(tmp_path / "t473.json")
    p474 = str(tmp_path / "missing.json")
    write_json(p471, valid_t471())
    write_json(p472, valid_t472())
    write_json(p473, valid_t473())
    r = generate_phase_control_report(load_json(p471), load_json(p472), load_json(p473), load_json(p474), p471, p472, p473, p474)
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p471 = str(tmp_path / "t471.json")
    p472 = str(tmp_path / "t472.json")
    p473 = str(tmp_path / "t473.json")
    p474 = str(tmp_path / "t474.json")
    out = str(tmp_path / "out.json")
    write_json(p471, valid_t471())
    write_json(p472, valid_t472())
    write_json(p473, valid_t473())
    write_json(p474, valid_t474())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_iteration_review_phase_control_report_v1.py"),
        "--iteration-review-packet", p471,
        "--blocker-analysis-report", p472,
        "--iteration-plan", p473,
        "--approval-artifact", p474,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
