import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_testnet_dry_run_enablement_safety_switch_v1 import (
    REQUIRED_BLOCKED_ACTIONS,
    load_json,
    verify_safety_switch,
    write_json,
)


def valid_t451() -> dict:
    return {"ok": True}


def valid_config() -> dict:
    return {
        "mode": "TESTNET_DRY_RUN_ONLY",
        "enable_testnet_dry_run_only": True,
        "testnet_submit_allowed": False,
        "real_submit_allowed": False,
        "submit_order_allowed": False,
        "cancel_order_allowed": False,
        "flatten_position_allowed": False,
        "operator_confirmation_required": True,
        "manual_final_gate_required": True,
        "notes": "ok",
    }


def test_valid_config_pass(tmp_path):
    report = verify_safety_switch(valid_t451(), valid_config())
    assert report["ok"] is True
    assert report["safety_switch_status"] == "TESTNET_DRY_RUN_ENABLEMENT_SAFETY_SWITCH_VERIFIED"
    assert report["final_decision"] == "READY_FOR_TESTNET_DRY_RUN_OPERATOR_CONFIRMATION"


def test_invalid_mode(tmp_path):
    cfg = valid_config()
    cfg["mode"] = "WRONG"
    report = verify_safety_switch(valid_t451(), cfg)
    assert report["ok"] is False
    assert "INVALID_MODE" in report["violations"]


def test_enable_false_violation(tmp_path):
    cfg = valid_config()
    cfg["enable_testnet_dry_run_only"] = False
    report = verify_safety_switch(valid_t451(), cfg)
    assert report["ok"] is False
    assert "TESTNET_DRY_RUN_ONLY_NOT_ENABLED_IN_CONFIG" in report["violations"]


def test_submit_cancel_flatten_true_exact_violations(tmp_path):
    cfg = valid_config()
    cfg["submit_order_allowed"] = True
    cfg["cancel_order_allowed"] = True
    cfg["flatten_position_allowed"] = True
    report = verify_safety_switch(valid_t451(), cfg)

    assert report["ok"] is False
    assert "SUBMIT_ORDER_NOT_ALLOWED" in report["violations"]
    assert "CANCEL_ORDER_NOT_ALLOWED" in report["violations"]
    assert "FLATTEN_POSITION_NOT_ALLOWED" in report["violations"]


def test_operator_confirmation_false_violation(tmp_path):
    cfg = valid_config()
    cfg["operator_confirmation_required"] = False
    report = verify_safety_switch(valid_t451(), cfg)
    assert report["ok"] is False
    assert "OPERATOR_CONFIRMATION_NOT_REQUIRED" in report["violations"]


def test_manual_final_gate_false_violation(tmp_path):
    cfg = valid_config()
    cfg["manual_final_gate_required"] = False
    report = verify_safety_switch(valid_t451(), cfg)
    assert report["ok"] is False
    assert "MANUAL_FINAL_GATE_NOT_REQUIRED" in report["violations"]


def test_t451_blocked_violation(tmp_path):
    t451 = {"ok": False}
    report = verify_safety_switch(t451, valid_config())
    assert report["ok"] is False
    assert "ENABLEMENT_PACKET_NOT_READY" in report["violations"]


def test_safety_invariants(tmp_path):
    report = verify_safety_switch(valid_t451(), valid_config())

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
    t451_path = str(tmp_path / "t451.json")
    cfg_path = str(tmp_path / "cfg.json")
    write_json(t451_path, valid_t451())
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write("invalid json")

    report = verify_safety_switch(load_json(t451_path), load_json(cfg_path))
    assert report["ok"] is False


def test_missing_file(tmp_path):
    t451_path = str(tmp_path / "t451.json")
    missing_cfg_path = str(tmp_path / "missing_cfg.json")
    write_json(t451_path, valid_t451())

    report = verify_safety_switch(load_json(t451_path), load_json(missing_cfg_path))
    assert report["ok"] is False


def test_cli_smoke(tmp_path):
    t451_path = str(tmp_path / "t451.json")
    cfg_path = str(tmp_path / "cfg.json")
    output_path = str(tmp_path / "out.json")
    write_json(t451_path, valid_t451())
    write_json(cfg_path, valid_config())

    proc = subprocess.Popen(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent.parent
                / "scripts"
                / "verify_testnet_dry_run_enablement_safety_switch_v1.py"
            ),
            "--enablement-packet",
            t451_path,
            "--safety-switch-config",
            cfg_path,
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
