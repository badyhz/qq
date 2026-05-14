import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_manual_testnet_dry_run_approval_artifact_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_approval_artifact,
    load_json,
    write_json,
)


def create_approved_t447() -> dict:
    return {
        "ok": True,
        "checklist_status": "MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST_APPROVED",
        "final_decision": "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_ARTIFACT",
    }


def test_approved_t447_pass(tmp_path):
    report = generate_approval_artifact(create_approved_t447())

    assert report["ok"] is True
    assert report["approval_status"] == "MANUAL_TESTNET_DRY_RUN_APPROVED_FOR_ENABLEMENT_REVIEW"
    assert report["final_decision"] == "READY_FOR_MANUAL_TESTNET_DRY_RUN_FINAL_GATE"


def test_rejected_t447_blocked(tmp_path):
    t447 = create_approved_t447()
    t447["ok"] = False
    report = generate_approval_artifact(t447)

    assert report["ok"] is False
    assert report["approval_status"] == "BLOCKED"
    assert report["final_decision"] == "CONTINUE_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"


def test_approval_scope_enablement_review_only(tmp_path):
    report = generate_approval_artifact(create_approved_t447())
    assert report["approval_scope"] == "APPROVE_TESTNET_DRY_RUN_ENABLEMENT_REVIEW_ONLY"


def test_testnet_dry_run_only_still_blocked(tmp_path):
    report = generate_approval_artifact(create_approved_t447())
    assert "TESTNET_DRY_RUN_ONLY" not in report["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" in report["blocked_actions"]


def test_invalid_json(tmp_path):
    t447_path = str(tmp_path / "t447.json")
    with open(t447_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_approval_artifact(load_json(t447_path))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t447_path = str(tmp_path / "missing_t447.json")
    report = generate_approval_artifact(load_json(t447_path))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t447_path = str(tmp_path / "t447.json")
    output_path = str(tmp_path / "out.json")
    write_json(t447_path, create_approved_t447())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "generate_manual_testnet_dry_run_approval_artifact_v1.py"
            ),
            "--checklist-interpretation",
            t447_path,
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


def test_safety_invariants(tmp_path):
    report = generate_approval_artifact(create_approved_t447())
    assert report["safety_flags"]["submit_attempted"] is False
    assert report["safety_flags"]["cancel_attempted"] is False
    assert report["safety_flags"]["flatten_attempted"] is False

    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]
        assert blocked in report["blocked_actions"]
