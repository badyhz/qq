import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_operator_confirmation_artifact_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    REQUIRED_CONFIRMATIONS,
    generate_operator_confirmation_artifact,
    load_json,
    write_json,
)


def valid_t452() -> dict:
    return {"ok": True}


def valid_confirmation(confirmed=True) -> dict:
    return {
        "operator": "op",
        "confirmed": confirmed,
        "confirmations": {item: True for item in REQUIRED_CONFIRMATIONS},
        "notes": "ok",
    }


def test_confirmed_all_true_pass(tmp_path):
    report = generate_operator_confirmation_artifact(valid_t452(), valid_confirmation(True))

    assert report["ok"] is True
    assert report["operator_confirmation_status"] == "TESTNET_DRY_RUN_OPERATOR_CONFIRMED"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_FINAL_GATE"


def test_confirmed_false_fail(tmp_path):
    report = generate_operator_confirmation_artifact(valid_t452(), valid_confirmation(False))
    assert report["ok"] is False


def test_missing_item_fail(tmp_path):
    c = valid_confirmation(True)
    c["confirmations"].pop(REQUIRED_CONFIRMATIONS[0])
    report = generate_operator_confirmation_artifact(valid_t452(), c)
    assert report["ok"] is False
    assert REQUIRED_CONFIRMATIONS[0] in report["missing_items"]


def test_one_false_item_fail(tmp_path):
    c = valid_confirmation(True)
    c["confirmations"][REQUIRED_CONFIRMATIONS[1]] = False
    report = generate_operator_confirmation_artifact(valid_t452(), c)
    assert report["ok"] is False
    assert REQUIRED_CONFIRMATIONS[1] in report["failed_items"]


def test_t452_blocked_fail(tmp_path):
    report = generate_operator_confirmation_artifact({"ok": False}, valid_confirmation(True))
    assert report["ok"] is False


def test_safety_invariants(tmp_path):
    report = generate_operator_confirmation_artifact(valid_t452(), valid_confirmation(True))

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
    t452_path = str(tmp_path / "t452.json")
    op_path = str(tmp_path / "op.json")
    write_json(t452_path, valid_t452())
    with open(op_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_operator_confirmation_artifact(load_json(t452_path), load_json(op_path))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t452_path = str(tmp_path / "t452.json")
    missing_op_path = str(tmp_path / "missing_op.json")
    write_json(t452_path, valid_t452())

    report = generate_operator_confirmation_artifact(load_json(t452_path), load_json(missing_op_path))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t452_path = str(tmp_path / "t452.json")
    op_path = str(tmp_path / "op.json")
    output_path = str(tmp_path / "out.json")
    write_json(t452_path, valid_t452())
    write_json(op_path, valid_confirmation(True))

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "generate_testnet_dry_run_operator_confirmation_artifact_v1.py"
            ),
            "--safety-switch-report",
            t452_path,
            "--operator-confirmation",
            op_path,
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
