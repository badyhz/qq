import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_manual_testnet_submit_candidate_review_packet_v1 import generate_review


def elig(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def sel(cands):
    return {"selected_candidates": cands}


def c(env="testnet", base="https://testnet.binance.vision", symbol="BTCUSDT", side="BUY", qty="0.01"):
    return {"env": env, "base_url": base, "symbol": symbol, "side": side, "quantity": qty}


def test_pass():
    r = generate_review(elig("PASS"), sel([c()]), {"concentration_status": "LOW"})
    assert r["verdict"] == "PASS"
    assert r["submit_allowed"] is False
    assert r["review_mode"] == "REVIEW_ONLY"


def test_high_concentration_partial():
    r = generate_review(elig("PASS"), sel([c()]), {"concentration_status": "HIGH"})
    assert r["verdict"] == "PARTIAL"


def test_wrong_env_rejected():
    r = generate_review(elig("PASS"), sel([c(env="mainnet")]), {"concentration_status": "LOW"})
    assert r["verdict"] == "FAIL"


def test_mainnet_blocked():
    r = generate_review(elig("PASS"), sel([c(base="https://api.binance.com")]), {"concentration_status": "LOW"})
    assert r["verdict"] == "FAIL"


def test_no_submit_command_emitted():
    r = generate_review(elig("PASS"), sel([c()]), {"concentration_status": "LOW"})
    dumped = str(r)
    assert "--allow-testnet-submit" not in dumped
    assert "--confirm-token" not in dumped
