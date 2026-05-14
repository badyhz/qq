import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_enablement_final_gate_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_enablement_final_gate_report,
    load_json,
    write_json,
)


def valid_t453() -> dict:
    return {
        "ok": True,
        "operator_confirmation_status": "TESTNET_DRY_RUN_OPERATOR_CONFIRMED",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ENABLEMENT_FINAL_GATE",
    }


def test_confirmed_t453_pass(tmp_path):
    report = generate_enablement_final_gate_report(valid_t453())

    assert report["ok"] is True
    assert report["final_gate_status"] == "TESTNET_DRY_RUN_ENABLEMENT_FINAL_GATE_PASSED"
    assert report["gate_result"] == "READY_FOR_TESTNET_DRY_RUN_ONLY_MODE"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ONLY_MODE"


def test_blocked_t453_blocked(tmp_path):
    t453 = valid_t453()
    t453["ok"] = False
    report = generate_enablement_final_gate_report(t453)

    assert report["ok"] is False
    assert report["final_gate_status"] == "BLOCKED"
    assert report["final_decision"] == "CONTINUE_TESTNET_DRY_RUN_ENABLEMENT_REVIEW"


def test_never_allows_submit_cancel_flatten(tmp_path):
    report = generate_enablement_final_gate_report(valid_t453())
    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]
        assert blocked in report["blocked_actions"]


def test_safety_invariants(tmp_path):
    report = generate_enablement_final_gate_report(valid_t453())

    assert report["safety_flags"]["testnet_dry_run_allowed"] is False
    assert report["safety_flags"]["testnet_submit_allowed"] is False
    assert report["safety_flags"]["real_submit_allowed"] is False
    assert report["safety_flags"]["submit_attempted"] is False
    assert report["safety_flags"]["cancel_attempted"] is False
    assert report["safety_flags"]["flatten_attempted"] is False


def test_invalid_json(tmp_path):
    t453_path = str(tmp_path / "t453.json")
    with open(t453_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = generate_enablement_final_gate_report(load_json(t453_path))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t453_path = str(tmp_path / "missing_t453.json")
    report = generate_enablement_final_gate_report(load_json(t453_path))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t453_path = str(tmp_path / "t453.json")
    output_path = str(tmp_path / "out.json")
    write_json(t453_path, valid_t453())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "generate_testnet_dry_run_enablement_final_gate_report_v1.py"
            ),
            "--operator-confirmation-artifact",
            t453_path,
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
