import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_small_batch_dry_run_risk_concentration_report_v1 import generate_report


def selection(cands, submit_allowed=False):
    return {"selected_candidates": cands, "submit_allowed": submit_allowed}


def cand(symbol, side="BUY", qty="1", env="testnet"):
    return {"symbol": symbol, "side": side, "quantity": qty, "env": env, "reference_price": "100", "base_url": "https://testnet.binance.vision"}


def test_t519_low():
    cands = [cand("BTCUSDT", "BUY"), cand("ETHUSDT", "SELL"), cand("XRPUSDT", "BUY")]
    r = generate_report(selection(cands))
    assert r["verdict"] in ["PASS", "PARTIAL"]


def test_t519_high_duplicate_symbol():
    cands = [cand("BTCUSDT"), cand("BTCUSDT"), cand("ETHUSDT")]
    r = generate_report(selection(cands))
    assert r["concentration_status"] == "HIGH"


def test_t519_high_same_side():
    cands = [cand("BTCUSDT", "BUY"), cand("ETHUSDT", "BUY"), cand("XRPUSDT", "BUY")]
    r = generate_report(selection(cands))
    assert r["concentration_status"] == "HIGH"


def test_t519_fail_submit_allowed():
    r = generate_report(selection([cand("BTCUSDT")], submit_allowed=True))
    assert r["verdict"] == "FAIL"


def test_t519_fail_gt5_candidates():
    cands = [cand(f"S{i}") for i in range(6)]
    r = generate_report(selection(cands))
    assert r["verdict"] == "FAIL"
