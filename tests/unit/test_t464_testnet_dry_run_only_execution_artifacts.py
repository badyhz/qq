import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_testnet_dry_run_only_execution_artifacts_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    load_json,
    verify_execution_artifacts,
    write_json,
)


def valid_t462() -> dict:
    return {
        "ok": True,
        "materialization_status": "NO_SUBMIT_PAYLOAD_MATERIALIZED",
        "payload_digest": "abc123",
        "materialized_payload": {
            "exchange_api_call_attempted": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
    }


def valid_t463() -> dict:
    return {
        "ok": True,
        "execution_result_status": "TESTNET_DRY_RUN_ONLY_EXECUTION_REPORTED",
        "simulated_execution_summary": {
            "status": "ARTIFACT_ONLY_NO_SUBMIT_COMPLETED",
            "exchange_api_call_attempted": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        },
    }


def test_valid_t462_t463_pass(tmp_path):
    report = verify_execution_artifacts(valid_t462(), valid_t463())
    assert report["ok"] is True
    assert report["artifact_verification_status"] == "TESTNET_DRY_RUN_ONLY_ARTIFACTS_VERIFIED"


def test_missing_digest_fail(tmp_path):
    t462 = valid_t462()
    t462["payload_digest"] = ""
    report = verify_execution_artifacts(t462, valid_t463())
    assert report["ok"] is False
    assert "PAYLOAD_DIGEST_MISSING" in report["violations"]


def test_t462_blocked_fail(tmp_path):
    t462 = valid_t462()
    t462["ok"] = False
    report = verify_execution_artifacts(t462, valid_t463())
    assert report["ok"] is False
    assert "MATERIALIZED_PAYLOAD_NOT_READY" in report["violations"]


def test_t463_blocked_fail(tmp_path):
    t463 = valid_t463()
    t463["ok"] = False
    report = verify_execution_artifacts(valid_t462(), t463)
    assert report["ok"] is False
    assert "EXECUTION_RESULT_REPORT_NOT_READY" in report["violations"]


def test_simulated_status_wrong_fail(tmp_path):
    t463 = valid_t463()
    t463["simulated_execution_summary"]["status"] = "BAD"
    report = verify_execution_artifacts(valid_t462(), t463)
    assert report["ok"] is False
    assert "SIMULATED_EXECUTION_NOT_COMPLETED" in report["violations"]


def test_submit_attempted_true_fail(tmp_path):
    t463 = valid_t463()
    t463["simulated_execution_summary"]["submit_attempted"] = True
    report = verify_execution_artifacts(valid_t462(), t463)
    assert report["ok"] is False
    assert "SUBMIT_CANCEL_FLATTEN_ATTEMPT_DETECTED" in report["violations"]


def test_never_allows_blocked_actions(tmp_path):
    report = verify_execution_artifacts(valid_t462(), valid_t463())
    for b in REQUIRED_BLOCKED_ACTIONS:
        assert b not in report["allowed_actions"]
        assert b in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t462.json")
    p2 = str(tmp_path / "t463.json")
    write_json(p1, valid_t462())
    with open(p2, "w", encoding="utf-8") as f:
        f.write("invalid json")
    report = verify_execution_artifacts(load_json(p1), load_json(p2))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t462.json")
    p2 = str(tmp_path / "missing_t463.json")
    write_json(p1, valid_t462())
    report = verify_execution_artifacts(load_json(p1), load_json(p2))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t462.json")
    p2 = str(tmp_path / "t463.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t462())
    write_json(p2, valid_t463())
    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "verify_testnet_dry_run_only_execution_artifacts_v1.py"),
            "--materialized-payload",
            p1,
            "--execution-result-report",
            p2,
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
