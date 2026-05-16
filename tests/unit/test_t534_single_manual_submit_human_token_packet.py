import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_single_manual_submit_human_token_packet_v1 import generate_token_packet


def preflight(v="PASS"):
    return {"verdict": v}


def packet(v="PASS"):
    return {
        "verdict": v,
        "env": "testnet",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.01",
    }


def test_pass():
    r = generate_token_packet(preflight("PASS"), packet("PASS"))
    assert r["verdict"] == "PASS"
    assert r["token_required"] is True
    assert r["submit_allowed"] is False


def test_preflight_fail():
    r = generate_token_packet(preflight("FAIL"), packet("PASS"))
    assert r["verdict"] == "FAIL"


def test_packet_fail():
    r = generate_token_packet(preflight("PASS"), packet("FAIL"))
    assert r["verdict"] == "FAIL"


def test_token_binds_fields():
    r = generate_token_packet(preflight("PASS"), packet("PASS"))
    tpl = r["token_phrase_template"]
    assert "testnet" in tpl
    assert "BTCUSDT" in tpl
    assert "BUY" in tpl
    assert "0.01" in tpl
    assert "COUNT_1" in tpl
