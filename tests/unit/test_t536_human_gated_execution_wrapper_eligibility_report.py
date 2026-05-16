import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_human_gated_execution_wrapper_eligibility_report_v1 import generate_report


def phase(v="PASS", decision="READY_FOR_HUMAN_MANUAL_TESTNET_SUBMIT"):
    return {"verdict": v, "decision": decision, "submit_allowed": False}


def token_packet(v="PASS", token_required=True):
    return {"verdict": v, "token_required": token_required, "submit_allowed": False, "max_submit_count": 1}


def preflight(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def packet(v="PASS"):
    return {"verdict": v, "submit_allowed": False, "max_submit_count": 1}


def test_pass():
    r = generate_report(phase("PASS"), token_packet("PASS"), preflight("PASS"), packet("PASS"))
    assert r["verdict"] == "PASS"
    assert r["eligible_for_execution_wrapper"] is True
    assert r["wrapper_mode"] == "HUMAN_GATED_SINGLE_TESTNET_SUBMIT"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1
    assert r["required_manual_confirmation"] is True


def test_phase_not_ready_fail():
    r = generate_report(phase("PASS", "REVIEW"), token_packet("PASS"), preflight("PASS"), packet("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["eligible_for_execution_wrapper"] is False


def test_token_packet_fail():
    r = generate_report(phase("PASS"), token_packet("FAIL"), preflight("PASS"), packet("PASS"))
    assert r["verdict"] == "FAIL"


def test_token_required_not_true_fail():
    r = generate_report(phase("PASS"), token_packet("PASS", token_required=False), preflight("PASS"), packet("PASS"))
    assert r["verdict"] == "FAIL"


def test_preflight_fail():
    r = generate_report(phase("PASS"), token_packet("PASS"), preflight("FAIL"), packet("PASS"))
    assert r["verdict"] == "FAIL"


def test_packet_fail():
    r = generate_report(phase("PASS"), token_packet("PASS"), preflight("PASS"), packet("FAIL"))
    assert r["verdict"] == "FAIL"


def test_max_submit_count_not_1_fail():
    tp = token_packet("PASS")
    tp["max_submit_count"] = 2
    r = generate_report(phase("PASS"), tp, preflight("PASS"), packet("PASS"))
    assert r["verdict"] == "FAIL"
    assert "TOKEN_PACKET_MAX_SUBMIT_COUNT_NOT_1" in r["blockers"]

    sp = packet("PASS")
    sp["max_submit_count"] = 3
    r = generate_report(phase("PASS"), token_packet("PASS"), preflight("PASS"), sp)
    assert r["verdict"] == "FAIL"
    assert "SINGLE_PACKET_MAX_SUBMIT_COUNT_NOT_1" in r["blockers"]


def test_submit_allowed_true_in_input_fail():
    p = phase("PASS")
    p["submit_allowed"] = True
    r = generate_report(p, token_packet("PASS"), preflight("PASS"), packet("PASS"))
    assert r["verdict"] == "FAIL"
    assert "SUBMIT_ALLOWED_TRUE_IN_INPUT" in r["blockers"]


def test_malformed_input_missing_json():
    r = generate_report(None, token_packet("PASS"), preflight("PASS"), packet("PASS"))
    assert r["verdict"] == "FAIL"
    assert "SINGLE_MANUAL_SUBMIT_PHASE_MISSING" in r["blockers"]


def test_submit_allowed_remains_false_always():
    r = generate_report(phase("PASS"), token_packet("PASS"), preflight("PASS"), packet("PASS"))
    assert r["submit_allowed"] is False

    r = generate_report(phase("FAIL"), token_packet("FAIL"), preflight("FAIL"), packet("FAIL"))
    assert r["submit_allowed"] is False
