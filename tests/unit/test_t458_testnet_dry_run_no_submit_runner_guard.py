import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_testnet_dry_run_no_submit_runner_guard_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    load_json,
    verify_runner_guard,
    write_json,
)


def valid_t457() -> dict:
    return {"ok": True}


def valid_runner_config() -> dict:
    return {
        "dry_run_only": True,
        "exchange_api_calls_enabled": False,
        "submit_enabled": False,
        "cancel_enabled": False,
        "flatten_enabled": False,
        "write_artifacts_only": True,
        "operator_review_required": True,
    }


def test_valid_runner_config_pass(tmp_path):
    report = verify_runner_guard(valid_t457(), valid_runner_config())
    assert report["ok"] is True
    assert report["runner_guard_status"] == "NO_SUBMIT_RUNNER_GUARD_VERIFIED"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_ONLY_PREFLIGHT_REPORT"


def test_t457_blocked_fail(tmp_path):
    report = verify_runner_guard({"ok": False}, valid_runner_config())
    assert report["ok"] is False
    assert "PAYLOAD_PLAN_NOT_READY" in report["violations"]


def test_exchange_api_enabled_fail(tmp_path):
    cfg = valid_runner_config()
    cfg["exchange_api_calls_enabled"] = True
    report = verify_runner_guard(valid_t457(), cfg)
    assert report["ok"] is False
    assert "EXCHANGE_API_CALLS_ENABLED" in report["violations"]


def test_submit_cancel_flatten_enabled_fail(tmp_path):
    cfg = valid_runner_config()
    cfg["submit_enabled"] = True
    cfg["cancel_enabled"] = True
    cfg["flatten_enabled"] = True
    report = verify_runner_guard(valid_t457(), cfg)
    assert report["ok"] is False
    assert "SUBMIT_ENABLED" in report["violations"]
    assert "CANCEL_ENABLED" in report["violations"]
    assert "FLATTEN_ENABLED" in report["violations"]


def test_write_artifacts_false_fail(tmp_path):
    cfg = valid_runner_config()
    cfg["write_artifacts_only"] = False
    report = verify_runner_guard(valid_t457(), cfg)
    assert report["ok"] is False
    assert "WRITE_ARTIFACTS_ONLY_NOT_ENABLED" in report["violations"]


def test_operator_review_false_fail(tmp_path):
    cfg = valid_runner_config()
    cfg["operator_review_required"] = False
    report = verify_runner_guard(valid_t457(), cfg)
    assert report["ok"] is False
    assert "OPERATOR_REVIEW_NOT_REQUIRED" in report["violations"]


def test_never_allows_submit_cancel_flatten(tmp_path):
    report = verify_runner_guard(valid_t457(), valid_runner_config())
    for blocked in REQUIRED_BLOCKED_ACTIONS:
        assert blocked not in report["allowed_actions"]
        assert blocked in report["blocked_actions"]


def test_invalid_json(tmp_path):
    p1 = str(tmp_path / "t457.json")
    p2 = str(tmp_path / "cfg.json")
    write_json(p1, valid_t457())
    with open(p2, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = verify_runner_guard(load_json(p1), load_json(p2))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    p1 = str(tmp_path / "t457.json")
    p2 = str(tmp_path / "missing_cfg.json")
    write_json(p1, valid_t457())

    report = verify_runner_guard(load_json(p1), load_json(p2))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    p1 = str(tmp_path / "t457.json")
    p2 = str(tmp_path / "cfg.json")
    out = str(tmp_path / "out.json")
    write_json(p1, valid_t457())
    write_json(p2, valid_runner_config())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "verify_testnet_dry_run_no_submit_runner_guard_v1.py"),
            "--payload-plan",
            p1,
            "--runner-config",
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
