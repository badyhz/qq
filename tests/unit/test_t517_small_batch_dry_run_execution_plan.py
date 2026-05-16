import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_small_batch_dry_run_execution_plan_v1 import generate_plan


def selection_ok():
    return {
        "verdict": "PASS",
        "submit_allowed": False,
        "selected_candidates": [
            {"symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01", "base_url": "https://testnet.binance.vision"}
        ],
    }


def test_t517_pass():
    r = generate_plan(selection_ok())
    assert r["verdict"] == "PASS"
    assert r["submit_allowed"] is False


def test_t517_submit_flag_blocked():
    s = selection_ok()
    s["submit_allowed"] = True
    r = generate_plan(s)
    assert r["verdict"] == "FAIL"


def test_t517_confirm_token_blocked():
    r = generate_plan(selection_ok())
    assert all("--confirm-token" not in c for c in r["dry_run_commands"])


def test_t517_mainnet_blocked():
    s = selection_ok()
    s["selected_candidates"][0]["base_url"] = "https://api.binance.com"
    r = generate_plan(s)
    assert r["verdict"] == "FAIL"


def test_t517_malformed_selection():
    r = generate_plan(None)
    assert r["verdict"] == "FAIL"
