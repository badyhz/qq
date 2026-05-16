import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_manual_testnet_submit_review_score_report_v1 import generate_score


def re(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def cr(v="PASS", preferred=True, high_warn=False):
    w = ["HIGH_CONCENTRATION_WARNING"] if high_warn else []
    return {"verdict": v, "submit_allowed": False, "preferred_candidate": ({"symbol": "BTCUSDT"} if preferred else None), "warnings": w}


def ck(v="PASS"):
    return {"verdict": v}


def rs(v="PASS", drift=False):
    w = ["SIGNIFICANT_PASS_RATE_DRIFT"] if drift else []
    return {"verdict": v, "warnings": w}


def test_pass_ready():
    r = generate_score(re(), cr(), ck(), rs())
    assert r["verdict"] == "PASS"
    assert r["decision"] == "READY_FOR_SINGLE_MANUAL_SUBMIT_PACKET"


def test_partial_review_more():
    r = generate_score(re("PARTIAL"), cr(), ck(), rs())
    assert r["verdict"] == "PARTIAL"
    assert r["decision"] == "REVIEW_MORE_DRY_RUN"


def test_fail_blocked():
    r = generate_score(re("FAIL"), cr(), ck(), rs())
    assert r["verdict"] == "FAIL"
    assert r["decision"] == "BLOCK"


def test_submit_never_allowed():
    r = generate_score(re(), cr(), ck(), rs())
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 0


def test_score_caps():
    r = generate_score(re(), cr(preferred=False, high_warn=True), ck("PARTIAL"), rs(drift=True))
    assert r["review_score"] <= 50
