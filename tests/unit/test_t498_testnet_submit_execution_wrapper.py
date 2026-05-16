import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.run_testnet_submit_execution_wrapper_v1 import execute_wrapper, write_json


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "run_testnet_submit_execution_wrapper_v1.py"


def command_packet():
    return {"verdict": "PASS"}


def token_gate(token="TESTNET_SUBMIT_BTCUSDT_BUY_20260101_ABCD1234"):
    return {"verdict": "PASS", "confirmation_token": token}


def payload(base_url="https://testnet.binance.vision", env="testnet"):
    return {
        "env": env,
        "base_url": base_url,
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.01",
        "order_type": "MARKET",
    }


def invariant_pass():
    return {"verdict": "PASS"}


def phase_pass():
    return {"verdict": "PASS"}


def test_t498_default_dry_run_no_submit_call():
    called = {"n": 0}

    def fake_submit(_):
        called["n"] += 1
        return {"ok": True}

    r = execute_wrapper(command_packet(), token_gate(), payload(), invariant_pass(), phase_pass(), submit_func=fake_submit)
    assert r["verdict"] == "DRY_RUN"
    assert r["submit_executed"] is False
    assert called["n"] == 0


def test_t498_submitted_requires_exact_token_allow_env_testnet():
    tok = "TESTNET_SUBMIT_BTCUSDT_BUY_20260101_ABCD1234"
    called = {"n": 0}

    def fake_submit(_):
        called["n"] += 1
        return {"ok": True}

    r = execute_wrapper(
        command_packet(),
        token_gate(tok),
        payload(),
        invariant_pass(),
        phase_pass(),
        allow_testnet_submit=True,
        confirm_token=tok,
        env="testnet",
        submit_func=fake_submit,
    )
    assert r["verdict"] == "SUBMITTED"
    assert r["submit_executed"] is True
    assert called["n"] == 1


def test_t498_wrong_token_blocks():
    r = execute_wrapper(
        command_packet(), token_gate("RIGHT"), payload(), invariant_pass(), phase_pass(),
        allow_testnet_submit=True, confirm_token="WRONG", env="testnet"
    )
    assert r["verdict"] == "BLOCKED"
    assert "CONFIRM_TOKEN_MISMATCH" in r["blocking_reasons"]


def test_t498_mainnet_or_live_blocks():
    r = execute_wrapper(
        command_packet(), token_gate("T"), payload(base_url="https://api.binance.com"), invariant_pass(), phase_pass(),
        allow_testnet_submit=True, confirm_token="T", env="testnet"
    )
    assert r["verdict"] == "BLOCKED"
    assert "BASE_URL_NOT_TESTNET" in r["blocking_reasons"]


def test_t498_invariant_or_phase_not_pass_blocks():
    r1 = execute_wrapper(
        command_packet(), token_gate("T"), payload(), {"verdict": "FAIL"}, phase_pass(),
        allow_testnet_submit=True, confirm_token="T", env="testnet"
    )
    assert "INVARIANT_REPORT_NOT_PASS" in r1["blocking_reasons"]

    r2 = execute_wrapper(
        command_packet(), token_gate("T"), payload(), invariant_pass(), {"verdict": "FAIL"},
        allow_testnet_submit=True, confirm_token="T", env="testnet"
    )
    assert "PHASE_REPORT_NOT_PASS" in r2["blocking_reasons"]


def test_t498_cli_smoke(tmp_path):
    p1 = tmp_path / "c.json"
    p2 = tmp_path / "t.json"
    p3 = tmp_path / "p.json"
    p4 = tmp_path / "i.json"
    p5 = tmp_path / "f.json"
    out = tmp_path / "out.json"
    write_json(str(p1), command_packet())
    write_json(str(p2), token_gate())
    write_json(str(p3), payload())
    write_json(str(p4), invariant_pass())
    write_json(str(p5), phase_pass())
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--inputs", str(p1), str(p2), str(p3), str(p4), str(p5), "--output", str(out), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
