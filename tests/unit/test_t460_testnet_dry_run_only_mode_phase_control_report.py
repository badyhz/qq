import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_only_mode_phase_control_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_phase_control_report,
    load_json,
    write_json,
)


def safety_flags() -> dict:
    return {
        "testnet_dry_run_allowed": True,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_order_allowed": False,
        "cancel_order_allowed": False,
        "flatten_position_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


def common_allowed() -> list:
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY"]


def common_blocked() -> list:
    return list(REQUIRED_BLOCKED_ACTIONS)


def valid_t456() -> dict:
    return {
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_PLAN",
        "safety_flags": safety_flags(),
        "allowed_actions": common_allowed(),
        "blocked_actions": common_blocked(),
    }


def valid_t457() -> dict:
    return {
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_RUNNER_GUARD",
        "safety_flags": safety_flags(),
        "allowed_actions": common_allowed(),
        "blocked_actions": common_blocked(),
    }


def valid_t458() -> dict:
    return {
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ONLY_PREFLIGHT_REPORT",
        "safety_flags": safety_flags(),
        "allowed_actions": common_allowed(),
        "blocked_actions": common_blocked(),
    }


def valid_t459() -> dict:
    return {
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ONLY_PHASE_CONTROL",
        "safety_flags": safety_flags(),
        "allowed_actions": common_allowed(),
        "blocked_actions": common_blocked(),
    }


def run_report(t456, t457, t458, t459, tmp_path):
    p456 = str(tmp_path / "t456.json")
    p457 = str(tmp_path / "t457.json")
    p458 = str(tmp_path / "t458.json")
    p459 = str(tmp_path / "t459.json")
    write_json(p456, t456)
    write_json(p457, t457)
    write_json(p458, t458)
    write_json(p459, t459)

    return generate_phase_control_report(t456, t457, t458, t459, p456, p457, p458, p459)


def test_all_pass_ready_for_execution(tmp_path):
    report = run_report(valid_t456(), valid_t457(), valid_t458(), valid_t459(), tmp_path)
    assert report["ok"] is True
    assert report["phase_completion_status"] == "COMPLETED_READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION"
    assert report["safety_flags"]["testnet_dry_run_allowed"] is True


def test_each_component_fail_exact_blocker(tmp_path):
    t456 = valid_t456()
    t456["final_decision"] = "BAD"
    report = run_report(t456, valid_t457(), valid_t458(), valid_t459(), tmp_path)
    assert "T456_MODE_PACKET_NOT_READY" in report["blockers"]

    t457 = valid_t457()
    t457["final_decision"] = "BAD"
    report = run_report(valid_t456(), t457, valid_t458(), valid_t459(), tmp_path)
    assert "T457_PAYLOAD_PLAN_NOT_READY" in report["blockers"]

    t458 = valid_t458()
    t458["final_decision"] = "BAD"
    report = run_report(valid_t456(), valid_t457(), t458, valid_t459(), tmp_path)
    assert "T458_RUNNER_GUARD_NOT_VERIFIED" in report["blockers"]

    t459 = valid_t459()
    t459["final_decision"] = "BAD"
    report = run_report(valid_t456(), valid_t457(), valid_t458(), t459, tmp_path)
    assert "T459_PREFLIGHT_NOT_PASSED" in report["blockers"]


def test_submit_cancel_flatten_violation_blocker(tmp_path):
    t459 = valid_t459()
    t459["safety_flags"]["cancel_attempted"] = True
    report = run_report(valid_t456(), valid_t457(), valid_t458(), t459, tmp_path)
    assert report["ok"] is False
    assert "SUBMIT_CANCEL_FLATTEN_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_allowed_actions_never_contains_submit_cancel_flatten(tmp_path):
    report = run_report(valid_t456(), valid_t457(), valid_t458(), valid_t459(), tmp_path)
    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]


def test_blocked_actions_include_all(tmp_path):
    report = run_report(valid_t456(), valid_t457(), valid_t458(), valid_t459(), tmp_path)
    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p456 = str(tmp_path / "t456.json")
    p457 = str(tmp_path / "t457.json")
    p458 = str(tmp_path / "t458.json")
    p459 = str(tmp_path / "t459.json")
    write_json(p456, valid_t456())
    write_json(p457, valid_t457())
    write_json(p458, valid_t458())
    with open(p459, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_phase_control_report(
        load_json(p456), load_json(p457), load_json(p458), load_json(p459), p456, p457, p458, p459
    )
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p456 = str(tmp_path / "t456.json")
    p457 = str(tmp_path / "t457.json")
    p458 = str(tmp_path / "t458.json")
    p459 = str(tmp_path / "missing_t459.json")
    write_json(p456, valid_t456())
    write_json(p457, valid_t457())
    write_json(p458, valid_t458())

    report = generate_phase_control_report(
        load_json(p456), load_json(p457), load_json(p458), load_json(p459), p456, p457, p458, p459
    )
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p456 = str(tmp_path / "t456.json")
    p457 = str(tmp_path / "t457.json")
    p458 = str(tmp_path / "t458.json")
    p459 = str(tmp_path / "t459.json")
    out = str(tmp_path / "out.json")

    write_json(p456, valid_t456())
    write_json(p457, valid_t457())
    write_json(p458, valid_t458())
    write_json(p459, valid_t459())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_only_mode_phase_control_report_v1.py"),
            "--mode-packet",
            p456,
            "--payload-plan",
            p457,
            "--runner-guard-report",
            p458,
            "--preflight-report",
            p459,
            "--output",
            out,
            "--json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()

    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
