import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.verify_testnet_submit_payload_invariants_v1 import verify_invariants, write_json


SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "verify_testnet_submit_payload_invariants_v1.py"


def valid_payload():
    return {
        "env": "testnet",
        "dry_run_artifact": "artifacts/dry_run.json",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.01",
        "order_type": "MARKET",
        "reduceOnly": False,
        "expect_protective_orders": True,
        "stop_loss": {"type": "STOP_MARKET", "stopPrice": "50000", "trigger_direction": "BELOW"},
        "take_profit": {"type": "TAKE_PROFIT_MARKET", "stopPrice": "70000", "trigger_direction": "ABOVE"},
        "base_url": "https://testnet.binance.vision",
        "endpoint": "/fapi/v1/order/test",
    }


def test_t492_pass():
    report = verify_invariants(valid_payload())
    assert report["ok"] is True
    assert report["verdict"] == "PASS"


def test_t492_partial_warning():
    payload = valid_payload()
    payload["expect_protective_orders"] = False
    report = verify_invariants(payload)
    assert report["ok"] is True
    assert report["verdict"] == "PARTIAL"
    assert "PROTECTIVE_CONFIG_PRESENT_WITHOUT_EXPECTATION" in report["warnings"]


def test_t492_fail_mainnet_endpoint_detection():
    payload = valid_payload()
    payload["base_url"] = "https://api.binance.com"
    report = verify_invariants(payload)
    assert report["ok"] is False
    assert report["verdict"] == "FAIL"
    assert "LIVE_BASE_URL_DETECTED" in report["blocking_reasons"]


def test_t492_fail_invalid_fields():
    payload = valid_payload()
    payload["symbol"] = ""
    payload["side"] = "LONG"
    payload["quantity"] = "0"
    report = verify_invariants(payload)
    assert report["ok"] is False
    assert "SYMBOL_MISSING" in report["blocking_reasons"]
    assert "SIDE_INVALID" in report["blocking_reasons"]
    assert "QUANTITY_INVALID" in report["blocking_reasons"]


def test_t492_cli_smoke(tmp_path):
    inp = tmp_path / "payload.json"
    out = tmp_path / "out.json"
    write_json(str(inp), valid_payload())
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--input", str(inp), "--output", str(out), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.communicate()
    assert proc.returncode in [0, 1]
    assert os.path.exists(out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert "invariant_checks" in loaded
