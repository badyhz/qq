import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_human_gated_execution_wrapper_dry_run_plan_v1 import generate_plan


def elig(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def packet(v="PASS"):
    return {
        "verdict": v,
        "submit_allowed": False,
        "dry_run_command": "python3 scripts/run_testnet_submit_execution_wrapper_v1.py --env testnet --symbol BTCUSDT --side BUY --quantity 0.01 --dry-run",
        "manual_submit_command_template": "python3 scripts/run_testnet_submit_execution_wrapper_v1.py --allow-testnet-submit --confirm-token <TOKEN> --env testnet --symbol BTCUSDT --side BUY --quantity 0.01",
    }


def token(v="PASS"):
    return {"verdict": v, "submit_allowed": False}


def test_pass():
    r = generate_plan(elig("PASS"), packet("PASS"), token("PASS"))
    assert r["verdict"] == "PASS"
    assert r["dry_run_only"] is True
    assert r["submit_allowed"] is False
    assert r["max_submit_count"] == 1
    assert "--allow-testnet-submit" in r["required_runtime_inputs"]
    assert "--confirm-token" in str(r["required_runtime_inputs"])
    assert "--env testnet" in r["required_runtime_inputs"]


def test_eligibility_fail():
    r = generate_plan(elig("FAIL"), packet("PASS"), token("PASS"))
    assert r["verdict"] == "FAIL"


def test_forbidden_live_marker_fail():
    p = packet("PASS")
    p["manual_submit_command_template"] = "python3 script.py --env mainnet"
    r = generate_plan(elig("PASS"), p, token("PASS"))
    assert r["verdict"] == "FAIL"
    assert "FORBIDDEN_LIVE_MARKER_FOUND" in r["blockers"]


def test_forbidden_auto_submit_marker_fail():
    p = packet("PASS")
    p["manual_submit_command_template"] = "python3 script.py --auto-submit"
    r = generate_plan(elig("PASS"), p, token("PASS"))
    assert r["verdict"] == "FAIL"
    assert "FORBIDDEN_AUTO_SUBMIT_MARKER_FOUND" in r["blockers"]


def test_missing_token_gate_fail():
    p = packet("PASS")
    p["manual_submit_command_template"] = "python3 script.py --no-gate"
    r = generate_plan(elig("PASS"), p, token("PASS"))
    assert r["verdict"] == "FAIL"
    assert "REQUIRED_TOKEN_GATE_MISSING_IN_TEMPLATE" in r["blockers"]


def test_submit_allowed_true_in_input_fail():
    e = elig("PASS")
    e["submit_allowed"] = True
    r = generate_plan(e, packet("PASS"), token("PASS"))
    assert r["verdict"] == "FAIL"
    assert "SUBMIT_ALLOWED_TRUE_IN_INPUT" in r["blockers"]


def test_submit_allowed_remains_false_always():
    r = generate_plan(elig("PASS"), packet("PASS"), token("PASS"))
    assert r["submit_allowed"] is False

    r = generate_plan(elig("FAIL"), packet("FAIL"), token("FAIL"))
    assert r["submit_allowed"] is False


def test_dry_run_default_true():
    r = generate_plan(elig("PASS"), packet("PASS"), token("PASS"))
    assert r["dry_run_only"] is True
