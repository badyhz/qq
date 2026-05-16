import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_repeat_small_batch_candidate_refresh_packet_v1 import generate_refresh


def elig(v="PASS"):
    return {"verdict": v, "max_dry_run_candidates": 5}


def cand(i, env="testnet", base="https://testnet.binance.vision"):
    return {"symbol": f"S{i}", "side": "BUY", "quantity": "0.01", "env": env, "base_url": base}


def test_t522_pass():
    r = generate_refresh(elig("PASS"), [cand(1), cand(2)], None)
    assert r["verdict"] == "PASS"
    assert r["selected_count"] <= 5


def test_t522_partial_eligibility():
    r = generate_refresh(elig("PARTIAL"), [cand(1), cand(2)], None)
    assert r["verdict"] == "PARTIAL"


def test_t522_wrong_env_rejected():
    r = generate_refresh(elig("PASS"), [cand(1), cand(2, env="mainnet")], None)
    assert r["verdict"] == "FAIL"
    assert any(x["reason"] == "ENV_NOT_TESTNET" for x in r["rejected_candidates"])


def test_t522_mainnet_blocked():
    r = generate_refresh(elig("PASS"), [cand(1, base="https://api.binance.com")], None)
    assert r["verdict"] == "FAIL"


def test_t522_selected_count_capped():
    cands = [cand(i) for i in range(10)]
    r = generate_refresh(elig("PASS"), cands, None)
    assert r["selected_count"] <= 5
    assert r["submit_allowed"] is False
