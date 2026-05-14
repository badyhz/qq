import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_testnet_dry_run_only_execution_result_report_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    generate_execution_result_report,
    load_json,
    write_json,
)


def valid_t462() -> dict:
    return {
        "ok": True,
        "materialization_status": "NO_SUBMIT_PAYLOAD_MATERIALIZED",
        "final_decision": "READY_FOR_TESTNET_DRY_RUN_ONLY_EXECUTION_RESULT_REPORT",
        "materialized_payload": {
            "dry_run_only": True,
            "artifact_only": True,
            "exchange_api_call_attempted": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
    }


def test_valid_materialized_payload_pass(tmp_path):
    report = generate_execution_result_report(valid_t462())
    assert report["ok"] is True
    assert report["execution_result_status"] == "TESTNET_DRY_RUN_ONLY_EXECUTION_REPORTED"
    assert report["simulated_execution_summary"]["status"] == "ARTIFACT_ONLY_NO_SUBMIT_COMPLETED"


def test_t462_blocked_fail(tmp_path):
    t462 = valid_t462()
    t462["ok"] = False
    report = generate_execution_result_report(t462)
    assert report["ok"] is False


def test_dry_run_only_false_fail(tmp_path):
    t462 = valid_t462()
    t462["materialized_payload"]["dry_run_only"] = False
    report = generate_execution_result_report(t462)
    assert report["ok"] is False


def test_artifact_only_false_fail(tmp_path):
    t462 = valid_t462()
    t462["materialized_payload"]["artifact_only"] = False
    report = generate_execution_result_report(t462)
    assert report["ok"] is False


def test_submit_attempted_true_fail(tmp_path):
    t462 = valid_t462()
    t462["materialized_payload"]["submit_attempted"] = True
    report = generate_execution_result_report(t462)
    assert report["ok"] is False


def test_never_allows_blocked_actions(tmp_path):
    report = generate_execution_result_report(valid_t462())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in report["allowed_actions"]
        assert b in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p = str(tmp_path / "bad.json")
    with open(p, "w", encoding="utf-8") as f:
        f.write("invalid json")
    report = generate_execution_result_report(load_json(p))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p = str(tmp_path / "missing.json")
    report = generate_execution_result_report(load_json(p))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p = str(tmp_path / "t462.json")
    out = str(tmp_path / "out.json")
    write_json(p, valid_t462())
    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_testnet_dry_run_only_execution_result_report_v1.py"),
            "--materialized-payload",
            p,
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
