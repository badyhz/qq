import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_next_testnet_dry_run_only_iteration_phase_control_report_v1 import (
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
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY", "MATERIALIZE_PAYLOAD_ARTIFACT", "GENERATE_NEXT_DRY_RUN_ARTIFACT"]


def blocked():
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t476():
    return {"final_decision": "READY_FOR_NEXT_DRY_RUN_CANDIDATE_INPUT_ARTIFACT", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t477():
    return {"final_decision": "READY_FOR_NEXT_NO_SUBMIT_PAYLOAD_PLAN", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t478():
    return {"final_decision": "READY_FOR_NEXT_ARTIFACT_ONLY_MATERIALIZATION_REPORT", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def valid_t479():
    return {"final_decision": "READY_FOR_NEXT_DRY_RUN_ONLY_ITERATION_PHASE_CONTROL", "safety_flags": safe_flags(), "allowed_actions": allowed(), "blocked_actions": blocked()}


def run_report(t476, t477, t478, t479, tmp_path):
    p476 = str(tmp_path / "t476.json")
    p477 = str(tmp_path / "t477.json")
    p478 = str(tmp_path / "t478.json")
    p479 = str(tmp_path / "t479.json")
    write_json(p476, t476)
    write_json(p477, t477)
    write_json(p478, t478)
    write_json(p479, t479)
    return generate_phase_control_report(t476, t477, t478, t479, p476, p477, p478, p479)


def test_all_pass_ready_for_next_result_review(tmp_path):
    r = run_report(valid_t476(), valid_t477(), valid_t478(), valid_t479(), tmp_path)
    assert r["ok"] is True
    assert r["final_decision"] == "READY_FOR_NEXT_TESTNET_DRY_RUN_RESULT_REVIEW"


def test_each_component_fail_exact_blocker(tmp_path):
    t476 = valid_t476(); t476["final_decision"] = "BAD"
    r = run_report(t476, valid_t477(), valid_t478(), valid_t479(), tmp_path)
    assert "T476_EXECUTION_PACKET_NOT_READY" in r["blockers"]

    t477 = valid_t477(); t477["final_decision"] = "BAD"
    r = run_report(valid_t476(), t477, valid_t478(), valid_t479(), tmp_path)
    assert "T477_CANDIDATE_ARTIFACT_NOT_READY" in r["blockers"]

    t478 = valid_t478(); t478["final_decision"] = "BAD"
    r = run_report(valid_t476(), valid_t477(), t478, valid_t479(), tmp_path)
    assert "T478_PAYLOAD_PLAN_NOT_READY" in r["blockers"]

    t479 = valid_t479(); t479["final_decision"] = "BAD"
    r = run_report(valid_t476(), valid_t477(), valid_t478(), t479, tmp_path)
    assert "T479_MATERIALIZATION_NOT_READY" in r["blockers"]


def test_exchange_submit_cancel_flatten_violation_blocker(tmp_path):
    t479 = valid_t479(); t479["safety_flags"]["exchange_api_calls_allowed"] = True
    r = run_report(valid_t476(), valid_t477(), valid_t478(), t479, tmp_path)
    assert "NO_SUBMIT_NO_EXCHANGE_BLOCK_NOT_CONFIRMED" in r["blockers"]


def test_allowed_actions_never_contains_blocked(tmp_path):
    r = run_report(valid_t476(), valid_t477(), valid_t478(), valid_t479(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in r["allowed_actions"]


def test_blocked_actions_include_all(tmp_path):
    r = run_report(valid_t476(), valid_t477(), valid_t478(), valid_t479(), tmp_path)
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b in r["blocked_actions"]


def test_invalid_json(tmp_path):
    p476 = str(tmp_path / "t476.json")
    p477 = str(tmp_path / "t477.json")
    p478 = str(tmp_path / "t478.json")
    p479 = str(tmp_path / "t479.json")
    write_json(p476, valid_t476())
    write_json(p477, valid_t477())
    write_json(p478, valid_t478())
    with open(p479, "w", encoding="utf-8") as f:
        f.write("bad")
    r = generate_phase_control_report(load_json(p476), load_json(p477), load_json(p478), load_json(p479), p476, p477, p478, p479)
    assert r["ok"] is False


def test_missing_file(tmp_path):
    p476 = str(tmp_path / "t476.json")
    p477 = str(tmp_path / "t477.json")
    p478 = str(tmp_path / "t478.json")
    p479 = str(tmp_path / "missing.json")
    write_json(p476, valid_t476())
    write_json(p477, valid_t477())
    write_json(p478, valid_t478())
    r = generate_phase_control_report(load_json(p476), load_json(p477), load_json(p478), load_json(p479), p476, p477, p478, p479)
    assert r["ok"] is False


def test_cli_smoke(tmp_path):
    p476 = str(tmp_path / "t476.json")
    p477 = str(tmp_path / "t477.json")
    p478 = str(tmp_path / "t478.json")
    p479 = str(tmp_path / "t479.json")
    out = str(tmp_path / "out.json")
    write_json(p476, valid_t476())
    write_json(p477, valid_t477())
    write_json(p478, valid_t478())
    write_json(p479, valid_t479())
    proc = subprocess.Popen([
        sys.executable,
        str(Path(__file__).parent.parent.parent / "scripts" / "generate_next_testnet_dry_run_only_iteration_phase_control_report_v1.py"),
        "--execution-packet", p476,
        "--candidate-artifact", p477,
        "--payload-plan", p478,
        "--materialization-report", p479,
        "--output", out,
        "--json",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
