import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_third_manual_testnet_submit_command_packet_v1 import generate_command_packet


def eligibility_ok():
    return {"verdict": "PASS", "eligible_for_third_manual_submit": True, "max_submit_count": 1}


def candidate_ok(env="testnet", base_url="https://testnet.binance.vision"):
    return {"env": env, "symbol": "BTCUSDT", "side": "BUY", "quantity": "0.01", "base_url": base_url}


def test_t512_pass():
    r = generate_command_packet(eligibility_ok(), candidate_ok())
    assert r["verdict"] == "PASS"


def test_t512_wrong_env_fail():
    r = generate_command_packet(eligibility_ok(), candidate_ok(env="mainnet"))
    assert r["verdict"] == "FAIL"


def test_t512_eligibility_fail():
    r = generate_command_packet({"verdict": "FAIL", "eligible_for_third_manual_submit": False, "max_submit_count": 0}, candidate_ok())
    assert r["verdict"] == "FAIL"


def test_t512_live_base_url_blocked():
    r = generate_command_packet(eligibility_ok(), candidate_ok(base_url="https://api.binance.com"))
    assert r["verdict"] == "FAIL"
    assert "CANDIDATE_BASE_URL_NOT_TESTNET" in r["blockers"]


def test_t512_dry_run_default():
    r = generate_command_packet(eligibility_ok(), candidate_ok())
    assert "--allow-testnet-submit" not in r["dry_run_command"]
    assert "--allow-testnet-submit" in r["submit_command_template"]
    assert "--confirm-token" in r["submit_command_template"]
