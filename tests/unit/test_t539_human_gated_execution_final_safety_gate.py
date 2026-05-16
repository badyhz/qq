import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_human_gated_execution_final_safety_gate_v1 import generate_gate


def elig(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def plan(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def token(v="PASS", matches=True):
    return {"verdict": v, "token_matches": matches, "submit_allowed": False}


def preflight(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def test_ready():
    r = generate_gate(elig("PASS"), plan("PASS"), token("PASS", True), preflight("PASS"))
    assert r["verdict"] == "PASS"
    assert r["gate_status"] == "READY_FOR_HUMAN_EXECUTION"
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1
    assert r["execution_requires_allow_flag"] is True
    assert r["execution_requires_confirm_token"] is True
    assert r["execution_requires_env_testnet"] is True


def test_token_partial_needs_review():
    r = generate_gate(elig("PASS"), plan("PASS"), token("PARTIAL", False), preflight("PASS"))
    assert r["verdict"] == "PARTIAL"
    assert r["gate_status"] == "NEEDS_REVIEW"


def test_any_fail_blocked():
    r = generate_gate(elig("FAIL"), plan("PASS"), token("PASS", True), preflight("PASS"))
    assert r["verdict"] == "FAIL"
    assert r["gate_status"] == "BLOCKED"


def test_submit_allowed_remains_false_always():
    r = generate_gate(elig("PASS"), plan("PASS"), token("PASS", True), preflight("PASS"))
    assert r["submit_allowed"] is False

    r = generate_gate(elig("FAIL"), plan("FAIL"), token("FAIL", False), preflight("FAIL"))
    assert r["submit_allowed"] is False


def test_required_checks_present():
    r = generate_gate(elig("PASS"), plan("PASS"), token("PASS", True), preflight("PASS"))
    checks = r["final_human_checks"]
    assert "VERIFY_ENV_IS_TESTNET" in checks
    assert "VERIFY_SYMBOL_SIDE_QUANTITY_ARE_CORRECT" in checks
    assert "VERIFY_TOKEN_MATCHES_EXACTLY" in checks
    assert "VERIFY_ALLOW_TESTNET_SUBMIT_FLAG_IS_INTENTIONAL" in checks
    assert "VERIFY_NO_MAINNET_OR_LIVE_MARKERS" in checks
    assert "VERIFY_NO_AUTO_OR_REPEAT_SUBMIT" in checks
    assert "VERIFY_MAX_SUBMIT_COUNT_IS_1" in checks


def test_submit_allowed_true_in_input_fail():
    e = elig("PASS")
    e["submit_allowed"] = True
    r = generate_gate(e, plan("PASS"), token("PASS", True), preflight("PASS"))
    assert r["verdict"] == "FAIL"
    assert "SUBMIT_ALLOWED_TRUE_IN_INPUT" in r["blockers"]
