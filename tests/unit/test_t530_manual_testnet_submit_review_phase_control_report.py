import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_manual_testnet_submit_review_phase_control_report_v1 import generate_report


def p(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def score(v="PASS", d="READY_FOR_SINGLE_MANUAL_SUBMIT_PACKET"):
    return {"verdict": v, "decision": d}


def test_allow_packet_generation():
    r = generate_report(p("PASS"), p("PASS"), p("PASS"), score("PASS", "READY_FOR_SINGLE_MANUAL_SUBMIT_PACKET"))
    assert r["verdict"] == "PASS"
    assert r["decision"] == "ALLOW_SINGLE_MANUAL_SUBMIT_PACKET_GENERATION"


def test_repeat_dry_run():
    r = generate_report(p("PARTIAL"), p("PASS"), p("PASS"), score("PARTIAL", "REVIEW_MORE_DRY_RUN"))
    assert r["decision"] in ["REPEAT_SMALL_BATCH_DRY_RUN", "REVIEW"]


def test_review():
    r = generate_report(p("PARTIAL"), p("PASS"), p("PASS"), score("PARTIAL", "BLOCK"))
    assert r["decision"] == "REVIEW"


def test_stop():
    r = generate_report(p("FAIL"), p("PASS"), p("PASS"), score("PASS", "READY_FOR_SINGLE_MANUAL_SUBMIT_PACKET"))
    assert r["decision"] == "STOP"


def test_submit_never_allowed():
    r = generate_report(p("PASS"), p("PASS"), p("PASS"), score("PASS", "READY_FOR_SINGLE_MANUAL_SUBMIT_PACKET"))
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 0
