import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.interpret_manual_testnet_dry_run_approval_checklist_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    REQUIRED_CHECKLIST_ITEMS,
    interpret_checklist,
    load_json,
    write_json,
)


def create_valid_t446() -> dict:
    return {
        "ok": True,
        "final_decision": "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST",
    }


def create_checklist_result(approved=True) -> dict:
    return {
        "reviewer": "operator",
        "approved": approved,
        "checklist": {item: True for item in REQUIRED_CHECKLIST_ITEMS},
        "notes": "ok",
    }


def test_approved_all_true_pass(tmp_path):
    t446 = create_valid_t446()
    checklist = create_checklist_result(True)

    report = interpret_checklist(t446, checklist)

    assert report["ok"] is True
    assert report["checklist_status"] == "MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST_APPROVED"
    assert report["final_decision"] == "READY_FOR_MANUAL_TESTNET_DRY_RUN_APPROVAL_ARTIFACT"


def test_approved_false_reject(tmp_path):
    report = interpret_checklist(create_valid_t446(), create_checklist_result(False))
    assert report["ok"] is False
    assert report["checklist_status"] == "MANUAL_TESTNET_DRY_RUN_APPROVAL_CHECKLIST_REJECTED_OR_INCOMPLETE"


def test_missing_item_fail(tmp_path):
    checklist = create_checklist_result(True)
    checklist["checklist"].pop(REQUIRED_CHECKLIST_ITEMS[0])
    report = interpret_checklist(create_valid_t446(), checklist)
    assert report["ok"] is False
    assert REQUIRED_CHECKLIST_ITEMS[0] in report["missing_items"]


def test_one_false_item_fail(tmp_path):
    checklist = create_checklist_result(True)
    checklist["checklist"][REQUIRED_CHECKLIST_ITEMS[1]] = False
    report = interpret_checklist(create_valid_t446(), checklist)
    assert report["ok"] is False
    assert REQUIRED_CHECKLIST_ITEMS[1] in report["failed_items"]


def test_t446_blocked_fail(tmp_path):
    t446 = create_valid_t446()
    t446["ok"] = False
    report = interpret_checklist(t446, create_checklist_result(True))
    assert report["ok"] is False


def test_safety_invariants(tmp_path):
    report = interpret_checklist(create_valid_t446(), create_checklist_result(True))

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
    checklist_path = str(tmp_path / "checklist.json")
    write_json(t446_path, create_valid_t446())
    with open(checklist_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = interpret_checklist(load_json(t446_path), load_json(checklist_path))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t446_path = str(tmp_path / "t446.json")
    missing_checklist_path = str(tmp_path / "missing_checklist.json")
    write_json(t446_path, create_valid_t446())

    report = interpret_checklist(load_json(t446_path), load_json(missing_checklist_path))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t446_path = str(tmp_path / "t446.json")
    checklist_path = str(tmp_path / "checklist.json")
    output_path = str(tmp_path / "out.json")

    write_json(t446_path, create_valid_t446())
    write_json(checklist_path, create_checklist_result(True))

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "interpret_manual_testnet_dry_run_approval_checklist_v1.py"
            ),
            "--review-packet",
            t446_path,
            "--checklist-result",
            checklist_path,
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
