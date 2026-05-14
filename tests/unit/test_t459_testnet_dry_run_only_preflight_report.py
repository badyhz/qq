import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_only_preflight_report_v1 import (
    PREFLIGHT_ITEMS,
    generate_preflight_report,
    load_json,
    write_json,
)


def flags(blocked=False):
    return {
        "testnet_dry_run_allowed": not blocked,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_order_allowed": False,
        "cancel_order_allowed": False,
        "flatten_position_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


def actions():
    return ["READ_REPORTS", "TESTNET_DRY_RUN_ONLY"]


def blocked_actions():
    return ["TESTNET_SUBMIT", "REAL_SUBMIT", "SUBMIT_ORDER", "CANCEL_ORDER", "FLATTEN_POSITION"]


def valid_t456() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_PAYLOAD_PLAN",
        "safety_flags": flags(),
        "allowed_actions": actions(),
        "blocked_actions": blocked_actions(),
    }


def valid_t457() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_NO_SUBMIT_RUNNER_GUARD",
        "safety_flags": flags(),
        "allowed_actions": actions(),
        "blocked_actions": blocked_actions(),
    }


def valid_t458() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ONLY_PREFLIGHT_REPORT",
        "safety_flags": flags(),
        "allowed_actions": actions(),
        "blocked_actions": blocked_actions(),
    }


def test_all_pass_preflight_passed(tmp_path):
    report = generate_preflight_report(valid_t456(), valid_t457(), valid_t458())
    assert report["ok"] is True
    assert report["preflight_status"] == "TESTNET_DRY_RUN_ONLY_PREFLIGHT_PASSED"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ONLY_PHASE_CONTROL"


def test_each_component_fail_exact_blocker(tmp_path):
    t456 = valid_t456()
    t456["ok"] = False
    report = generate_preflight_report(t456, valid_t457(), valid_t458())
    assert "T456_MODE_PACKET_NOT_READY" in report["blockers"]

    t457 = valid_t457()
    t457["ok"] = False
    report = generate_preflight_report(valid_t456(), t457, valid_t458())
    assert "T457_PAYLOAD_PLAN_NOT_READY" in report["blockers"]

    t458 = valid_t458()
    t458["ok"] = False
    report = generate_preflight_report(valid_t456(), valid_t457(), t458)
    assert "T458_RUNNER_GUARD_NOT_VERIFIED" in report["blockers"]


def test_submit_cancel_flatten_violation_blocker(tmp_path):
    t458 = valid_t458()
    t458["safety_flags"]["submit_attempted"] = True
    report = generate_preflight_report(valid_t456(), valid_t457(), t458)
    assert report["ok"] is False
    assert "SUBMIT_CANCEL_FLATTEN_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_preflight_items_present(tmp_path):
    report = generate_preflight_report(valid_t456(), valid_t457(), valid_t458())
    for item in PREFLIGHT_ITEMS:
        assert item in report["preflight_items"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t456.json")
    p2 = str(tmp_path / "t457.json")
    p3 = str(tmp_path / "t458.json")

    write_json(p1, valid_t456())
    write_json(p2, valid_t457())
    with open(p3, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_preflight_report(load_json(p1), load_json(p2), load_json(p3))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t456.json")
    p2 = str(tmp_path / "t457.json")
    p3 = str(tmp_path / "missing_t458.json")

    write_json(p1, valid_t456())
    write_json(p2, valid_t457())

    report = generate_preflight_report(load_json(p1), load_json(p2), load_json(p3))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t456.json")
    p2 = str(tmp_path / "t457.json")
    p3 = str(tmp_path / "t458.json")
    out = str(tmp_path / "out.json")

    write_json(p1, valid_t456())
    write_json(p2, valid_t457())
    write_json(p3, valid_t458())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_only_preflight_report_v1.py"),
            "--mode-packet",
            p1,
            "--payload-plan",
            p2,
            "--runner-guard-report",
            p3,
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
