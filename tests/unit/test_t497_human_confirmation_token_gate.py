import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_human_confirmation_token_gate_v1 import generate_token_gate, write_json


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "generate_human_confirmation_token_gate_v1.py"


def phase_pass():
    return {"verdict": "PASS", "phase": "final_pre_testnet_submit_control"}


def invariant_pass():
    return {
        "verdict": "PASS",
        "invariant_checks": [
            {"name": "env_is_testnet", "value": "testnet"},
            {"name": "symbol_exists", "value": "BTCUSDT"},
            {"name": "side_valid", "value": "BUY"},
        ],
    }


def delta_pass():
    return {"verdict": "PASS", "machine_readable_deltas": []}


def test_t497_pass_token_shape():
    r = generate_token_gate(phase_pass(), invariant_pass(), delta_pass())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["confirmation_token"].startswith("TESTNET_SUBMIT_BTCUSDT_BUY_")


def test_t497_fail_if_phase_not_pass():
    r = generate_token_gate({"verdict": "FAIL"}, invariant_pass(), delta_pass())
    assert r["ok"] is False
    assert "PHASE_REPORT_NOT_PASS" in r["blocking_reasons"]


def test_t497_fail_if_invariant_not_pass_or_env_bad():
    inv = invariant_pass()
    inv["verdict"] = "FAIL"
    inv["invariant_checks"][0]["value"] = "mainnet"
    r = generate_token_gate(phase_pass(), inv, delta_pass())
    assert r["ok"] is False
    assert "INVARIANT_REPORT_NOT_PASS" in r["blocking_reasons"]
    assert "ENV_NOT_TESTNET" in r["blocking_reasons"]


def test_t497_fail_if_dangerous_delta():
    r = generate_token_gate(phase_pass(), invariant_pass(), {"verdict": "FAIL"})
    assert r["ok"] is False
    assert "RISK_DELTA_DANGEROUS" in r["blocking_reasons"]


def test_t497_cli_smoke(tmp_path):
    p1 = tmp_path / "phase.json"
    p2 = tmp_path / "inv.json"
    p3 = tmp_path / "delta.json"
    out = tmp_path / "out.json"
    write_json(str(p1), phase_pass())
    write_json(str(p2), invariant_pass())
    write_json(str(p3), delta_pass())
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--inputs", str(p1), str(p2), str(p3), "--output", str(out), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
