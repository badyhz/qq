import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_manual_testnet_dry_run_final_gate_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_final_gate_report,
    load_json,
    write_json,
)


def create_approved_t448() -> dict:
    return {
        "ok": True,
        "approval_status": "MANUAL_TESTNET_DRY_RUN_APPROVED_FOR_ENABLEMENT_REVIEW",
        "final_decision": "READY_FOR_MANUAL_TESTNET_DRY_RUN_FINAL_GATE",
    }


def test_approved_artifact_ready_for_enablement_review(tmp_path):
    report = generate_final_gate_report(create_approved_t448())

    assert report["ok"] is True
    assert report["final_gate_status"] == "MANUAL_TESTNET_DRY_RUN_FINAL_GATE_PASSED"
    assert report["gate_result"] == "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"


def test_blocked_artifact_blocked(tmp_path):
    t448 = create_approved_t448()
    t448["ok"] = False
    report = generate_final_gate_report(t448)

    assert report["ok"] is False
    assert report["final_gate_status"] == "BLOCKED"
    assert report["final_decision"] == "CONTINUE_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"


def test_never_allows_testnet_dry_run_only(tmp_path):
    report = generate_final_gate_report(create_approved_t448())

    assert "READY_FOR_TESTNET_DRY_RUN_ONLY" not in report["final_decision"]
    assert "TESTNET_DRY_RUN_ONLY" not in report["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" in report["blocked_actions"]


def test_safety_invariants(tmp_path):
    report = generate_final_gate_report(create_approved_t448())

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
    t448_path = str(tmp_path / "t448.json")
    with open(t448_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_final_gate_report(load_json(t448_path))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t448_path = str(tmp_path / "missing_t448.json")
    report = generate_final_gate_report(load_json(t448_path))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t448_path = str(tmp_path / "t448.json")
    output_path = str(tmp_path / "out.json")

    write_json(t448_path, create_approved_t448())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "generate_manual_testnet_dry_run_final_gate_report_v1.py"
            ),
            "--approval-artifact",
            t448_path,
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
