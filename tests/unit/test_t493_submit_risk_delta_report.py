import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_submit_risk_delta_report_v1 import compare_payloads, write_json


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "generate_submit_risk_delta_report_v1.py"


def base_payload():
    return {
        "env": "testnet",
        "base_url": "https://testnet.binance.vision",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.01",
        "entry_price": "60000",
        "stop_loss": {"price": "58000"},
        "take_profit": {"price": "65000"},
    }


def test_t493_pass_no_delta():
    a = base_payload()
    b = base_payload()
    report = compare_payloads(a, b)
    assert report["ok"] is True
    assert report["verdict"] == "PASS"


def test_t493_partial_non_blocking_delta():
    a = base_payload()
    b = base_payload()
    b["entry_price"] = "60010"
    report = compare_payloads(a, b)
    assert report["ok"] is True
    assert report["verdict"] == "PARTIAL"
    assert report["safe_partial"] is True


def test_t493_fail_changed_symbol_side_quantity():
    a = base_payload()
    b = base_payload()
    b["symbol"] = "ETHUSDT"
    b["side"] = "SELL"
    b["quantity"] = "0.02"
    report = compare_payloads(a, b)
    assert report["ok"] is False
    assert report["verdict"] == "FAIL"
    assert "SYMBOL_CHANGED" in report["blocking_reasons"]
    assert "SIDE_CHANGED" in report["blocking_reasons"]
    assert "QUANTITY_CHANGED" in report["blocking_reasons"]


def test_t493_fail_mainnet_base_url():
    a = base_payload()
    b = base_payload()
    b["base_url"] = "https://api.binance.com"
    report = compare_payloads(a, b)
    assert report["verdict"] == "FAIL"
    assert "INTENDED_SUBMIT_BASE_URL_MAINNET_LIKE" in report["blocking_reasons"]


def test_t493_cli_smoke(tmp_path):
    dry = tmp_path / "dry.json"
    submit = tmp_path / "submit.json"
    out = tmp_path / "out.json"
    write_json(str(dry), base_payload())
    write_json(str(submit), base_payload())
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--inputs", str(dry), str(submit), "--output", str(out), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert "machine_readable_deltas" in loaded
