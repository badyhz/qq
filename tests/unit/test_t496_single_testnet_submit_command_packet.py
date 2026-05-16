import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_single_testnet_submit_command_packet_v1 import generate_command_packet, write_json


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "generate_single_testnet_submit_command_packet_v1.py"


def phase_pass():
    return {"verdict": "PASS", "phase": "final_pre_testnet_submit_control"}


def payload_ok():
    return {"env": "testnet", "base_url": "https://testnet.binance.vision", "symbol": "BTCUSDT", "side": "BUY"}


def test_t496_pass_and_dry_run_first():
    r = generate_command_packet(phase_pass(), payload_ok())
    assert r["ok"] is True
    assert r["verdict"] == "PASS"
    assert r["submit_mode_default"] == "dry_run"
    assert r["command_templates"][0]["name"] == "dry_run_first"


def test_t496_fail_if_phase_not_pass():
    r = generate_command_packet({"verdict": "FAIL"}, payload_ok())
    assert r["ok"] is False
    assert r["verdict"] == "FAIL"


def test_t496_blocks_mainnet_template_not_present():
    r = generate_command_packet(phase_pass(), {"env": "testnet", "base_url": "https://api.binance.com"})
    assert r["ok"] is False
    assert "PAYLOAD_BASE_URL_NOT_TESTNET" in r["blocking_reasons"]
    joined = json.dumps(r["command_templates"], sort_keys=True)
    assert "mainnet" not in joined.lower()


def test_t496_cli_smoke(tmp_path):
    p1 = tmp_path / "phase.json"
    p2 = tmp_path / "payload.json"
    out = tmp_path / "out.json"
    write_json(str(p1), phase_pass())
    write_json(str(p2), payload_ok())
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--inputs", str(p1), str(p2), "--output", str(out), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
