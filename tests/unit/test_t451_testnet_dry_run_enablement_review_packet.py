import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_enablement_review_packet_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    REQUIRED_ENABLEMENT_ITEMS,
    generate_enablement_review_packet,
    load_json,
    write_json,
)


def create_ready_t450() -> dict:
    return {
        "ok": True,
        "phase_completion_status": "COMPLETED_PENDING_TESTNET_DRY_RUN_ENABLEMENT_REVIEW",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_REVIEW",
    }


def test_ready_t450_pass(tmp_path):
    t450 = create_ready_t450()
    t450_path = str(tmp_path / "t450.json")
    write_json(t450_path, t450)

    report = generate_enablement_review_packet(t450, t450_path)

    assert report["ok"] is True
    assert report["enablement_packet_status"] == "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_SAFETY_SWITCH_REVIEW"
    assert report["enablement_scope"] == "REVIEW_TESTNET_DRY_RUN_ONLY_MODE_ENABLEMENT"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_SAFETY_SWITCH_REVIEW"


def test_blocked_t450(tmp_path):
    t450 = create_ready_t450()
    t450["ok"] = False
    t450_path = str(tmp_path / "t450.json")
    write_json(t450_path, t450)

    report = generate_enablement_review_packet(t450, t450_path)

    assert report["ok"] is False
    assert report["enablement_packet_status"] == "BLOCKED"
    assert report["final_decision"] == "CONTINUE_MANUAL_TESTNET_DRY_RUN_APPROVAL_REVIEW"


def test_required_items_present(tmp_path):
    t450_path = str(tmp_path / "t450.json")
    write_json(t450_path, create_ready_t450())

    report = generate_enablement_review_packet(load_json(t450_path), t450_path)
    for item in REQUIRED_ENABLEMENT_ITEMS:
        assert item in report["required_enablement_items"]


def test_safety_invariants(tmp_path):
    t450_path = str(tmp_path / "t450.json")
    write_json(t450_path, create_ready_t450())

    report = generate_enablement_review_packet(load_json(t450_path), t450_path)

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
    t450_path = str(tmp_path / "t450.json")
    with open(t450_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_enablement_review_packet(load_json(t450_path), t450_path)
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t450_path = str(tmp_path / "missing_t450.json")
    report = generate_enablement_review_packet(load_json(t450_path), t450_path)
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t450_path = str(tmp_path / "t450.json")
    output_path = str(tmp_path / "out.json")
    write_json(t450_path, create_ready_t450())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "generate_testnet_dry_run_enablement_review_packet_v1.py"
            ),
            "--manual-approval-phase-report",
            t450_path,
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
