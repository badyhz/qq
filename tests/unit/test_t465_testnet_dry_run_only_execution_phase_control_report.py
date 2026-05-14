import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_only_execution_phase_control_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_phase_control_report,
    load_json,
    write_json,
)


def flags() -> dict:
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


def allowed() -> list:
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "MATERIALIZE_PAYLOAD_ARTIFACT"]


def blocked() -> list:
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t461() -> dict:
    return {"final_decision": "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_MATERIALIZATION", "safety_flags": flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t462() -> dict:
    return {"final_decision": "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION_RESULT_REPORT", "safety_flags": flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t463() -> dict:
    return {"final_decision": "READY_FOR_TESTNET_DRY_RUN_ONLY_ARTIFACT_VERIFICATION", "safety_flags": flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t464() -> dict:
    return {"final_decision": "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION_PHASE_CONTROL", "safety_flags": flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def run_report(t461, t462, t463, t464, tmp_path):
    p461 = str(tmp_path / "t461.json")
    p462 = str(tmp_path / "t462.json")
    p463 = str(tmp_path / "t463.json")
    p464 = str(tmp_path / "t464.json")
    write_json(p461, t461)
    write_json(p462, t462)
    write_json(p463, t463)
    write_json(p464, t464)
    return generate_phase_control_report(t461, t462, t463, t464, p461, p462, p463, p464)


def test_all_pass_ready_for_result_review(tmp_path):
    report = run_report(valid_t461(), valid_t462(), valid_t463(), valid_t464(), tmp_path)
    assert report["ok"] is True
    assert report["phase_completion_status"] == "COMPLETED_TESTNET_DRY_RUN_ONLY_EXECUTION"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_RESULT_REVIEW"


def test_each_component_fail_exact_blocker(tmp_path):
    t461 = valid_t461(); t461["final_decision"] = "BAD"
    report = run_report(t461, valid_t462(), valid_t463(), valid_t464(), tmp_path)
    assert "T461_EXECUTION_PACKET_NOT_READY" in report["blockers"]

    t462 = valid_t462(); t462["final_decision"] = "BAD"
    report = run_report(valid_t461(), t462, valid_t463(), valid_t464(), tmp_path)
    assert "T462_PAYLOAD_MATERIALIZATION_NOT_READY" in report["blockers"]

    t463 = valid_t463(); t463["final_decision"] = "BAD"
    report = run_report(valid_t461(), valid_t462(), t463, valid_t464(), tmp_path)
    assert "T463_EXECUTION_RESULT_NOT_READY" in report["blockers"]

    t464 = valid_t464(); t464["final_decision"] = "BAD"
    report = run_report(valid_t461(), valid_t462(), valid_t463(), t464, tmp_path)
    assert "T464_ARTIFACT_VERIFICATION_NOT_READY" in report["blockers"]


def test_exchange_submit_cancel_flatten_violation_blocker(tmp_path):
    t464 = valid_t464()
    t464["safety_flags"]["exchange_api_calls_allowed"] = True
    report = run_report(valid_t461(), valid_t462(), valid_t463(), t464, tmp_path)
    assert report["ok"] is False
    assert "SUBMIT_CANCEL_FLATTEN_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_allowed_actions_never_contains_blocked(tmp_path):
    report = run_report(valid_t461(), valid_t462(), valid_t463(), valid_t464(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in report["allowed_actions"]


def test_blocked_actions_include_all(tmp_path):
    report = run_report(valid_t461(), valid_t462(), valid_t463(), valid_t464(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p461 = str(tmp_path / "t461.json")
    p462 = str(tmp_path / "t462.json")
    p463 = str(tmp_path / "t463.json")
    p464 = str(tmp_path / "t464.json")
    write_json(p461, valid_t461())
    write_json(p462, valid_t462())
    write_json(p463, valid_t463())
    with open(p464, "w", encoding="utf-8") as f:
        f.write("invalid json")
    report = generate_phase_control_report(load_json(p461), load_json(p462), load_json(p463), load_json(p464), p461, p462, p463, p464)
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p461 = str(tmp_path / "t461.json")
    p462 = str(tmp_path / "t462.json")
    p463 = str(tmp_path / "t463.json")
    p464 = str(tmp_path / "missing_t464.json")
    write_json(p461, valid_t461())
    write_json(p462, valid_t462())
    write_json(p463, valid_t463())
    report = generate_phase_control_report(load_json(p461), load_json(p462), load_json(p463), load_json(p464), p461, p462, p463, p464)
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p461 = str(tmp_path / "t461.json")
    p462 = str(tmp_path / "t462.json")
    p463 = str(tmp_path / "t463.json")
    p464 = str(tmp_path / "t464.json")
    out = str(tmp_path / "out.json")
    write_json(p461, valid_t461())
    write_json(p462, valid_t462())
    write_json(p463, valid_t463())
    write_json(p464, valid_t464())
    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_only_execution_phase_control_report_v1.py"),
            "--execution-packet", p461,
            "--materialized-payload", p462,
            "--execution-result-report", p463,
            "--artifact-verification-report", p464,
            "--output", out,
            "--json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
