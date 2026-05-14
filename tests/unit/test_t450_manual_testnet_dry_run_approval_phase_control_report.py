import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_manual_testnet_dry_run_approval_phase_control_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_phase_control_report,
    load_json,
    write_json,
)


def safety_flags() -> dict:
    return {
        "shadow_only": True,
        "testnet_dry_run_allowed": False,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_attempted": False,
        "cancel_attempted": False,
        "flatten_attempted": False,
    }


def create_valid_t446() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST",
        "safety_flags": safety_flags(),
        "allowed_actions": [],
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
    }


def create_valid_t447() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_ARTIFACT",
        "safety_flags": safety_flags(),
        "allowed_actions": [],
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
    }


def create_valid_t448() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_MANUAL_TESTNET_DRY_RUN_FINAL_GATE",
        "safety_flags": safety_flags(),
        "allowed_actions": [],
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
    }


def create_valid_t449() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_REVIEW",
        "safety_flags": safety_flags(),
        "allowed_actions": [],
        "blocked_actions": list(REQUIRED_BLOCKED_ACTIONS),
    }


def run_report(t446: dict, t447: dict, t448: dict, t449: dict, tmp_path):
    t446_path = str(tmp_path / "t446.json")
    t447_path = str(tmp_path / "t447.json")
    t448_path = str(tmp_path / "t448.json")
    t449_path = str(tmp_path / "t449.json")

    write_json(t446_path, t446)
    write_json(t447_path, t447)
    write_json(t448_path, t448)
    write_json(t449_path, t449)

    return generate_phase_control_report(
        t446,
        t447,
        t448,
        t449,
        t446_path,
        t447_path,
        t448_path,
        t449_path,
    )


def test_all_pass_ready_for_enablement_review(tmp_path):
    report = run_report(
        create_valid_t446(), create_valid_t447(), create_valid_t448(), create_valid_t449(), tmp_path
    )

    assert report["ok"] is True
    assert report["phase_completion_status"] == "COMPLETED_PENDING_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
    assert report["next_phase"] == "TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"


def test_t446_fail_exact_blocker(tmp_path):
    t446 = create_valid_t446()
    t446["ok"] = False
    report = run_report(t446, create_valid_t447(), create_valid_t448(), create_valid_t449(), tmp_path)
    assert report["ok"] is False
    assert "T446_REVIEW_PACKET_NOT_READY" in report["blockers"]


def test_t447_fail_exact_blocker(tmp_path):
    t447 = create_valid_t447()
    t447["ok"] = False
    report = run_report(create_valid_t446(), t447, create_valid_t448(), create_valid_t449(), tmp_path)
    assert report["ok"] is False
    assert "T447_CHECKLIST_NOT_APPROVED" in report["blockers"]


def test_t448_fail_exact_blocker(tmp_path):
    t448 = create_valid_t448()
    t448["ok"] = False
    report = run_report(create_valid_t446(), create_valid_t447(), t448, create_valid_t449(), tmp_path)
    assert report["ok"] is False
    assert "T448_APPROVAL_ARTIFACT_NOT_READY" in report["blockers"]


def test_t449_fail_exact_blocker(tmp_path):
    t449 = create_valid_t449()
    t449["ok"] = False
    report = run_report(create_valid_t446(), create_valid_t447(), create_valid_t448(), t449, tmp_path)
    assert report["ok"] is False
    assert "T449_FINAL_GATE_NOT_PASSED" in report["blockers"]


def test_execution_violation_blocker(tmp_path):
    t449 = create_valid_t449()
    t449["safety_flags"]["submit_attempted"] = True
    report = run_report(create_valid_t446(), create_valid_t447(), create_valid_t448(), t449, tmp_path)
    assert report["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_allowed_contains_testnet_dry_run_only_blocker(tmp_path):
    t449 = create_valid_t449()
    t449["allowed_actions"].append("TESTNET_DRY_RUN_ONLY")
    report = run_report(create_valid_t446(), create_valid_t447(), create_valid_t448(), t449, tmp_path)
    assert report["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_blocked_missing_flatten_position_blocker(tmp_path):
    t449 = create_valid_t449()
    t449["blocked_actions"].remove("FLATTEN_POSITION")
    report = run_report(create_valid_t446(), create_valid_t447(), create_valid_t448(), t449, tmp_path)
    assert report["ok"] is False
    assert "EXECUTION_BLOCK_NOT_CONFIRMED" in report["blockers"]


def test_output_safety_invariants(tmp_path):
    report = run_report(
        create_valid_t446(), create_valid_t447(), create_valid_t448(), create_valid_t449(), tmp_path
    )

    assert report["safety_flags"]["testnet_dry_run_allowed"] is False
    assert report["safety_flags"]["testnet_submit_allowed"] is False
    assert report["safety_flags"]["real_submit_allowed"] is False
    assert report["safety_flags"]["submit_attempted"] is False
    assert report["safety_flags"]["cancel_attempted"] is False
    assert report["safety_flags"]["flatten_attempted"] is False

    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]
        assert blocked in report["blocked_actions"]


def test_invalid_json(tmp_path):
    t446_path = str(tmp_path / "t446.json")
    t447_path = str(tmp_path / "t447.json")
    t448_path = str(tmp_path / "t448.json")
    t449_path = str(tmp_path / "t449.json")

    write_json(t446_path, create_valid_t446())
    write_json(t447_path, create_valid_t447())
    write_json(t448_path, create_valid_t448())
    with open(t449_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_phase_control_report(
        load_json(t446_path),
        load_json(t447_path),
        load_json(t448_path),
        load_json(t449_path),
        t446_path,
        t447_path,
        t448_path,
        t449_path,
    )
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t446_path = str(tmp_path / "t446.json")
    t447_path = str(tmp_path / "t447.json")
    t448_path = str(tmp_path / "t448.json")
    missing_t449_path = str(tmp_path / "missing_t449.json")

    write_json(t446_path, create_valid_t446())
    write_json(t447_path, create_valid_t447())
    write_json(t448_path, create_valid_t448())

    report = generate_phase_control_report(
        load_json(t446_path),
        load_json(t447_path),
        load_json(t448_path),
        load_json(missing_t449_path),
        t446_path,
        t447_path,
        t448_path,
        missing_t449_path,
    )
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t446_path = str(tmp_path / "t446.json")
    t447_path = str(tmp_path / "t447.json")
    t448_path = str(tmp_path / "t448.json")
    t449_path = str(tmp_path / "t449.json")
    output_path = str(tmp_path / "out.json")

    write_json(t446_path, create_valid_t446())
    write_json(t447_path, create_valid_t447())
    write_json(t448_path, create_valid_t448())
    write_json(t449_path, create_valid_t449())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "generate_manual_testnet_dry_run_approval_phase_control_report_v1.py"
            ),
            "--review-packet",
            t446_path,
            "--checklist-interpretation",
            t447_path,
            "--approval-artifact",
            t448_path,
            "--final-gate-report",
            t449_path,
            "--output",
            output_path,
            "--json",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()

    assert proc.returncode in [0, 1]
    assert os.path.exists(output_path)
