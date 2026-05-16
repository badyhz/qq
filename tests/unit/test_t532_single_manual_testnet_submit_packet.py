import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_single_manual_testnet_submit_packet_v1 import generate_packet


def elig(v="PASS"):
    return {"verdict": v, "eligible_for_packet_generation": v == "PASS"}


def review(v="PASS", candidate=None):
    if candidate is None:
        candidate = {
            "env": "testnet",
            "base_url": "https://testnet.binance.vision",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "0.01",
        }
    return {"verdict": v, "preferred_candidate": candidate}


def test_pass():
    r = generate_packet(elig("PASS"), review("PASS"))
    assert r["verdict"] == "PASS"
    assert r["packet_type"] == "SINGLE_MANUAL_TESTNET_SUBMIT"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1


def test_wrong_env_fail():
    c = review("PASS")["preferred_candidate"]
    c["env"] = "mainnet"
    r = generate_packet(elig("PASS"), review("PASS", c))
    assert r["verdict"] == "FAIL"


def test_eligibility_fail():
    r = generate_packet(elig("FAIL"), review("PASS"))
    assert r["verdict"] == "FAIL"


def test_candidate_review_fail():
    r = generate_packet(elig("PASS"), review("FAIL"))
    assert r["verdict"] == "FAIL"


def test_dry_run_default_and_token_gated_template():
    r = generate_packet(elig("PASS"), review("PASS"))
    assert "--dry-run" in r["dry_run_command"]
    tmpl = r["manual_submit_command_template"]
    assert "--allow-testnet-submit" in tmpl
    assert "--confirm-token" in tmpl
    assert "--env testnet" in tmpl
