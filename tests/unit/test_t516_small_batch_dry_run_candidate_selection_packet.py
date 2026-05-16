import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_small_batch_dry_run_candidate_selection_packet_v1 import generate_selection


def phase_ok(max_n=5):
    return {"decision": "ALLOW_SMALL_BATCH_DRY_RUN_ONLY", "submit_allowed": False, "max_dry_run_candidates": max_n}


def cand(i, env="testnet", url="https://testnet.binance.vision"):
    return {"id": i, "env": env, "symbol": f"BTCUSDT{i}", "side": "BUY", "quantity": "0.01", "base_url": url}


def test_t516_pass():
    cands = [cand(1), cand(2)]
    r = generate_selection(phase_ok(), cands)
    assert r["verdict"] in ["PASS", "PARTIAL"]
    assert r["selected_count"] <= 5
    assert r["submit_allowed"] is False


def test_t516_phase_not_allowed_fail():
    p = phase_ok()
    p["decision"] = "REVIEW"
    r = generate_selection(p, [cand(1)])
    assert r["verdict"] == "FAIL"


def test_t516_too_many_capped_or_fail():
    cands = [cand(i) for i in range(10)]
    r = generate_selection(phase_ok(5), cands)
    assert r["selected_count"] <= 5


def test_t516_wrong_env_rejected():
    cands = [cand(1), cand(2, env="mainnet")]
    r = generate_selection(phase_ok(), cands)
    assert any(x["reason"] == "ENV_NOT_TESTNET" for x in r["rejected_candidates"])


def test_t516_malformed_candidates_fail():
    r = generate_selection(phase_ok(), {"bad": "shape"})
    assert r["verdict"] == "FAIL"
