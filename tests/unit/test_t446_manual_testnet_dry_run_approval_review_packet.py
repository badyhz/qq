import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_manual_testnet_dry_run_approval_review_packet_v1 import (
    CHECKLIST_ITEMS,
    REQUIRED_BLOCKED_ACTIONS,
    generate_review_packet,
    load_json,
    write_json,
)


def create_ready_t445() -> dict:
    return {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW",
        "final_decision": "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW",
    }


def test_ready_t445_pass(tmp_path):
    t445 = create_ready_t445()
    t445_path = str(tmp_path / "t445.json")
    write_json(t445_path, t445)

    report = generate_review_packet(t445, t445_path)

    assert report["ok"] is True
    assert report["review_packet_status"] == "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST"
    assert report["required_manual_decision"] == "APPROVE_OR_REJECT_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"
    assert report["final_decision"] == "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST"


def test_blocked_t445(tmp_path):
    t445 = create_ready_t445()
    t445["ok"] = False
    t445_path = str(tmp_path / "t445.json")
    write_json(t445_path, t445)

    report = generate_review_packet(t445, t445_path)

    assert report["ok"] is False
    assert report["review_packet_status"] == "BLOCKED"
    assert report["final_decision"] == "CONTINUE_TESTNET_DRY_RUN_READINESS_REVIEW"


def test_checklist_items_present(tmp_path):
    t445 = create_ready_t445()
    t445_path = str(tmp_path / "t445.json")
    write_json(t445_path, t445)

    report = generate_review_packet(t445, t445_path)
    for item in CHECKLIST_ITEMS:
        assert item in report["checklist_items"]


def test_safety_invariants(tmp_path):
    t445 = create_ready_t445()
    t445_path = str(tmp_path / "t445.json")
    write_json(t445_path, t445)

    report = generate_review_packet(t445, t445_path)

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
    t445_path = str(tmp_path / "t445.json")
    with open(t445_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_review_packet(load_json(t445_path), t445_path)
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t445_path = str(tmp_path / "missing_t445.json")
    report = generate_review_packet(load_json(t445_path), t445_path)
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t445_path = str(tmp_path / "t445.json")
    output_path = str(tmp_path / "out.json")
    write_json(t445_path, create_ready_t445())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "generate_manual_testnet_dry_run_approval_review_packet_v1.py"
            ),
            "--readiness-phase-report",
            t445_path,
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
